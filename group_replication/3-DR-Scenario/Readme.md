# Disaster Recovery Handling
We simulate situation whereby primary site (InnoDB Cluster) is completely down and data is coming to secondary site when primary site is unavailable.
## Making Primary Site (InnoDB Cluster) unavaibale
On node-1, shutdown all databases
```
mysqladmin -uroot -h127.0.0.1 -P3306 shutdown
mysqladmin -uroot -h127.0.0.1 -P3307 shutdown
mysqladmin -uroot -h127.0.0.1 -P3308 shutdown
```
## Activate Secondary Site 
On node-2, connect to PRIMARY node of Group Replication and stop replica.
```
mysql -uroot -h127.0.0.1 -P3306
mysql > stop replica for channel 'channel1';
mysql > exit;
```
On node-2, connect to PRIMARY node using MySQL Shell and convert Group Replication to InnoDB Cluster
```
mysqlsh gradmin:grpass@test-drive-preparation:3306
mysqlsh > group_replication.convertToIC('mycluster')
mysqlsh > var cluster = dba.getCluster()
mysqlsh > cluster.status()
```
Create transactions on node2
```
mysql -uroot -h127.0.0.1 -P3306 -e "insert into test.test values (11),(12)"
mysql -uroot -h127.0.0.1 -P3306 -e "select * from test.test"
```
Setup router on Node2 for replication
```
mysqlrouter --bootstrap gradmin:grpass@localhost:3306 --directory router
router/start.sh
```
## Primary Site comes back!
On Node1, start all databases
```
mysqld_safe --defaults-file=3306.cnf
mysqld_safe --defaults-file=3307.cnf
mysqld_safe --defaults-file=3308.cnf
```
On Node1, start InnoDB Cluster
```
mysqlsh gradmin:grpass@test-929103:3306
mysqlsh > dba.rebootClusterFromCompleteOutage()
```
Change this InnoDB Cluster on Node1 to Group Replication
```
mysqlsh > group_replication.adoptFromIC()
```
Start Replication to InnoDB Cluster on Node2 (use replication filter)
```
mysql -uroot -h127.0.0.1 -P3306
mysql > change master to master_user='repl', master_password='repl', master_host='test-drive-preparation', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > change replication filter replicate_ignore_db=(mysql_innodb_cluster_metadata) for channel 'channel1';
mysql > start replica for channel 'channel1';
```
