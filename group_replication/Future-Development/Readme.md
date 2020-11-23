# Future Development
In Oracle, Data Guard failover is manual unless we use Data Guard Broker in the middle. </br>
So, using the same concept, all scripts here are actually able to be orchestrated by the "man in the middle", I call it a "Broker". </br>
1. Broker will have repository to store information on both cluster and group replication as well as the replication
2. Broker will have active monitoring to group replication using event scheduler. Any PRIMARY node failover will trigger broker to start replication channel
3. Broker does not contain any data, so expected to be very small and easy to maintain (backup / restore)
4. Broker will have adminAPI to orchestrate site switchover
5. Broker will have adminAPI to orchestrate DR scenario
6. Using only MySQL Shell and a MySQL instance for repository
![Image of Yaktocat](https://github.com/tripplea-sg/mysqlsh/blob/main/group_replication/DR-Setup/Screenshot%202020-11-22%20at%209.15.08%20AM.png)
