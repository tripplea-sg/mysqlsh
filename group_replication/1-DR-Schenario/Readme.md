# Primary Node Failover Handling
We see two schenarios while router is up:
1. Primary Node failover on InnoDB Cluster
2. Primary Node failover on Group Replication
## A. Preparation
Create a table on instance 3306 of Node1 and insert record
```
<login to Node1>
mysql -uroot -h127.0.0.1 -P3306 -e "create database test; create table test.test (i int primary key); insert into test.test values (1)" 
```
