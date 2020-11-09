#    Group Replication MySQL Shell Plugin
#    A community version of operator for Group Replication 
#
#    Copyright (C) 2020  Hananto Wicaksono, hananto.wicaksono@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


def status():
    import mysqlsh
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    query = "SELECT * FROM performance_schema.replication_group_members where channel_name='group_replication_applier';"
    result = session.run_sql(query)
    
    if (result.has_data()):
        report = [result.get_column_names()]
        for row in result.fetch_all():
            report.append(list(row))
    return report

def async_replication_failover(connectionStr, channelName, sourceIP, sourcePort, repl_user, repl_passwd, master_connect_retry, master_retry_count):
    import mysqlsh

    shell = mysqlsh.globals.shell
    session = shell.connect(connectionStr)

    query = "change master to master_user='" + repl_user + "', master_host='" + sourceIP + "', master_port=" + sourcePort + ", master_auto_position=1, master_password='" + repl_passwd + "', source_connection_auto_failover=1, master_connect_retry=" + master_connect_retry + ", master_retry_count=" + master_retry_count + " for channel '" + channelName + "';"
    result = session.run_sql(query)

    i = 100
   
    session = shell.connect(repl_user + ":" + repl_passwd + "@" + sourceIP + ":" + sourcePort)
    query = "SELECT concat(member_host,':',member_port) FROM performance_schema.replication_group_members where channel_name='group_replication_applier'"
    result = session.run_sql(query)
    host_list = []
    if (result.has_data()):
        for row in result.fetch_all():
            host_list.append(str(list(row)).strip("[']"))
     
    session = shell.connect(connectionStr)
    i = 100
    print(len(host_list))
    if len(host_list) != 0:
        for item in host_list:
            hostname = (item.replace(":"," ")).split()[0]
            port = (item.replace(":"," ")).split()[1]
            
            query = "select asynchronous_connection_failover_add_source('" + channelName + "', '" + hostname + "', " + port + ", '', " + str(i) + ")"
            result = session.run_sql(query)
            i = i - 10

    if len(host_list) != 0:    
        query = "select * from mysql.replication_asynchronous_connection_failover"
        result = session.run_sql(query)
        
        if (result.has_data()):
            #  report = [result.get_column_names()]
             for row in result.fetch_all():
                 # report.append(list(row))
                 print(list(row))
                 # print(report)

    query = "start replica for channel '" + channelName + "'"
    result = session.run_sql(query)

    query = "show replica status for channel '" + channelName + "'"
    result = session.run_sql(query)

    if (result.has_data()):
        report = [result.get_column_names()]
        for row in result.fetch_all():
            report.append(list(row))
    
    return report

def convertToIC(connectionStr,clusterName):
    import mysqlsh

    shell = mysqlsh.globals.shell
    session = shell.connect(connectionStr)

    query = "drop database if exists mysql_innodb_cluster_metadata;"
    result = session.run_sql(query)

    query = "select channel_name from performance_schema.replication_connection_configuration where CHANNEL_NAME<>'group_replication_applier'"
    result = session.run_sql(query)
    if (result.has_data()):
        for row in result.fetch_all():
             channelName = str(list(row)).strip("[']")
             
             query = "stop replica for channel '" + channelName + "'"
             result = session.run_sql(query)

    dba.create_cluster(clusterName, {"adoptFromGR":"true"})

    return dba.get_cluster().status()


def adoptFromIC(connectionStr):
    import mysqlsh
    import time
    
    shell = mysqlsh.globals.shell
    session = shell.connect(connectionStr)

    clusterAdmin = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[0]
    clusterAdminPassword = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[1]
    hostname = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[2]
    port = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[3]
    local_address = hostname + ":" + port

    query = "SELECT concat(member_host,':',member_port) FROM performance_schema.replication_group_members where channel_name='group_replication_applier'"
    result = session.run_sql(query)
    gr_group_seed = ""
    host_list = []
    if (result.has_data()):
        for row in result.fetch_all():
            if gr_group_seed != "":
                gr_group_seed = gr_group_seed + ","
            grmember = str(list(row)).strip("[']")
            gr_group_seed = gr_group_seed + grmember + "1"
            host_list.append(grmember)
    user_credential = connectionStr.replace("@", " ").split()[0]
    dba.get_cluster().dissolve({"interactive":"false"})  

    query = "set persist group_replication_local_address='" + local_address + "1'"
    result = session.run_sql(query)

    query = "set persist group_replication_group_seeds='" + gr_group_seed + "'"
    result = session.run_sql(query)

    query = "set persist group_replication_bootstrap_group=off"
    result = session.run_sql(query)

    query = "CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';"
    result = session.run_sql(query)

    query = "SET GLOBAL group_replication_bootstrap_group=ON;"
    result = session.run_sql(query)

    query = "START GROUP_REPLICATION;"
    result = session.run_sql(query)

    query = "SET GLOBAL group_replication_bootstrap_group=OFF;"
    result = session.run_sql(query)

    time.sleep(10); 

    for item in host_list:
        if item != local_address:
             session = shell.connect(user_credential + "@" + item)

             query = "set persist group_replication_local_address='" + item + "1'"
             result = session.run_sql(query)

             query = "set persist group_replication_group_seeds='" + gr_group_seed + "'"
             result = session.run_sql(query)

             query = "set persist group_replication_bootstrap_group=off"
             result = session.run_sql(query)

             query = "CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';"
             result = session.run_sql(query)

             query = "START GROUP_REPLICATION;"
             result = session.run_sql(query)

             time.sleep(10)

    session = shell.connect(connectionStr)
       
    return status() 


if 'group_replication' in globals():
    global_obj = group_replication
else:
    # Otherwise register new global object named 'ext'
    global_obj = shell.create_extension_object()
    shell.register_global("group_replication", global_obj,
                          {"brief": "MySQL Shell extension plugins."})

#You can add sub objects to global objects by category

    shell.add_extension_object_member(global_obj,
                                      "adoptFromIC",
                                      adoptFromIC, {
                                       "brief":"Convert from InnoDB Cluster into Group Replication",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"clusterAdmin:clusterAdminPassword@hostname:port"
                                        }
                                        ] }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "convertToIC",
                                      convertToIC, {
                                       "brief":"Convert From Group Replication to InnoDB Cluster",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"clusterAdmin:clusterAdminPassword@hostname:port"
                                        },
                                        {
                                            "name":"clusterName",
                                            "type":"string",
                                            "brief":"Any name for your InnoDB Cluster"
                                        }
                                        ] }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "status",
                                      status, {
                                       "brief":"Check Group Replication Status"
                                        }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "async_replication_failover",
                                      async_replication_failover, {
                                       "brief":"Establish asynchronous with HA",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"clusterAdmin:clusterAdminPassword@hostname:port"
                                        },
                                        {
                                            "name":"channelName",
                                            "type":"string",
                                            "brief":"Any name for your replication channel"
                                        },
                                        {
                                            "name":"sourceIP",
                                            "type":"string",
                                            "brief":"Source hostname / IP"
                                        },
                                        {
                                            "name":"sourcePort",
                                            "type":"string",
                                            "brief":"Source port number"
                                        },
                                        {
                                            "name":"repl_user",
                                            "type":"string",
                                            "brief":"Replication user name"
                                        },
                                        {
                                            "name":"repl_passwd",
                                            "type":"string",
                                            "brief":"Replication user password"
                                        },
                                        {
                                            "name":"master_connect_retry",
                                            "type":"string",
                                            "brief":"master_connect_retry parameter"
                                        },
                                        {
                                            "name":"master_retry_count",
                                            "type":"string",
                                            "brief":"master_retry_count parameter"
                                        }
                                        ] }
                                      );
