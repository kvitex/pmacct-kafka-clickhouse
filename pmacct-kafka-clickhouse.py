#!/usr/bin/env python3
from prometheus_client import start_http_server, Counter
from kafka import KafkaConsumer
from json import loads
from json import dumps
from dotenv import load_dotenv
from datetime import datetime
from clickhouse_driver import Client
import os
import re
import pytz


load_dotenv()
kafka_bootstrap_servers          = os.environ['KAFKA_BOOTSTRAP_SERVERS']
kafka_topic                      = os.environ['KAFKA_TOPIC']
kafka_consumer_group_id          = os.environ.get('KAFKA_CONSUMER_GROUP_ID','kafka2clickhouse')
clickhouse_host                  = os.environ['CLICKHOUSE_HOST']
clickhouse_db                    = os.environ.get('CLICKHOUSE_DB', 'pmacct')
clickhouse_table                 = os.environ.get('CLICKHOUSE_TABLE','sflowstat')
clickhouse_user                  = os.environ['CLICKHOUSE_USER']
clickhouse_password              = os.environ['CLICKHOUSE_PASSWORD']
clickhouse_data_schema           = os.environ['CLICKHOUSE_DATA_SCHEMA']
clickhouse_create_table          = os.environ.get('CLICKHOUSE_CREATE_TABLE','YES')
clickhouse_order_by              = os.environ.get('CLICKHOUSE_ORDER_BY','')
clickhouse_partition_by          = os.environ.get('CLICKHOUSE_PARTITION_BY','')
clickhouse_max_samples_per_send  = int(os.environ.get('CLICKHOUSE_MAX_SAMPLES_PER_SEND','1000'))
clickhouse_max_time_to_send      = int(os.environ.get('CLICKHOUSE_MAX_TIME_TO_SEND','10'))
prometheus_client_port           = int(os.environ.get('PROMETHEUS_CLIENT_PORT','9003'))
timestmap_template               = os.environ.get('TIMESTAMP_TEMPLATE', '%Y-%m-%d %H:%M:%S')


def nowstamp():
    return str(datetime.now())

def def_by_type(data_type):
    def_value = ''
    if re.search('Int',data_type):
        def_value = 0
    return def_value

def main():
    client = Client(host=clickhouse_host, user=clickhouse_user, password=clickhouse_password)
    # Creating dict with field names as keys and types as values from CLICKHOUSE_DATA_SCHEMA string.
    fields = dict(tuple(map(lambda st: (st.split(':')[0], st.split(':')[1]), re.findall(r'[^,;\r\n\t\f\v]+', clickhouse_data_schema))))
    if clickhouse_create_table == 'YES':
        create_table_sql = f'''
            CREATE TABLE IF NOT EXISTS {clickhouse_db}.{clickhouse_table}
            (
                { ','.join(list(map( lambda field_tuple: ' '.join(field_tuple), fields.items()))) }
                )
                ENGINE = MergeTree()
                PARTITION BY ({clickhouse_partition_by})
                ORDER BY ({clickhouse_order_by})
        '''
        print(create_table_sql)
        print(client.execute(create_table_sql))
    print(client.execute('SHOW TABLES from pmacct'))
    print(f'{nowstamp()} Connecting to Kafka broker. Bootstrap servers {kafka_bootstrap_servers}')
    consumer = KafkaConsumer(
        kafka_topic, 
        bootstrap_servers=kafka_bootstrap_servers.split(','),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id=kafka_consumer_group_id,
        value_deserializer=lambda x: loads(x.decode('utf-8'))
        )
    print(f'{nowstamp()} Connected')
    samples_counter = Counter('samples_count_total', 'Total number of samples ')
    print(f'{nowstamp()} Starting Prometheus client http server')
    start_http_server(prometheus_client_port)
    db_rows = []
    samples_timer = int(datetime.now().timestamp())
    samples_max_count = 0
    insert_sql  = f'INSERT INTO {clickhouse_db}.{clickhouse_table} ({ ",".join(fields.keys()) }) VALUES'
    print(insert_sql)
    for message in consumer:
        db_rows.append({k: message.value.get(k, def_by_type(fields[k])) if re.search('Date', fields[k]) is None 
                           else datetime.strptime(message.value[k], timestmap_template).replace(tzinfo=pytz.utc)
                           for k in fields 
                        })
        samples_counter.inc()
        samples_max_count += 1
        if (samples_max_count > clickhouse_max_samples_per_send) or ((int(datetime.now().timestamp()) - samples_timer) > clickhouse_max_time_to_send):
            print(db_rows)
            r = client.execute(insert_sql, db_rows)
            print(f'{nowstamp()} Sent {samples_max_count} samples')
            samples_timer = int(datetime.now().timestamp())
            samples_max_count = 0
            db_rows = []
    return

if __name__ == "__main__":
    main()