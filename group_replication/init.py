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

def i_run_sql(query, strdel, getColumnNames):
    import mysqlsh

    shell = mysqlsh.globals.shell
    session = shell.get_session()
    result = session.run_sql(query)
    list_output = []
    if (result.has_data()):
        if getColumnNames:
            list_output = [result.get_column_names()]
        for row in result.fetch_all():
             list_output.append(str(list(row)).strip(strdel))
    else:
        list_output.append("0")
    return list_output

def i_sess_identity(conn):
    import mysqlsh
    shell = mysqlsh.globals.shell

    clusterAdminPassword = ""
    if conn == "current":
        session = shell.get_session()
    else:
        session = shell.connect(conn)
        y = conn.replace(":"," ").replace("@", " ").split()
        clusterAdminPassword = y[1]

    clusterAdmin = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[0]
    # hostname = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[1]
    hostname = (i_run_sql("select @@hostname;","[`]'", False))[0]
    port = session.get_uri().replace("mysql://","").replace("@"," ").replace(":"," ").split()[2]

    return clusterAdmin, clusterAdminPassword, hostname, port

def status():
    import mysqlsh
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    report = i_run_sql("SELECT * FROM performance_schema.replication_group_members where channel_name='group_replication_applier';","",True)
    return report

def i_check_local_role():
    clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
    result = i_run_sql("select member_role from performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + hostname + ":" + port + "'","[']",False)
    return result[0]

def i_start_gr(isPRIMARY):

    if isPRIMARY:
        result = i_run_sql("SET GLOBAL group_replication_bootstrap_group=ON","",False)
        result = i_run_sql("START GROUP_REPLICATION;", "", False)
        result = i_run_sql("SET GLOBAL group_replication_bootstrap_group=OFF","",False)

    else:
        result = i_run_sql("START GROUP_REPLICATION;","",False)

def i_get_other_node():
    clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
    result = i_run_sql("show variables like 'group_replication_group_seeds'","[']",False)
    host_list = result[0].strip("group_replication_group_seeds',").strip(" '").replace(",", " ").split()
    result = []
    for node in host_list:
        if node != (hostname + ":" + port + "1"):
            result.append(node[:-1])
    return result

def i_comp_gtid(gtid1, gtid2):
    result = i_run_sql("select gtid_subset('" + gtid2 + "','" + gtid1 + "')","[`]", False)
    return result[0]

def i_get_gtid(connectionStr):
    if connectionStr != "current":
        shell.connect(connectionStr)
    result = i_run_sql("show variables like 'gtid_executed'","[`]",False)
    return result[0].replace("'gtid_executed', '","").replace("'","")

def i_drop_ic_metadata():
    result = i_run_sql("drop database if exists mysql_innodb_cluster_metadata;","[']",False)

def i_stop_other_replicas():
    result = i_run_sql("select channel_name from performance_schema.replication_connection_configuration where CHANNEL_NAME not like 'group_replication_%'","",False)
    if len(result) != 0:
        for channelName in result:
            stop_other_replicas = i_run_sql("stop replica for channel '" + channelName + "'","",False)

def i_get_gr_seed():
    result = i_run_sql("show variables like 'group_replication_group_seeds'","['group_replication_group_seeds'",False)
    return result[0].strip(", '").strip("']")

def i_set_grseed_replicas(gr_seed, clusterAdmin, clusterAdminPassword):
    result = i_run_sql("set persist group_replication_group_seeds='" + gr_seed + "'","[']",False)
    if clusterAdmin == "":
       result = i_run_sql("CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "' FOR CHANNEL 'group_replication_recovery';","[']",False) 
    else:
       result = i_run_sql("CHANGE MASTER TO MASTER_USER='" + clusterAdmin + "', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';","[']",False)

def i_get_host_port(connectionStr):
    if (connectionStr.find("@") != -1):
        connectionStr = connectionStr.replace("@", " ").split()[1]
    if (connectionStr.find("localhost") != -1 or connectionStr.find("127.0.0.1") != -1):
        clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
        port = connectionStr.replace(":"," ").split()[1]
        connectionStr = hostname + ":" + port
    return connectionStr

def setPrimaryInstance(connectionStr):
    connectionStr = i_get_host_port(connectionStr)
    new_primary = i_run_sql("SELECT member_id FROM performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + connectionStr + "'","[']",False)
    result = i_run_sql("select group_replication_set_as_primary('" + new_primary[0] + "')","'",False)
    return status()

def i_start_gr_all(connectionStr):
    clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity(connectionStr)
    i_start_gr(True)
    for node in i_get_other_node():
        shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + node)
        i_start_gr(False)
    shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + hostname + ":" + port)

def i_create_or_add(ops, connectionStr, clusterAdmin, clusterAdminPassword, group_replication_group_name, group_replication_group_seeds):
    if ops == "ADD":
        cA, cAP, local_hostname, local_port = i_sess_identity("current")
        print(clusterAdmin + ":" + clusterAdminPassword + "@" + connectionStr[:-1])
        session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + connectionStr[:-1])
    result = i_run_sql("select count(1) from information_schema.plugins where plugin_name='group_replication'","[']", False)
    if result[0] == "0":
        result = i_run_sql("INSTALL PLUGIN group_replication SONAME 'group_replication.so';","[']",False)
    result = i_run_sql("set persist group_replication_group_name='" + group_replication_group_name + "'","[']",False)
    result = i_run_sql("set persist group_replication_start_on_boot='ON'","[']",False)
    result = i_run_sql("set persist group_replication_bootstrap_group=off","[']",False)
    result = i_run_sql("set persist group_replication_ssl_mode='REQUIRED'","[']",False)
    result = i_run_sql("set persist group_replication_local_address='" + connectionStr + "'","[']",False)
    i_set_grseed_replicas(group_replication_group_seeds, clusterAdmin, clusterAdminPassword)
    if ops == "CREATE":
        i_start_gr(True)
    else:
        i_start_gr(False)
        session = shell.connect(clusterAdmin + ":" + clusterAdminPassword + "@" + local_hostname + ":" + local_port)
    return status()

def create():
    clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
    gr_seed = hostname + ":" + port + "1"
    i_create_or_add("CREATE",gr_seed,clusterAdmin, clusterAdminPassword, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", gr_seed)
    return status()

def addInstance(connectionStr):
    clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
    if (connectionStr.count(':') == 1):
        clusterAdminPassword = str(input('Enter password for ' + connectionStr + ' : '))
    else:
        clusterAdminPassword = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[1]
    gr_seed = i_get_gr_seed() + "," + i_get_host_port(connectionStr) + "1"
    i_set_grseed_replicas(gr_seed, clusterAdmin, clusterAdminPassword)
    i_create_or_add("ADD",i_get_host_port(connectionStr) + "1",clusterAdmin,clusterAdminPassword,"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", gr_seed)
    return status()

def convertToIC(clusterName):
    msg_output = "0"
    if i_check_local_role() == "PRIMARY":
        i_drop_ic_metadata()
        i_stop_other_replicas()
        dba.create_cluster(clusterName, {"adoptFromGR":True})
        msg_output = "Successful conversion from Group Replication to InnoDB Cluster"
    else:
        msg_output = "FAILED - Instance is not PRIMARY"
    return msg_output

def adoptFromIC():
    msg_output = "FAILED - Instance is not a PRIMARY"
    if i_check_local_role() == "PRIMARY":
       clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
       clusterAdminPassword = str(input('Enter Cluster Admin password: '))
       host_list = i_get_other_node()
       dba.get_cluster().dissolve({"interactive":False})
       create()
       if len(host_list) != 0:
           for secNode in host_list:
               addInstance(clusterAdmin + ":" + clusterAdminPassword + "@" + secNode)
       i_drop_ic_metadata()
       msg_output = "Successful conversion from InnoDB Cluster to Group Replication"
    return msg_output

def rebootGRFromCompleteOutage():
   clusterAdmin, clusterAdminPassword, hostname, port = i_sess_identity("current")
   clusterAdminPassword = str(input('Enter Cluster Admin Password : '))
   local_gtid = i_get_gtid("current")
   process_sts = "Y"
   for node in i_get_other_node():
       remote_gtid = i_get_gtid(clusterAdmin + ":" + clusterAdminPassword + "@" + node)
       if i_comp_gtid(local_gtid, remote_gtid) != "1":
            process_sts = "N"
   if process_sts == "Y":
       i_start_gr_all(clusterAdmin + ":" + clusterAdminPassword + "@" + hostname + ":" + port)
       print("Reboot Group Replication process is completed")
   else:
       print("Node was not a PRIMARY, try another node")
   return status()
  
if 'group_replication' in globals():
    global_obj = group_replication
else:
    # Otherwise register new global object named 'ext'
    global_obj = shell.create_extension_object()
    shell.register_global("group_replication", global_obj,
                          {"brief": "MySQL Shell extension plugins."})

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
                                      "adoptFromIC",
                                      adoptFromIC, {
                                       "brief":"Convert from InnoDB Cluster into Group Replication",
                                        }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "rebootGRFromCompleteOutage",
                                      rebootGRFromCompleteOutage, {
                                       "brief":"Startup Group Replication",
                                        }
                                      );
