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

def addInstance(connectionStr):
    import mysqlsh
    import os
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    clusterAdmin = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[0]
    clusterAdminPassword = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[1]
    hostname = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[2]
    port = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[3]

    query = "set persist group_replication_local_address='" + hostname + ":" + port + "1'"
    result = session.run_sql(query);

    # query = "set persist group_replication_group_seeds='" + hostname + ":" + port + "1'"
    # result = session.run_sql(query);

    query = "set persist group_replication_bootstrap_group=off"
    result = session.run_sql(query);

    query = "CHANGE MASTER TO MASTER_USER='" + clusterAdmin +"', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';"
    result = session.run_sql(query);

    query = "START GROUP_REPLICATION;"
    result = session.run_sql(query);

    return status()    

def convertGR(connectionStr):
    import mysqlsh
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    clusterAdmin = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[0]
    clusterAdminPassword = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[1]
    hostname = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[2]
    port = ((connectionStr.replace(":"," ")).replace("@", " ")).split()[3]

    query = "set persist group_replication_local_address='" + hostname + ":" + port + "1'"
    result = session.run_sql(query);

    # query = "set persist group_replication_group_seeds='" + hostname + ":" + port + "1'"
    # result = session.run_sql(query);

    query = "set persist group_replication_bootstrap_group=off"
    result = session.run_sql(query);

    query = "CHANGE MASTER TO MASTER_USER='" + clusterAdmin +"', MASTER_PASSWORD='" + clusterAdminPassword + "' FOR CHANNEL 'group_replication_recovery';"
    result = session.run_sql(query);

    query = "SET GLOBAL group_replication_bootstrap_group=ON;"
    result = session.run_sql(query);

    query = "START GROUP_REPLICATION;"
    result = session.run_sql(query);

    query = "SET GLOBAL group_replication_bootstrap_group=OFF;"
    result = session.run_sql(query);

    return status()

def dissolve():
    import mysqlsh
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    query = "stop group_replication;"
    result = session.run_sql(query);

    query = "set sql_log_bin=0; "
    result = session.run_sql(query);

    query = "set global super_read_only=off;"
    result = session.run_sql(query);

    query = "set global read_only=off; "
    result = session.run_sql(query);

    query = "drop database if exists mysql_innodb_cluster_metadata;"
    result = session.run_sql(query);

    query = "set sql_log_bin=1"
    result = session.run_sql(query);

    return status()

def setGroupReplicationGroupSeed(seedStr):
    import mysqlsh
    import os
    shell = mysqlsh.globals.shell
    session = shell.get_session()

    query = "set persist group_replication_group_seeds='" + seedStr + "'"
    result = session.run_sql(query);

    return print("Group Replication Group Seed is set to " + seedStr)


if 'group_replication' in globals():
    global_obj = group_replication
else:
    # Otherwise register new global object named 'ext'
    global_obj = shell.create_extension_object()
    shell.register_global("group_replication", global_obj,
                          {"brief": "MySQL Shell extension plugins."})

#You can add sub objects to global objects by category
    shell.add_extension_object_member(global_obj,
                                      "convertGR",
                                      convertGR, {
                                       "brief":"Convert into Group Replication",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"clusterAdmin:clusterAdminPassword@hostname:port"
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
                                      "addInstance",
                                      addInstance, {
                                       "brief":"Add instance into Group Replication",
                                       "parameters": [
                                       {
                                            "name":"connectionStr",
                                            "type":"string",
                                            "brief":"clusterAdmin:clusterAdminPassword@hostname:port"
                                        }
                                        ] }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "setGroupReplicationGroupSeed",
                                      setGroupReplicationGroupSeed, {
                                       "brief":"Set Group Replication group seed",
                                       "parameters": [
                                       {
                                            "name":"seedStr",
                                            "type":"string",
                                            "brief":"group replication group seed"
                                        }
                                        ] }
                                      );

    shell.add_extension_object_member(global_obj,
                                      "dissolve",
                                      dissolve, {
                                       "brief":"Exit from the group"
                                        }
                                      );
