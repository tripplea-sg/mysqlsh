# MySQL Shell's Extension Objects for Group Replication management
</br>
This is custom MySQL Shell Plugin for Group Replication's replication to InnoDB Cluster. </br>
</br>
The following functions are added into MySQL Shell's standard adminAPI: </br>
</br>
1. group_replication.status(): This is to check group replication status from performance_schema.replication_group_members </br>
</br>
2. group_replication.async_replication_failover(connectionStr, channelName, sourceIP, sourcePort, repl_user, repl_passwd, master_connect_retry, master_retry_count): This function creates asynchronous replication with failover (8.0.22)
</br></br>
3. group_replication.convertToIC(connectionStr,clusterName): This is the function to convert group replication to InnoDB Cluster </br>
</br>
4. group_replication.adoptFromIC(connectionStr): This is the function to convert InnoDB Cluster to group replication </br>
</br>
5. group_replication.registerNode(connectionStr,grSeed,isPrimary): This is the function to deploy Group replication </br>
