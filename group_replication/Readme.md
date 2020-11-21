# MySQL Shell's Extension Objects for Group Replication management
This is a community-based custom MySQL Shell Plugin for Group Replication's replication to InnoDB Cluster. </br>
The codes and methods here are beta version, and we have not tested against production environment.
## Plugin Installation
1. Copy init.py
2. Paste into $HOME/.mysqlsh/group_replication/init.py
## Steps to create Group Replication using Shell
### A. Environment
Let say we have 3 instances: 
1. Node1, port 3306
2. Node2, port 3306
3. Node3, port 3306
### B. Configure Instance
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





* group_replication.convertToIC(connectionStr,clusterName): This is the function to convert group replication to InnoDB Cluster </br>
</br>
* group_replication.adoptFromIC(connectionStr): This is the function to convert InnoDB Cluster to group replication </br>
</br>
* group_replication.registerNode(connectionStr,grSeed,isPrimary): This is the function to deploy Group replication </br>
