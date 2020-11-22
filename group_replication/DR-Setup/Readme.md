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




