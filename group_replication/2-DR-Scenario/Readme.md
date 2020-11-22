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
#### B. Connect InnoDB Cluster on Node1 into Group Replication
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
### D. Create Replication Channel on PRIMARY Node of Group Replication (Node1)
Connect to 3307 on Node1 (PRIMARY), and create replication to MySQL Router
```
mysql -uroot -h127.0.0.1 -P3307
mysql > change master to master_user='repl', master_password='repl', master_host='test-drive-preparation', master_port=6446, master_auto_position=1, master_ssl=1, get_master_public_key=1 for channel 'channel1';
start replica for channel 'channel1';
show replica status for channel 'channel1' \G
```
