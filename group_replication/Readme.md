# MySQL Group Replication management and utilities (MySQL 8.0.23)

A collection of functions to: </br>
- Deploy and manage MySQL Group Replication without using MySQL InnoDB Cluster (no metadata) as if deploying InnoDB Cluster
- Deploy and manage Asynchronous Replication between MySQL InnoDB Cluster and MySQL Group Replication using Plugin API Command
- Clone MySQL InnoDB Cluster to MySQL Group Replication using single PLUGIN API COMMAND
- Orchestrate the switch over process to flip MySQL InnoDB Cluster into MySQL Group Replication and vice versa using single PLUGIN API COMMAND 

## Disclaimer:
This method is distributed as Open Source in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 

## A. List of Functions

| Purpose | InnoDB Cluster (Standard AdminAPI) | Group Replication (Add-on) |
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
| Set replication from InnoDB Cluster | | mysqlsh > group_replication.setPrimaryCluster(connectionStr) |
| Start replication channel | | mysqlsh > group_replication.setPrimaryCluster(connectionStr) |
| Stop replication channel | | mysqlsh > group_replication.stopPrimaryCluster() |
| Show all replications status | | mysqlsh > group_replication.showChannel() | 
| Flip Cluster Roles for site switchover | | mysqlsh > group_replication.claimPrimaryCluster() | 
| Sync group replication group seeds | | mysqlsh > group_replication.syncLocalMembers() |

## B. Plugin Installation
1. Create directory for the plugin on local terminal: mkdir -p $HOME/.mysqlsh/plugins/group_replication 
2. Download init.py from this site and place it into $HOME/.mysqlsh/plugins/group_replication/init.py
3. Download gr.py from this site and place it into $HOME/.mysqlsh/plugins/group_replication/gr.py

## C. MySQL Group Replication Deployment
### C.1. Environment
Let say we have 3 instances, which are:
1. gr-1, port 3306
2. gr-2, port 3306
3. gr-3, port 3306
### C.2. Configure Instance
Assume our clusterAdmin user is "gradmin", and clusterAdminPassword is "grpass" </br>
Login to gr-1 and run configureInstance() as in MySQL InnoDB Cluster
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
Login to gr-2 and run configureInstance() as in MySQL InnoDB Cluster
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
Login to gr-3 and run configureInstance() as in MySQL InnoDB Cluster
```
mysqlsh -- dba configure-instance { --host=127.0.0.1 --port=3306 --user=root } --clusterAdmin=gradmin --clusterAdminPassword=grpass --interactive=false --restart=true
```
### C.3. Install MySQL Group Replication
Login to gr-1 and create Group Replication with the following command:
```
$ mysqlsh gradmin:grpass@gr-1:3306
mysqlsh > group_replication.create()
```
Still on the same terminal, add gr-2 into MySQL Group Replication:
```
mysqlsh > group_replication.addInstance("gr-2:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
Still on the same terminal, add gr-3 into MySQL Group Replication:
```
mysqlsh > group_replication.addInstance("gr-3:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
View status to ensure databases within the Group Replication are ONLINE
```
mysqlsh > group_replication.status()
```
This PLUGIN automatically set system variable group_replication_start_on_boot to ON.
## D. MySQL Group Replication Management
### D.1. PRIMARY Node Switch
Let say we want to switch PRIMARY node from gr-1 to gr-2:
```
mysqlsh > group_replication.setPrimaryInstance("gr-2:3306")
```
### D.2. Starting Up the Group Replication
Let say all databases are OFFLINE, run the following command to ONLINE all databases:
```
mysqlsh > group_replication.rebootGRFromCompleteOutage()
```
### D.3. Convert to MySQL InnoDB Cluster
To convert a Group Replication into MySQL InnoDB Cluster, login to PRIMARY node and run below function. </br>
Assume cluster_name is 'mycluster'
```
mysqlsh > group_replication.convertToIC('mycluster')
```
### D.4. Convert MySQL InnoDB Cluster to MySQL Group Replication
To convert an InnoDB Cluster into MySQL Group Replication and remove mysql_innodb_cluster_metadata, login to PRIMARY node and run below function:
```
mysqlsh > group_replication.adoptFromIC()
```
## E. Asynchronous Replication between MySQL InnoDB Cluster as Source and MySQL Group Replication as Replica
On PRIMARY node of Group Replication
```
mysqlsh > group_replication.setPrimaryCluster("ic-1:3306")
```
## F. DR Site Switch Over
This section explains how to perform site switchover, whereby Production site becomes DR and DR site becomes Production:
- MySQL InnoDB Cluster on Production site is to be converted into MySQL Group Replication
- MySQL Group Replication on DR site is to be converted into MySQL InnoDB Cluster
- Setup replication from MySQL InnoDB Cluster on DR site to MySQL Group Replication on Production site
Login into PRIMARY node of MySQL Group Replication as Cluster Admin user, and run the following command:
```
mysqlsh > group_replication.claimPrimaryCluster()
```
## G. DR site activation
During production site downtime, DR site has to be activated:
- convert MySQL Group Replication on DR site into MySQL InnoDB Cluster
```
mysqlsh > group_replication.stopPrimaryCluster()
mysqlsh > group_replication.convertToIC('mycluster')
```
When production available:
```
mysqlsh > dba.rebootClusterFromCompleteOutage()
mysqlsh > group_replicaton.adoptFromIC()
mysqlsh > group_replication.setPrimaryCluster("gr-1:3306")
```
Switch Back Operation to use Production Site from Group Replication:
```
mysqlsh > group_replication.claimPrimaryCluster()
```
