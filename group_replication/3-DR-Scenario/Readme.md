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
Start Replication directly to PRIMARY node of InnoDB Cluster on Node2 (use replication filter until data is sync.)
```
mysql -uroot -h127.0.0.1 -P3306
mysql > change master to master_user='repl', master_password='repl', master_host='test-drive-preparation', master_port=3306, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > change replication filter replicate_ignore_db=(mysql_innodb_cluster_metadata) for channel 'channel1';
mysql > start replica for channel 'channel1';
```
## Migrate InnoDB Cluster Metadata from InnoDB Cluster on Node2 to Group Replication on Node1
This step is optional. The reason is Group Replication on Node1 does not have mysql_innodb_cluster_metadata schema from InnoDB Cluster on Node2, hence replication filter is required. If we want to remove replication filter, then we need to migrate mysql_innodb_cluster_metadata schema from Node2 (InnoDB Cluster) to Node 1 (Group Replication)
#### A. Stop Application to prevent updates (migration of this metadata is very fast) and stop replica on Group Replication on Node 1
```
mysql > stop replica for channel 'channel1';
```
#### B. Backup mysql_innodb_cluster_metadata schema
Connect to PRIMARY node of Node2 and backup the schema using MySQL Shell
```
mysqlsh gradmin:grpass@localhost:3306 --interactive -e "util.dumpSchemas(['mysql_innodb_cluster_metadata'],'/home/opc/config/backup')"
```
#### C. Restore this backup to PRIMARY node of Group Replication on Node 1
```
mysqlsh gradmin:grpass@test-929103:3306 
mysqlsh > \sql set global local_infile=on;
mysqlsh > util.loadDump('/home/opc/config/backup')
```
#### D. Start Router on Node2 for Replication 
```
mysqlrouter --bootstrap gradmin:grpass@localhost:3306 --directory router
router/start.sh
```
#### E. Configure and Start Replication on Group Replication (node1) pointing to Router without Replication Filter
Connect to PRIMARY node on Node1
```
mysql > change master to master_user='repl', master_password='repl', master_host='test-drive-preparation', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
mysql > change replication filter replicate_ignore_db=() for channel 'channel1';
mysql > start replica for channel 'channel1';
mysql > show replica status for channel 'channel1' \G
```
