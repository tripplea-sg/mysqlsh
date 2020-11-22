# Site Role Switch-over and Switch-back
We tested this design with the following scenarios:
1. Switch node-1 to Group Replication, Switch node-2 to InnoDB Cluster and reverse replication from node2 to node-1
2. Perform PRIMARY node failover on both node-1 and node-2
3. Switch back node-1 to InnoDB Cluster, switch back node-2 to Group Replication and reverse back replication from node1 to node-2
Caveat: Site Role Switch-over is mostly manual process and hardly automated, because moving operation to DR site is also a business decision and require DR declaration. 
## Role Switch (Node1 = Group Replication, Node2 = InnoDB Cluster)
#### A. Stop MySQL Router on Node1
```
router/stop.sh
```
#### B. Convert InnoDB Cluster on Node1 into Group Replication
Connect to PRIMARY node of InnoDB Cluster on Node1 (which is 3307), and convert to Group Replication
```
mysqlsh gradmin:grpass@test-929103:3307
mysqlsh > group_replication.adoptFromIC()
mysqlsh > group_replication.status()
```
#### C. Convert Group Replication on Node2 into InnoDB Cluster
Stop replication channel on Node2
```
mysql -uroot -h127.0.0.1 -P3307 -e "stop replica for channel 'channel1'"
```
Connect to PRIMARY node on Node2 and convert to InnoDB Cluster
```
mysqlsh gradmin:grpass@test-drive-preparation:3307
mysqlsh > group_replication.convertToIC('mycluster')
mysqlsh > var cluster = dba.getCluster()
mysqlsh > cluster.status()
```
Deploy Router connecting to InnoDB Cluster on Node2
```
mysqlrouter --bootstrap gradmin:grpass@localhost:3307 --directory router
router/start.sh
```
#### D. Create Replication Channel on PRIMARY Node of Group Replication (Node1)
Connect to 3307 on Node1 (PRIMARY), and create replication to MySQL Router
```
mysql -uroot -h127.0.0.1 -P3307
mysql > change master to master_user='repl', master_password='repl', master_host='test-drive-preparation', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > start replica for channel 'channel1';
mysql > show replica status for channel 'channel1' \G
```
#### E. Let's Test
Connect to 3307 on Node2 (PRIMARY) and create transaction:
```
mysql -uroot -h127.0.0.1 -P3307
mysql > insert into test.test values (8);
```
On Node1, check the records on all nodes:
```
mysql -uroot -h127.0.0.1 -P3306 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3307 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3308 -e "select * from test.test"
```
Record is successfully replicated from Node2 to Node1.
#### F. Let's test further with PRIMARY node failover on Node2 (InnoDB Cluster)
Change Primary Node of InnoDB Cluster on Node 2 from 3307 back to 3306
```
mysqlsh gradmin:grpass@localhost:3307 -- cluster setPrimaryInstance gradmin:grpass@localhost:3306
```
Connect to 3306 on Node2 and create transaction:
```
mysql -uroot -h127.0.0.1 -P3306 -e "insert into test.test values (9)"
```
On node1, check the records on all nodes:
```
mysql -uroot -h127.0.0.1 -P3306 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3307 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3308 -e "select * from test.test"
```
Record is successfully replicated from Node2 to Node1.
#### G. Further test with PRIMARY node failover on Node 1 (Group Replication)
Change Primary Node of Group Replication on Node 1 from 3307 to 3306
```
mysql -uroot -h127.0.0.1 -P3307 -e "restart"
```
Still on Node1, connect to instance 3306 and activate replication:
```
mysql -uroot -h127.0.0.1 -P3306
mysql > change master to master_user='repl', master_password='repl', master_host='test-drive-preparation', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > start replica for channel 'channel1';
mysql > show replica status for channel 'channel1' \G
```
Connect to 3306 on Node2 and create transaction:
```
mysql -uroot -h127.0.0.1 -P3306 -e "insert into test.test values (10)"
```
On node1, check the records on all nodes:
```
mysql -uroot -h127.0.0.1 -P3306 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3307 -e "select * from test.test"
mysql -uroot -h127.0.0.1 -P3308 -e "select * from test.test"
```
Record is successfully replicated from Node2 to Node1.
## Switch Back (Node1 = Group InnoDB Cluster, Node2 = Group Replication)
#### A. Stop MySQL Router on Node2
```
router/stop.sh
```
#### B. Convert InnoDB Cluster on Node2 into Group Replication
Connect to PRIMARY node of InnoDB Cluster on Node2 (which is 3306), and convert to Group Replication
```
mysqlsh gradmin:grpass@test-drive-preparation:3306
mysqlsh > group_replication.adoptFromIC()
mysqlsh > group_replication.status()
```
#### C. Convert Group Replication on Node1 into InnoDB Cluster
Stop replication channel on Node1
```
mysql -uroot -h127.0.0.1 -P3306 -e "stop replica for channel 'channel1'"
```
Connect to PRIMARY node on Node1 and convert to InnoDB Cluster
```
mysqlsh gradmin:grpass@test-929103:3306
mysqlsh > group_replication.convertToIC('mycluster')
mysqlsh > var cluster = dba.getCluster()
mysqlsh > cluster.status()
```
Deploy Router connecting to InnoDB Cluster on Node1
```
mysqlrouter --bootstrap gradmin:grpass@localhost:3306 --directory router --force
router/start.sh
```
#### D. Create Replication Channel on PRIMARY Node of Group Replication (Node2)
Connect to 3306 on Node2 (PRIMARY), and create replication to MySQL Router
```
mysql -uroot -h127.0.0.1 -P3306
mysql > change master to master_user='repl', master_password='repl', master_host='test-929103', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > start replica for channel 'channel1';
mysql > show replica status for channel 'channel1' \G
mysql > stop replica for channel 'channel1';
```
We encounter the following error: Last_SQL_Error: Error executing row event: 'Unknown database 'mysql_innodb_cluster_metadata'' </br>

