# Integrating MySQL Shell with Group Replication
This is a community-based custom MySQL Shell Plugin for Group Replication. </br>
The codes and methods here are beta version, and we have not tested against production environment. </br>
Appreciate your kind feedback.
</br>
This method is distributed in the hope that it will be useful,
</br> but WITHOUT ANY WARRANTY; without even the implied warranty of
</br> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 

## Comparison

| Purpose | InnoDB Cluster Command | Group Replication Command |
| ------|-------------|---------------- |
| Configure Instance | mysqlsh > dba.configureInstance() | mysqlsh > dba.configureInstance() |
| Create / Deploy | mysqlsh > dba.createCluster('cluster_name') | mysqlsh > group_replication.create() |
| Add Instance | mysqlsh > cluster.addInstance('new_node') | mysqlsh > group_replication.addInstance('new_node') |
| Check Status | mysqlsh > cluster.status() | mysqlsh > group_replication.status() |
| Set Primary Instance | mysqlsh > cluster.setPrimaryInstance('new_primary_node') | mysqlsh > group_replication.setPrimaryInstance('new_primary_node') |
| Startup  | mysqlsh > dba.rebootClusterFromCompleteOutage() | mysqlsh > group_replication.rebootGRFromCompleteOutage() |
| Convert to InnoDB Cluster |   | mysqlsh > group_replication.convertToIC('cluster_name') |
| Convert from InnoDB Cluster to Group Replication |  | mysqlsh > group_replication.adoptFromIC() |
| Set replication from InnoDB Cluster | | mysqlsh > group_replication.replicateFromIC('channel_name','router_host',router_port) |

## Plugin Installation
1. Copy init.py
2. Paste into $HOME/.mysqlsh/plugins/group_replication/init.py
## Steps to create Group Replication using Shell
### A. Environment
Let say we have 3 instances: 
1. Node1, port 3306
2. Node2, port 3306
3. Node3, port 3306
### B. Configure Instance
Assume clusterAdmin = gradmin, clusterAdminPassword = grpass </br>
Login to Node1:
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
Login to Node2:
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
Login to Node3:
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
### C. Create Group Replication using Shell
Login to Node1 and create Group Replication:
```
$ mysqlsh gradmin:grpass@localhost:3306
mysqlsh > group_replication.create()
```
Still on MySQL Shell, add Node2:
```
mysqlsh > group_replication.addInstance("gradmin:grpass@node2:3306")
```
Still on MySQL Shell, add Node2:
```
mysqlsh > group_replication.addInstance("gradmin:grpass@node3:3306")
```
View group replication status to ensure all nodes are ONLINE
```
mysqlsh > group_replication.status()
```
## How to Switch Primary Instance to Another node
Let say we want to switch PRIMARY node to Node2
```
mysqlsh > group_replication.setPrimaryInstance("gradmin:grpass@node2:3306")
```
Check the group replication status to ensure the result:
```
mysqlsh > group_replication.status()
```
## How to reboot Group Replication From Complete Outage
Let say all nodes are down. Start all nodes, and run rebootGRFromCompleteOutage below from one of the nodes:
```
mysqlsh gradmin:grpass@node2:3306
mysqlsh > group_replication.rebootGRFromCompleteOutage()
```
Key-in the cluster Admin Password. </br>
Check group replication status
```
mysqlsh > group_replication.status()
```
When any nodes is restarted, it will autojoin to Group Replication without manual intervention </br>
This is because system variable group_replication_start_on_boot is set to ON.
## How to convert Group Replication to InnoDB Cluster
Let say we want to run as InnoDB Cluster instead of Group Replication, then login to PRIMARY node and run below:
```
mysqlsh > group_replication.convertToIC('mycluster')
```
Check InnoDB Cluster status as follow:
```
mysqlsh > var cluster = dba.getCluster()
mysqlsh > cluster.status()
```
## How to convert InnoDB Cluster to Group Replication
Let say for some reasons we want to convert InnoDB Cluster to Group Replication (i.e. for DR purposes). </br>
Login to PRIMARY node and run below:
```
mysqlsh > group_replication.adoptFromIC()
```
## How to add additional node to existing Group Replication
If we have a new database, let say node4:3306, and we want to add this database to the group. </br>
### A. Configure Instance Node4
Connect to Node4 using mysqlsh and run configure-instance
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
### B. Add Instance Node4
Using MySQL Shell, connect to PRIMARY node and run group_replication.addInstance()
```
mysqlsh > group_replication.addInstance("gradmin:grpass@node4:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
Choose "C" for clone or "I" for incremental.
## Use Case
| Topic | Description |
| ------|-------------|
| [DR-Setup](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/DR-Setup) | Setup Group Replication for DR, while PROD uses InnoDB Cluster |
| [DR-Scenario-1](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/1-DR-Schenario) | Primary Node Failover Handling on PROD and DR |
| [DR-Scenario-2](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/2-DR-Scenario) | Site Switchover and Switchback between PROD and DR |
| [DR-Scenario-3](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/3-DR-Scenario) | Disaster Recovery Handling |
| [Automation](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/Future-Development) | IC to GR Replication Broker |



