# Integrating MySQL Shell with Group Replication

MySQL Group Replication management and utilities. </br>
A collection of functions to: </br>
- Deploy and manager MySQL Group Replication without using MySQL InnoDB Cluster (no metadata) 
- Integrate with MySQL InnoDB Cluster as Production and Group Replication as DR using async. replication 
- Support flip cluster roles, auto clone from InnoDB Cluster, async. replication failover and many more

This is a community-based custom MySQL Shell Plugin for Group Replication. </br>
The codes and methods here are beta version, and we have not tested against production environment. </br>
</br>
This method is distributed in the hope that it will be useful,
</br> but WITHOUT ANY WARRANTY; without even the implied warranty of
</br> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 

## A. List of Features

| Purpose | InnoDB Cluster Command | Group Replication Command |
| ------|-------------|---------------- |
| Configure Instance | mysqlsh > dba.configureInstance() | mysqlsh > dba.configureInstance() |
| Create / Deploy | mysqlsh > dba.createCluster('cluster_name') | mysqlsh > group_replication.create() |
| Add Instance | mysqlsh > cluster.addInstance('new_node') | mysqlsh > group_replication.addInstance('new_node') |
| Check Status | mysqlsh > cluster.status() | mysqlsh > group_replication.status() |
| Set Primary Instance | mysqlsh > cluster.setPrimaryInstance('new_primary_node') | mysqlsh > group_replication.setPrimaryInstance('new_primary_node') |
| Startup  | mysqlsh > dba.rebootClusterFromCompleteOutage() | mysqlsh > group_replication.rebootGRFromCompleteOutage() |
| SetOption | mysqlsh > cluster.setOptions(<option>) | |
| Set Instance Option | mysqlsh > cluster.setInstanceOptions(<option>) | |
| Remove Instance | mysqlsh > cluster.removeInstance('instance') | mysqlsh > group_replication.removeInstance('instance') |
| Dissolve cluster | mysqlsh > cluster.dissolve() | mysqlsh > group_replication.dissolve() |
| Convert to InnoDB Cluster | mysqlsh > dba.create_cluster('clusterName', {"adoptFromGR":True})  | mysqlsh > group_replication.convertToIC('cluster_name') |
| Convert from InnoDB Cluster to Group Replication |  | mysqlsh > group_replication.adoptFromIC() |
| Set replication from InnoDB Cluster | | mysqlsh > group_replication.setMultiClusterChannel('channel_name','router_host',router_port) |
| Start replication channel | | mysqlsh > group_replication.startMultiCluserChannel('channel_name') |
| Stop replication channel | | mysqlsh > group_replication.stopMultiClusterChannel('channel_name') |
| Edit replication channel | | mysqlsh > group_replication.editMultiClusterChannel('channel_name') |
| Show all replications status | | mysqlsh > group_replication.showChannel() | 
| Create Replication User on InnoDB Cluster | | mysqlsh > group_replication.setMultiClusterReplUser('username') |
| Flip Cluster Roles for site switchover | | mysqlsh > group_replication.flipClusterRoles('cluster_name') | 
| Implement async. auto failover | | mysqlsh > group_replication.setFailoverOnChannel('channel_name') |
| Sync group replication group seeds | | mysqlsh > group_replication.syncLocalMembers() |
| Remove auto Replication Async. Failover | | mysqlsh > group_replication.removeFailoverChannel('channel_name') |
| Auto Clone from InnoDB Cluster | | mysqlsh > group_replication.autoCloneICtoGR() |

## B. Plugin Installation
1. Copy init.py
2. Paste into $HOME/.mysqlsh/plugins/group_replication/init.py

## C.  Group Replication Deployment
### C.1. Environment
Let say we have 3 instances: 
1. Node1, port 3306
2. Node2, port 3306
3. Node3, port 3306
### C.2. Configure Instance
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
### C.3. Install a Group Replication
Login to Node1 and create Group Replication:
```
$ mysqlsh gradmin:grpass@localhost:3306
mysqlsh > group_replication.create()
```
Still on MySQL Shell, add Node2:
```
mysqlsh > group_replication.addInstance("gradmin:grpass@node2:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
Still on MySQL Shell, add Node3:
```
mysqlsh > group_replication.addInstance("gradmin:grpass@node3:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
View group replication status to ensure all nodes are ONLINE
```
mysqlsh > group_replication.status()
```
## D. Group Replication Management
### D.1. Switching Primary Node
Let say we want to switch PRIMARY node to Node2
```
mysqlsh > group_replication.setPrimaryInstance("gradmin:grpass@node2:3306")
```
Check the group replication status to ensure the result:
```
mysqlsh > group_replication.status()
```
### D.2. Reboot Group Replication From Complete Outage
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

### D.3. Convert Group Replication into InnoDB Cluster
Let say we want to run as InnoDB Cluster instead of Group Replication, then login to PRIMARY node and run below:
```
mysqlsh > group_replication.convertToIC('mycluster')
```
Check InnoDB Cluster status as follow:
```
mysqlsh > var cluster = dba.getCluster()
mysqlsh > cluster.status()
```
### D.4. Convert InnoDB Cluster to Group Replication
Let say for some reasons we want to convert InnoDB Cluster to Group Replication (i.e. for DR purposes). </br>
Login to PRIMARY node and run below:
```
mysqlsh > group_replication.adoptFromIC()
```
### D.5. Cloning Data from InnoDB Cluster into Group Replication
This is to clone InnoDB Cluster data to a Group Replication
```
mysqlsh > group_replication.autoCloneICtoGR()
```
### D.6. Setup Replication between InnoDB Cluster and Group Replication
Setup replication user on InnoDB Cluster
```
$ mysqlsh root@site-A-1:3306
mysqlsh > group_replication.setMultiClusterReplUser('{repl_username}')
```
Setup replication channel on Group Replication </br>
Two option:
- Using Router


- Without Router (min. version: 8.0.22)

## E. DR Sample and Functions 
See DR Folder
