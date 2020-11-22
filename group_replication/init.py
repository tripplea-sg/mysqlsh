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

def convertToIC(clusterName):
    import mysqlsh

    shell = mysqlsh.globals.shell
    session = shell.get_session()

    result = session.run_sql("select member_role from performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + session.get_uri().replace('@',' ').split()[1].replace('localhost','127.0.0.1') + "'")
    if (result.has_data()):
        for row in result.fetch_all():
            if (str(list(row)).strip("[']") == "PRIMARY"):
                msg_output = "PRIMARY"
            else:
                msg_output = "FAILED - Instance is not PRIMARY"
    
    if (msg_output == "PRIMARY"):
        query = "drop database if exists mysql_innodb_cluster_metadata;"
        result = session.run_sql(query)

        query = "select channel_name from performance_schema.replication_connection_configuration where CHANNEL_NAME not like 'group_replication_%'"
        result = session.run_sql(query)
        if (result.has_data()):
            for row in result.fetch_all():
                channelName = str(list(row)).strip("[']")
             
                query = "stop replica for channel '" + channelName + "'"
                result = session.run_sql(query)

        dba.create_cluster(clusterName, {"adoptFromGR":"true"})
        msg_output = "Successful conversion from Group Replication to InnoDB Cluster"

    return msg_output

def adoptFromIC():
    import mysqlsh
    import time
    
    shell = mysqlsh.globals.shell
    session = shell.get_session()
    
    clusterAdmin = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[0]
    
    msg_output = "Test"
    result = session.run_sql("select member_role from performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + session.get_uri().replace('@',' ').split()[1].replace('localhost','127.0.0.1') + "'")
    if (result.has_data()):
        for row in result.fetch_all():
            if (str(list(row)).strip("[']") == "PRIMARY"):
                query = "SELECT concat(member_host,':',member_port) FROM performance_schema.replication_group_members where channel_name='group_replication_applier' and member_role<>'PRIMARY'"
                result = session.run_sql(query)
                host_list = []
                if (result.has_data()):
                    for row in result.fetch_all():
                        host_list.append(str(list(row)).strip("[']"))
                dba.get_cluster().dissolve({"interactive":"false"})  
                create()
                for item in host_list:
                    addInstance(clusterAdmin + "@" + item)
                msg_output = "Successful conversion from InnoDB Cluster to Group Replication"
            else:
                msg_output = "FAILED - Instance is not PRIMARY"
    return msg_output

def setPrimaryInstance(connectionStr):
    import mysqlsh

    shell = mysqlsh.globals.shell
    session = shell.get_session()

    hostname = connectionStr.replace("localhost", "127.0.0.1")
    if (hostname.find("@") != -1):
        hostname = hostname.replace("@", " ").split()[1]

    result = session.run_sql("SELECT member_id FROM performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + hostname + "'")
    if (result.has_data()):
        for row in result.fetch_all():
            new_primary = str(list(row)).strip("[']")
            result = session.run_sql("select group_replication_set_as_primary('" + new_primary + "')") 

    return status()


def addInstance(connectionStr):
    import mysqlsh
    import time

    shell = mysqlsh.globals.shell
    session = shell.get_session()

    clusterAdmin = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[0]
    if (connectionStr.count(':') == 1):
        clusterAdminPassword = str(input('Enter password for ' + connectionStr + ' : '))
        remote_hostname = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[1]
        remote_port = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[2]
        connectionStr = clusterAdmin + ":" + clusterAdminPassword + "@" + remote_hostname + ":" + remote_port
    else:    
        clusterAdminPassword = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[1]
        remote_hostname = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[2]
        remote_port = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[3]

    hostname = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[1]
    port = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[2] 

    query = "show variables like 'group_replication_group_seeds'"
    result = session.run_sql(query)
    if (result.has_data()):
        for row in result.fetch_all():
            gr_seed = str(list(row)).strip("['group_replication_group_seeds'").strip(", '").strip("']")
    
    gr_seed = gr_seed + "," + remote_hostname + ":" + remote_port + "1"
    result = session.run_sql("set persist group_replication_group_seeds='" + gr_seed + "'")
    result = session.run_sql("CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';")

    remote_session = shell.connect(connectionStr)
    result = remote_session.run_sql("select count(1) from information_schema.plugins where plugin_name='group_replication'")
    if (result.has_data()):
        for row in result.fetch_all():
             i = str(list(row)).strip("[']")

    if i == "0":
       result = remote_session.run_sql("INSTALL PLUGIN group_replication SONAME 'group_replication.so';")

    result = remote_session.run_sql("set sql_log_bin=off")
    result = remote_session.run_sql("drop database if exists mysql_innodb_cluster_metadata;")
    result = remote_session.run_sql("set sql_log_bin=on")
    
    result = remote_session.run_sql("set persist group_replication_group_name='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'")
    result = remote_session.run_sql("set persist group_replication_start_on_boot='ON'")
    result = remote_session.run_sql("set persist group_replication_bootstrap_group=off")
    result = remote_session.run_sql("set persist group_replication_ssl_mode='REQUIRED'")
    result = remote_session.run_sql("CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';")
    result = remote_session.run_sql("set persist group_replication_local_address='" + remote_hostname + ":" + remote_port + "1'")
    result = remote_session.run_sql("set persist group_replication_group_seeds='" + gr_seed + "'")
    result = remote_session.run_sql("START GROUP_REPLICATION;")

    session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + hostname + ":" + port)
    return status() 

def create():
    import mysqlsh

    shell = mysqlsh.globals.shell
    session = shell.get_session()
    
    clusterAdmin = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[0]
    hostname = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[1]
    port = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[2]
    result = session.run_sql("select count(1) from information_schema.plugins where plugin_name='group_replication'")
    if (result.has_data()):
        for row in result.fetch_all():
             i = str(list(row)).strip("[']")

    if i == "0":
       result = session.run_sql("INSTALL PLUGIN group_replication SONAME 'group_replication.so';")

    result = session.run_sql("set sql_log_bin=off")
    result = session.run_sql("drop database if exists mysql_innodb_cluster_metadata;")
    result = session.run_sql("set sql_log_bin=on")
    
    result = session.run_sql("set persist group_replication_group_name='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'")
    result = session.run_sql("set persist group_replication_start_on_boot='ON'")
    result = session.run_sql("set persist group_replication_bootstrap_group=off")
    result = session.run_sql("CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "' FOR CHANNEL 'group_replication_recovery';")
    result = session.run_sql("set persist group_replication_local_address='" + hostname + ":" + port + "1'")
    result = session.run_sql("set persist group_replication_group_seeds='" + hostname + ":" + port + "1'")
    result = session.run_sql("set persist group_replication_ssl_mode='REQUIRED'")
    result = session.run_sql("SET GLOBAL group_replication_bootstrap_group=ON")
    result = session.run_sql("START GROUP_REPLICATION;")
    result = session.run_sql("SET GLOBAL group_replication_bootstrap_group=OFF")

    return status()

def compareGTID(local_gtid,clusterAdmin,clusterAdminPassword,remote_host):
    import mysqlsh
    
    shell = mysqlsh.globals.shell

    session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + remote_host)
    result = session.run_sql("show variables like 'gtid_executed'")

    v_output = "NONE"
 
    if (result.has_data()):
        for row in result.fetch_all():
            remote_gtid = str(list(row)).strip("[`]").replace("'gtid_executed', '","").replace("'","")

            result2 = session.run_sql("select gtid_subset('" + remote_gtid + "','" + local_gtid + "')")
            if (result2.has_data()):
                for row2 in result2.fetch_all():
                    v_output = str(list(row2)).strip("[`]")

    return v_output

def startGRremote(clusterAdmin,clusterAdminPassword,host):
    import mysqlsh
    shell = mysqlsh.globals.shell
    session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + host)
    result = session.run_sql("start group_replication")
    return "TRUE"

def rebootGRFromCompleteOutage(ListOfHosts):
    import mysqlsh
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    clusterAdmin = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[0]
    clusterAdminPassword = str(input('Enter password for Cluster Admin : '))

    hostname = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[1]
    port = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[2] 

    result = session.run_sql("show variables like 'gtid_executed'")
    
    output_msg = "FAILED - Not executed"
    if (result.has_data()):
        for row in result.fetch_all():
            local_gtid = str(list(row)).strip("[`]").replace("'gtid_executed', '","").replace("'","")

            hostname = session.get_uri().replace("mysql://","").replace("@"," ").replace("localhost","127.0.0.1").replace(":"," ").split()[1]
            port = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[2]
    
            host_member = ListOfHosts.replace(","," ").replace("localhost","127.0.0.1").replace(hostname + ":" + port, "").split()
            v_process = "Y"
            for x in host_member:
                if (compareGTID(local_gtid, clusterAdmin, clusterAdminPassword, x) != "1"):
                    v_process = "N"
            
            session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + hostname + ":" + port)

            if (v_process == "Y"):
                result2 = session.run_sql("SET GLOBAL group_replication_bootstrap_group=ON")
                result2 = session.run_sql("START GROUP_REPLICATION;")
                result2 = session.run_sql("SET GLOBAL group_replication_bootstrap_group=OFF")
                for x in host_member:
                   remote_host = startGRremote(clusterAdmin,clusterAdminPassword,x)
                output_msg = "Group Replication is started"
                session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + hostname + ":" + port)
            else:
                output_msg = "FAILED - Instance was not a PRIMARY or not having the most GTID"
    return output_msg

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
                                        }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "convertToIC",
                                      convertToIC, {
                                       "brief":"Convert From Group Replication to InnoDB Cluster",
                                       "parameters": [
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
                                      "create",
                                      create, {
                                       "brief":"Create Group Replication"
                                        }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "addInstance",
                                      addInstance, {
                                       "brief":"Add instance to group replication",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"clusterAdmin:clusterAdminPassword@hostname:port"
                                        }
                                       ]
                                        }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "setPrimaryInstance",
                                      setPrimaryInstance, {
                                       "brief":"Set Primary Instance",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"hostname:port"
                                        }
                                       ]
                                        }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "rebootGRFromCompleteOutage",
                                      rebootGRFromCompleteOutage, {
                                       "brief":"Startup Group Replication",
                                       "parameters": [
                                       {
                                            "name":"ListOfHosts",
                                            "type":"string",
                                            "brief":"All hosts:ports within Group Replication"
                                        }
                                       ]
                                        }
                                      );
