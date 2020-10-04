# pmacct-kafka-clickhouse
**pmacct-kafka-clickhouse** is a python script designed to read flow statistics from [Kafka], to process it and to store it into [Clickhouse].\
Flow statistics is expected to be produced  by [Pmacct] flow collector kafka plugin.\
Script creates in [Clickhouse] MergeTree table with predefined data schema.\
Prometheus client is used to expose total count of sample processed. Metrics can be scraped at "/metrics" path. Default port is "9003".

Scripts uses `stamp_updated` filed as a main timestamp.\
You have to set `kafka_history` and `kafka_history_roundoff` options in sfacct.conf or nfacct.conf.

Example:
```
plugins: kafka[kafka]
kafka_history[kafka]: 5m
kafka_history_roundoff[kafka]: m
```

### Runnig the script

Just run:
```
pmacct-kafka-clickhouse.py
```
Script gets its  configuration from environment variables or from .env file(see .env.example).

### Running script in docker:

```
docker run --env-file .env --name pmacct-kafka-clickhouse -p 9003:9003 kvitex/pmacct-kafka-clickhouse 
```

### Variables:

Variable | Description | Example
--- | --- | ---
`KAFKA_BOOTSTRAP_SERVERS` | Kafka botstrap server in host:port format. Where can be several ones, separated by coma  |  **mykafka1:9094**
`KAFKA_TOPIC` | Kafka topic to read from.|  **pmacct.sfacct**
`KAFKA_CONSUMER_GROUP_ID` | Kafka consumer group id. Default value is kafka2clickhouse.| kafka2clickhouse
`CLICKHOUSE_HOST` | Clickhouse hostname or ip address.| **clickhouse.my.domain**
`CLICKHOUSE_DB` | Existing Clickhouse database. Default value is 'pmacct'.|  pmacct
`CLICKHOUSE_TABLE` | Clickhouse table. Will be created if not exists. Default value is 'sflowstat'.|  sflowstat
`CLICKHOUSE_USER` | Username to use with  Clickhouse. | **pmlab**
`CLICKHOUSE_PASSWORD` | Password for Clickhouse user.| **mypassword**
`CLICKHOUSE_DATA_SCHEMA` | Fileds type mapping. Comma separated values field:type.|**mac_src:String,ip_src:IPv4,ip_dst:IPv4,peer_ip_src:IPv4,port_src:UInt16,port_dst:UInt32,ip_proto:String,stamp_updated:DateTime,packets:UInt64,bytes:UInt64** 
`CLICKHOUSE_CREATE_TABLE` | If 'YES' then script will try to create table. Default values is 'YES'.| YES
`CLICKHOUSE_ORDER_BY` | Fileds to use in sort key. Effective only if script creates table. Default value is ''.| stamp_updated,peer_ip_src
`CLICKHOUSE_PARTITION_BY` | Partititioning key. Effective only if script creates table. Default value is ''.| toYYYYMMDD(stamp_updated)
`CLICKHOUSE_MAX_SAMPLES_PER_SEND` | Maximum number of samples that script caches before store them in  [Clickhouse]. Defaul value is '1000'  | 1000
`CLICKHOUSE_MAX_TIME_TO_SEND` | Maximum time in seconds, between sending samples to  [Clickhouse]. Default value is 10.| 10
`PROMETHEUS_CLIENT_PORT` | Prometheus client http server port. Default value is '9003'.| 9003

Script is polling Kafka for new messages in topic and store them in memory. It looks for amount of samples were read and time passed from last insert to [Clickhouse] operation.\
If amount of samples is greater then `CLICKHOUSE_MAX_SAMPLES_PER_SEND`  or time has passed from last insert to [Clickhouse] is greater then `CLICKHOUSE_MAX_TIME_TO_SEND` or both, then cached samples are stored in [Clickhouse], cached samples counter is reset to 0 and timer is set to current timestamp.




[//]:#

[pmacct]: <http://www.pmacct.net/>
[clickhouse]: <https://clickhouse.tech/> 
[kafka]: <https://kafka.apache.org/>
