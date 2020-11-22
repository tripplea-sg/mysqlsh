# Primary Node Failover Handling
We see two schenarios while router is up:
1. Primary Node failover on InnoDB Cluster
2. Primary Node failover on Group Replication
## A. Preparation
Create a table on instance 3306 of Node1 and insert record
```
<login to Node1>
mysql -uroot -h127.0.0.1 -P3306 -e "create database test; create table test.test (i int primary key); insert into test.test values (1)" 
```
Check this tables on all nodes (both node1 and node2)
## B. PRIMARY node failover on InnoDB Cluster
On Node1, restart instance 3306
```
mysql -uroot -h127.0.0.1 -P3306 -e "restart"
```
Check InnoDB Cluster, instance 3307 becomes a new primary
```
mysqlsh gradmin:grpass@localhost:3307 -- cluster status
```
Insert record into 3307
```
mysql -uroot -h127.0.0.1 -P3307 -e "insert into test.test values (6)"
```
On node2, check if the record is replicated
```
mysql -uroot -h127.0.0.1 -P3306 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3307 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3308 -e "select * from test.test"
```
The record is replicated from InnoDB Cluster to Group Replication, despites changing of PRIMARY node on InnoDB Cluster
## C. PRIMARY node failover on Group Replication
On Node2, restart instance 3306
```
mysql -uroot -h127.0.0.1 -P3306 -e "restart"
```
Check Group Replication, instance 3307 becomes new primary
```
mysqlsh gradmin:grpass@localhost:3307 --interactive -e "group_replication.status()"
```
Create and start replication channel on instance 3307 of Node2 
```
mysql -uroot -h127.0.0.1 -P3307 
mysql > change master to master_user='repl', master_password='repl', master_host='test-929103', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > start replica for channel 'channel1';
mysql > show replica status for channel 'channel1' \G
```
Back to Node1, insert record into 3307 
```
mysql -uroot -h127.0.0.1 -P3307 -e "insert into test.test values (7)"
```
On node2, check if the record is replicated
```
mysql -uroot -h127.0.0.1 -P3306 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3307 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3308 -e "select * from test.test"
```
The record is replicated from InnoDB Cluster to Group Replication, despites changing of PRIMARY node on Group Replication
## Conclusion
1. Any PRIMARY node failover on InnoDB Cluster will not break replication to Group Replication
2. Any PRIMARY node failover on Group Replication will require replication channel to be recreated or started in the new PRIMARY of the Group Replication
3. To address no.2 above: we can have monitoring system and perform no.2 manually. OR .., we can schedule a cronjob to check local instance. If it's PRIMARY then start replication channel. OR .. some other automation.
