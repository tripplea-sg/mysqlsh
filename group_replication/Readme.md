# MySQL Shell's Extension Objects for Group Replication management
This is a community-based custom MySQL Shell Plugin for Group Replication's replication to InnoDB Cluster. 
## Plugin Installation
1. Copy init.py
2. Paste into $HOME/.mysqlsh/group_replication/init.py
## Steps to create Group Replication using Shell
Let say we have 3 instances: 
1. Node1, port 3306
2. Node2, port 3306
3. Node3, port 3306
### Configure Instance




</br>
The following functions are added into MySQL Shell's standard adminAPI: </br>
</br>
* group_replication.status(): This is to check group replication status from performance_schema.replication_group_members </br>
</br>
* group_replication.async_replication_failover(connectionStr, channelName, sourceIP, sourcePort, repl_user, repl_passwd, master_connect_retry, master_retry_count): This function creates asynchronous replication with failover (8.0.22)
</br></br>
* group_replication.convertToIC(connectionStr,clusterName): This is the function to convert group replication to InnoDB Cluster </br>
</br>
* group_replication.adoptFromIC(connectionStr): This is the function to convert InnoDB Cluster to group replication </br>
</br>
* group_replication.registerNode(connectionStr,grSeed,isPrimary): This is the function to deploy Group replication </br>
