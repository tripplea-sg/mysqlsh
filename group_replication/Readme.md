# Integrating MySQL Shell with Group Replication
This is a community-based custom MySQL Shell Plugin for Group Replication. </br>
The codes and methods here are beta version, and we have not tested against production environment. </br>
Appreciate your kind feedback.
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
mysqlsh > group_replication.rebootGRFromCompleteOutage("node1:3306,node2:3306,node3:3306")
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
mysqlsh > group_replication.convertToIC('<any_cluster_name>')
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
In future, I might work on how to automate the following processes. It's possible to build function on this.
### A. Configure Instance Node4
Connect to Node4 using mysqlsh and run configure-instance
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
### B. Clone from PRIMARY node
On PRIMARY node:
```
mysql > install plugin clone soname 'mysql_clone.so';
mysql > create user clone@'%' identified by 'clone';
mysql > grant backup_admin on *.* to clone@'%';
```
On Node4:
```
mysql > install plugin clone soname 'mysql_clone.so';
mysql > set global clone_valid_donor_list='node2:3306';
mysql > clone instance from clone@node2:3306 identified by 'clone';
```
Reconnect to Node4, and uninstall clone plugin
```
mysql > uninstall plugin clone;
```
Reconnect to PRIMARY, and uninstall clone plugin
```
mysql > uninstall plugin clone;
```
### C. Add Instance Node4
Using MySQL Shell, connect to PRIMARY node and run group_replication.addInstance()
```
mysqlsh > group_replication.addInstance("gradmin:grpass@node4:3306")
```
## Use Case
| Topic | Description |
| ------|-------------|
| [DR-Setup](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/DR-Setup) | Setup Group Replication for DR, while PROD uses InnoDB Cluster |
| [DR-Scenario-1](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/1-DR-Schenario) | Primary Node Failover Handling on PROD and DR |
| [DR-Scenario-2](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/2-DR-Scenario) | Site Switchover and Switchback between PROD and DR |
| [DR-Scenario-3](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/3-DR-Scenario) | Disaster Recovery Handling |
| [Automation](https://github.com/tripplea-sg/mysqlsh/tree/main/group_replication/Future-Development) | IC to GR Replication Broker |



