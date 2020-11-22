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
Connect to PRIMARY node of InnoDB Cluster on Node1 (which is 3307), and convert to Group Replication
```
mysqlsh gradmin:grpass@test-929103:3307
mysqlsh > group_replication.adoptFromIC()
mysqlsh > group_replication.status()
```
On Node2, stop replication channel 'channel1' on instance 3307
