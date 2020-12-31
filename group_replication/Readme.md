# MySQL Group Replication management and utilities

A collection of functions to: </br>
- Deploy and manage MySQL Group Replication without using MySQL InnoDB Cluster (no metadata) 
- Deploy and manage Asynchronous Replication between MySQL InnoDB Cluster and MySQL Group Replication
- Orchestrate the switch over process to flip MySQL InnoDB Cluster into MySQL Group Replication and vice versa 

This is a non-commercial and non-official custom MySQL Shell Plugin. </br></br>
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

## B. Use Case Diagram

![Image of Yaktocat](https://github.com/tripplea-sg/mysqlsh/blob/main/group_replication/picture/Diagram.png)

## C. Plugin Installation
1. Create directory for the plugin on local terminal: mkdir -p $HOME/.mysqlsh/plugins/group_replication 
2. Download init.py from this site and place it into $HOME/.mysqlsh/plugins/group_replication/init.py
3. Download gr.py from this site and place it into $HOME/.mysqlsh/plugins/group_replication/gr.py

## D. MySQL Group Replication Deployment
### D.1. Environment
Let say we have 3 instances, which are:
1. gr-1, port 3306
2. gr-2, port 3306
3. gr-3, port 3306
### D.2. Configure Instance
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
### D.3. Install MySQL Group Replication

![Image of Yaktocat](https://github.com/tripplea-sg/mysqlsh/blob/main/group_replication/picture/Group-Replication-Deployment.png)

Login to gr-1 and create Group Replication with the following command:
```
$ mysqlsh gradmin:grpass@gr-1:3306
mysqlsh > group_replication.create()
```
Still on the same terminal, add gr-2 into MySQL Group Replication:
```
mysqlsh > group_replication.addInstance("gradmin:grpass@gr-2:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
Still on the same terminal, add gr-3 into MySQL Group Replication:
```
mysqlsh > group_replication.addInstance("gradmin:grpass@gr-3:3306")
Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): 
```
View status to ensure databases within the Group Replication are ONLINE
```
mysqlsh > group_replication.status()
```
This PLUGIN automatically set system variable group_replication_start_on_boot to ON.
## E. MySQL Group Replication Management
### E.1. PRIMARY Node Switch
Let say we want to switch PRIMARY node from gr-1 to gr-2:
```
mysqlsh > group_replication.setPrimaryInstance("gr-2:3306")
```
### E.2. Starting Up the Group Replication
Let say all databases are OFFLINE, run the following command to ONLINE all databases:
```
mysqlsh > group_replication.rebootGRFromCompleteOutage()
```
### E.3. Making MySQL Group Replication Runs as a MySQL InnoDB Cluster
To convert a Group Replication into MySQL InnoDB Cluster, login to PRIMARY node and run below function. </br>
Assume cluster_name is 'mycluster'
```
mysqlsh > group_replication.convertToIC('mycluster')
```
### E.4. Making MySQL InnoDB Cluster Runs as a "Vanilla" Group Replication
To convert an InnoDB Cluster into MySQL Group Replication and remove mysql_innodb_cluster_metadata, login to PRIMARY node and run below function:
```
mysqlsh > group_replication.adoptFromIC()
```
### E.5. Clone or Transfer Data from a MySQL InnoDB Cluster to a Group Replication
To clone data from InnoDB Cluster to a Group Replication and make the Group Replication runs still as a Group Replication, use the following function:
```
mysqlsh > group_replication.autoCloneICtoGR()
```
This function is effective to build a new Group Replication with a BASELINE data coming from existing MySQL InnoDB Cluster.
### E.6. Asynchronous Replication between MySQL InnoDB Cluster as Source and MySQL Group Replication as Replica
#### E.6.1. On MySQL InnoDB Cluster as Source
As MySQL root user, setup replication user on the PRIMARY node of MySQL InnoDB Cluster by running the following function:
```
$ mysqlsh root@ic-1:3306
mysqlsh > group_replication.setMultiClusterReplUser('repl')
```
This command will create user 'repl' and assign all necessary privileges to support deployment and maintenance </br>
of replication between InnoDB Cluster and Group Replication </br>
#### E.6.2. On Group Replication as Replica
Two options available:
- Using Router as a gateway between InnoDB Cluster and Group Replication
```
## assume channel1 is the replication channel name
## assume router_host is the VM hostname where MySQL Router is running
## assume 6446 is the R/W port on MySQL Router

mysqlsh > group_replication.setMultiClusterChannel('channel1','router_host',6446)
```
- Without Router (min. version: 8.0.22)
```
## assume channel1 is the replication channel name
## assume ic-1 is the PRIMARY node of the MySQL InnoDB Cluster
## assume 3306 is the MySQL port

mysqlsh > group_replication.setMultiClusterChannel('channel1','ic-1',3306)

## activate the replication channel failover feature

mysqlsh > group_replication.setFailoverOnChannel('channel1')
```
IF - and ONLY IF - you want to convert replication channel from "without Router" to "using Router":
```
mysqlsh > group_replication.removeFailoverChannel('channel1')
mysqlsh > group_replication.editMultiClusterChannel('channel1','router_host',6446)
```
After this setup, a new schema will be added to both MySQL InnoDB Cluster and MySQL Group Replication </br>
Schema name is 'mysql_gr_replication_metadata', and it is used to maintain the integration between the two.
### E.7. Handling Mismatch between 'replication_group_members' and 'group_replication_group_seeds'
Since this plugin does not use metadata to maintain Group Replication as in MySQL InnoDB Cluster, </br>
it relies on 2 MySQL components to maintain the group membership:
- performance_schema.replication_group_members
- group_replication_group_seeds
```
## Command to check and compare replication_group_members and group_replication_group seeds variable:

mysqlsh > group_replication.status()

```
It is strongly adviseable to keep replication_group_members and group_replication_group_seeds in sync to avoid operational issues. </br>
However, it is not possible that due to some operation group_replication_group_seeds can possibly be out of sync with group_replication_group_members table. </br>
If group_replication_group_seeds is out of sync with group_replication_group_members table, then simply run the following on the affected nodes:
```
mysqlsh > group_replication.syncLocalMembers()
```
## F. Functions for DR Used Case
### F.1. Setup Group Replication as DR Environment
This section offers solution for DR environment using Group Replication while Production uses MySQL InnoDB Cluster
#### F.1.1. Install a New Group Replication
Follow section D2 and D3. 
#### F.1.2. Cloning BASELINE data from existing PROD InnoDB Cluster to this new Group Replication
![Image of Yaktocat](https://github.com/tripplea-sg/mysqlsh/blob/main/group_replication/picture/Clone.png)
Login to Group Replication's PRIMARY node as Cluster Admin user, and clone database from InnoDB Cluster to Group Replication:
```
mysqlsh > group_replication.autoCloneICtoGR()
```
Data from InnoDB Cluster will be copied into Group Replication, and this process is COMPLETELY ONLINE.
#### F.1.3. Setup Asynchronous Replication from MySQL InnoDB Cluster to MySQL Group Replication
Follow section E.6.
![Image of Yaktocat](https://github.com/tripplea-sg/mysqlsh/blob/main/group_replication/picture/Operation.png)
- If PRIMARY node of MySQL InnoDB Cluster as replication source is changed, replication will be automatically diverted from new PRIMARY
- If PRIMARY node of MySQL Group Replication as replica is changed, the replication has to be manually started on the new PRIMARY node of MySQL Group Replication with the following command:
```
mysqlsh > group_replication.startMultiClusterChannel('mychannel')
```
### F.2. DR Site Switch Over
This section explains how to perform site switchover, whereby Production site becomes DR and DR site becomes Production:
- MySQL InnoDB Cluster on Production site is to be converted into MySQL Group Replication
- MySQL Group Replication on DR site is to be converted into MySQL InnoDB Cluster
- Setup replication from MySQL InnoDB Cluster on DR site to MySQL Group Replication on Production site
Login into PRIMARY node of MySQL Group Replication as Cluster Admin user, and run the following command:
```
mysqlsh > group_replication.flipClusterRoles('mycluster')
```
### F.3. Real Disaster Recovery
#### F.3.1. DR site activation
During production site downtime, DR site has to be activated:
- convert MySQL Group Replication on DR site into MySQL InnoDB Cluster
```
mysqlsh > group_replication.convertToIC('mycluster')
```
- Setup Router to connect to this InnoDB Cluster for application to connect and use
#### F.3.2. Production site is back
If production site is back and available, then perform the following:
- setup a new Group Replication on Production site with no application data
```
mysqlsh > group_replication.create()
mysqlsh > group_replication.addInstance('gradmin@ic-2:3306')
mysqlsh > group_replication.addInstance('gradmin@ic-3:3306')
```
- Clone data from InnoDB Cluster on DR site into this Group Replication on Production site
```
mysqlsh > group_replication.autoCloneICtoGR()
```
- Setup and activate replication from DR site to Production site
```
## On production site:

mysqlsh > group_replication.setMultiClusterChannel('channel1','gr-1',3306)
mysqlsh > group_replication.setFailoverOnChannel('channel1')
```
#### F.3.3. Switch Back Operation to use Production Site
Plan a time to perform site switch back:
- convert MySQL InnoDB Cluster on DR site into MySQL Group Replication
- convert MySQL Group Replication on Production site into MySQL InnoDB Cluster
- Setup replication from MySQL InnoDB Cluster on Production site to MySQL Group Replication on DR site
```
```
Simply use one command to execute:
```
mysqlsh > group_replication.flipClusterRoles('mycluster')
```
