# Disaster Recovery Setup with Replication 
## A. Schenario:
1. Two Data Center: DC1 and DC2
2. DC1 runs InnoDB Cluster
3. DC2 runs Group Replication
4. Asynchronous Replication from InnoDB Cluster to Group Replication
5. Router on DC2 for Group Replication to connect to InnoDB Cluster
## B. Environment to simulate
1. Two Compute Node in OCI
2. One Compute Node for InnoDB Cluster, and the other one for Group Replication
```
node1
IP Address  : 10.0.0.171
Hostname    : test-929103

node2
IP Address  : 10.0.0.88
Hostname    : test-drive-preparation
```
Requirement: </br>
All nodes have to be restarted with skip-slave-start. The best way is to put skip-slave-start on Option files.
3. All MySQL instances are on MySQL 8.0.22
## C. Create InnoDB Cluster on Node1
### C.1. Create Databases (3306, 3307, 3308)
```
mysqld --defaults-file=3306.cnf --initialize-insecure
mysqld --defaults-file=3307.cnf --initialize-insecure
mysqld --defaults-file=3308.cnf --initialize-insecure
```
### C.2. Start Instances 
```
mysqld_safe --defaults-file=3306.cnf &
mysqld_safe --defaults-file=3307.cnf &
mysqld_safe --defaults-file=3308.cnf &
```
### C.3. Configure Instances
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3307 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3308 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
### C.4. Create Cluster on 3306
```
mysqlsh gradmin:grpass@localhost:3306 -- dba createCluster mycluster
```
### C.5. Add Instance 3307, 3308 into cluster
```
mysqlsh gradmin:grpass@localhost:3306 -- cluster add-instance gradmin:grpass@localhost:3307 --recoveryMethod=incremental
mysqlsh gradmin:grpass@localhost:3306 -- cluster add-instance gradmin:grpass@localhost:3308 --recoveryMethod=incremental
```
### C.6. Check Cluster Status
```
mysqlsh gradmin:grpass@localhost:3306 -- cluster status
```
### C.7. Create user for replication to Group Replication
```
mysql -uroot -h127.0.0.1 -P3306 -e "create user repl@'%' identified by 'repl'; grant replication slave on *.* to repl@'%'"
```
## D. Create Group Replication on Node2
### D.1. Create Databases (3306, 3307, 3308)
```
mysqld --defaults-file=3306.cnf --initialize-insecure
mysqld --defaults-file=3307.cnf --initialize-insecure
mysqld --defaults-file=3308.cnf --initialize-insecure
```
Note: in real life schenario, it can be more complex, involving backup one of the node on Node1 and restore on 3306, 3307, 3308.
### D.2. Start Instances 
```
mysqld_safe --defaults-file=3306.cnf &
mysqld_safe --defaults-file=3307.cnf &
mysqld_safe --defaults-file=3308.cnf &
```
### D.3. Configure Instances
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3307 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3308 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
### D.4. Create Group Replication on 3306
Login to 3306 using mysqlsh
```
mysqlsh gradmin:grpass@localhost:3306 
```
Create Group Replication
```
mysqlsh > group_replication.create()
```
### D.5. Add Instance 3307, 3308 into cluster
```
mysqlsh > group_replication.addInstance("gradmin:grpass@localhost:3307")
mysqlsh > group_replication.addInstance("gradmin:grpass@localhost:3308")
```
### D.6. Check Cluster Status
```
mysqlsh > group_replication.status()
```
## E. Setup Replication between InnoDB Cluster to Group Replication
### E.1. Setup Router on Node1 Pointing to InnoDB Cluster
```
mysqlrouter --bootstrap gradmin:grpass@test-929103:3306 --directory router
router/start.sh
```
### E.2. Setup Replication on Node2 Pointing to Router
Connect to 3306 instance on Node 2
```
mysql -uroot -h127.0.0.1 -P3306
mysql> change master to master_user='repl', master_password='repl', master_host='test-929103', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > start replica for channel 'channel1';
```
### E.3. Show Replication Channel Status
```
mysql> show replica status for channel 'channel1' \G
```
Once replication is started, the Group Replication is surely having mysql_innodb_cluster_metadata schema because of the replication. </br>
This is perfectly normal and it won't affect Group Replication because the Group Replication does not use mysql_innodb_cluster_metadata schema at all. </br>
Try to load Sakila schema on InnoDB Cluster, then all databases on node2 will have sakila schema as well.

