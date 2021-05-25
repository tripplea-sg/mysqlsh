from mysqlsh.plugin_manager import plugin, plugin_function
import mysqlsh
import time

shell = mysqlsh.globals.shell
dba = mysqlsh.globals.dba

clusterAdminPassword = None
recovery_user = None
recovery_password = None
convert_to_gr = False
autoFlipProcess = None
remote_user = None
remote_password = None
autoCloneProcess = None
grAllowList = None
PrimaryClusterName = None

# Make report_host a prerequisite
def _check_report_host():
    result = shell.get_session().run_sql("SELECT @@report_host;").fetch_one()
    return format(result[0])

def _check_report_port():
    result = shell.get_session().run_sql("SELECT @@report_port;").fetch_one()
    return format(result[0])

def _run_sql(query, getColumnNames):
    session = shell.get_session()
    result = session.run_sql(query)
    list_output = []
    if (result.has_data()):
        if getColumnNames:
            list_output = [result.get_column_names()]
        for row in result.fetch_all():
             list_output.append(list(row))
    else:
        list_output.append("0")
    return list_output

def _session_identity(conn):
    clusterAdminPassword = ""
    if conn == "current":
        hostname = _check_report_host()
        x = shell.parse_uri(shell.get_session().get_uri())
    else:
        z = shell.get_session()
        y = shell.open_session(conn)
        shell.set_session(y)
        hostname = _check_report_host()
        shell.set_session(z)
        x = shell.parse_uri(conn)
        clusterAdminPassword = x['password']
    port = x['port']
    clusterAdmin = x['user']
    return clusterAdmin, clusterAdminPassword, str(hostname), str(port)

def _check_local_role():
    clusterAdmin, clusterAdminPassword, hostname, port = _session_identity("current")
    result = _run_sql("select member_role from performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + hostname + ":" + port + "'",False)
    return result[0][0]

def _start_group_replication(isPRIMARY):
    try:
        if isPRIMARY:
            result = _run_sql("set sql_log_bin=0;", False)
            result = _run_sql("set global super_read_only=off;", False)
            try:
                result = _run_sql("select count(1) from mysql_innodb_cluster_metadata.instances where address='" + _check_report_host() + ":" + str(_check_report_port()) + "';", False)
                if result[0][0] > 0:
                   result = _run_sql("drop database mysql_innodb_cluster_metadata;", False)
            except:
                _run_sql("show databases;", False)
            result = _run_sql("set sql_log_bin=1;", False)
            result = _run_sql("set global super_read_only=on;", False)
            try:
                result = _run_sql("set persist_only skip_slave_start=on", False)
            except:
                print("Ensure skip-slave-start is set in Option File")
            result = _run_sql("SET GLOBAL group_replication_bootstrap_group=ON",False)
            result = _run_sql("START GROUP_REPLICATION;", False)
            result = _run_sql("SET GLOBAL group_replication_bootstrap_group=OFF",False)
        else:
            try:
                result = _run_sql("set persist_only skip_slave_start=on", False)
            except:
                print("Ensure skip-slave-start is set in Option File")
            result = _run_sql("START GROUP_REPLICATION;",False)
    except:
        print("\033[1mINFO: \033[0m Unable to start group replication on this node, SKIPPED!")

def _get_other_node():
    clusterAdmin, foo, hostname, port = _session_identity("current")
    result = _run_sql("show variables like 'group_replication_group_seeds'",False)
    host_list = result[0][1].split(",")
    result = []
    for node in host_list:
        if node != ("{}:{}".format(hostname, int(port) + 10)):
            result.append(node)
    return result

def _compare_gtid(gtid1, gtid2):
    result = _run_sql("select gtid_subset('" + gtid2 + "','" + gtid1 + "')", False)
    return result[0][0]

def _get_gtid():
    result = _run_sql("show variables like 'gtid_executed'",False)
    return result[0][1]

def _drop_ic_metadata():
    result = _run_sql("set global super_read_only=off", False)
    result = _run_sql("drop database if exists mysql_innodb_cluster_metadata;",False)

def _list_all_channel():
    result = _run_sql("select channel_name from performance_schema.replication_connection_status where channel_name not like '%group_replication_%' and service_state='ON';",False)
    return result

def _stop_other_replicas():
    if len(_list_all_channel()) != 0:
        for channelName in _list_all_channel():
            result = _run_sql("stop replica for channel '" + channelName[0] + "'", False)

def _check_group_replication_recovery():
    result = _run_sql("select count(1) from performance_schema.replication_connection_status where channel_name='group_replication_recovery'", False)
    return result[0][0]

def _get_group_replication_seed():
    result = _run_sql("show variables like 'group_replication_group_seeds'",False)
    return result[0][1]

def _check_distributed_recovery_user():
    global recovery_user
    global recovery_password
    if recovery_user is None:
        recovery_user = shell.prompt("\nWhich user do you want to use for distributed recovery ? ")
        result = _run_sql("select Repl_slave_priv from mysql.user where host='%' and user='{}'".format(recovery_user),False)
        if len(result) == 0:
            answer = shell.prompt("That user doesn't exist, do you want to create it ? (Y/n) ",{'defaultValue': "Y"}).upper()
            if answer != "Y":
               # aborting
               recovery_user = None
               recovery_password = None
               return False
            recovery_password2 = "a"
            while recovery_password != recovery_password2:
                recovery_password = shell.prompt("Enter the password for {} : ".format(recovery_user),{'type': 'password'})
                recovery_password2 = shell.prompt("Confirm the password for {} : ".format(recovery_user),{'type': 'password'})
                if recovery_password != recovery_password2:
                    print("Passwords don't match, try again !")
            #check is we are super read only
            result = shell.get_session().run_sql("SELECT @@super_read_only;").fetch_one()
            if result[0] == 1:
                print("ERROR: the server is running in Super Read Only Mode, aborting !")
                recovery_user = None
                recovery_password = None
                return False
            shell.get_session().run_sql("CREATE USER {} IDENTIFIED BY '{}';".format(recovery_user, recovery_password))
            shell.get_session().run_sql("GRANT REPLICATION SLAVE ON *.* TO {};".format(recovery_user))
            shell.get_session().run_sql("GRANT BACKUP_ADMIN ON *.* TO {};".format(recovery_user))
            return True
        if result[0] == "N":
            answer = shell.prompt("User {} doesn't have REPLICATION privilege, do you want to add it ? ",{'defaultValue': "Y"}).upper()
            if answer == "N":
                # aborting
                return False
            shell.get_session().run_sql("GRANT REPLICATION SLAVE ON *.* TO {};".format(recovery_user))
        result = i_run_sql("select PRIV from mysql.global_grants where host='%' and user='{}'".format(recovery_user),"[']",False)
        if result[0] == "0":
            # We don't have backup admin priv
            answer = shell.prompt("User {} doesn't have BACKUP_ADMIN privilege, do you want to add it ? ",{'defaultValue': "Y"}).upper()
            if answer == "N":
                # aborting
                return False
            shell.get_session().run_sql("GRANT BACKUP_ADMIN ON *.* TO {};".format(recovery_user))
        recovery_password = shell.prompt("Enter the password for {}: ".format(recovery_user),{'type': 'password'})
    return True

def _set_grseed_replicas(gr_seed, clusterAdmin):
    global clusterAdminPassword
    global recovery_user
    global recovery_password
    # import time

    _run_sql("set persist group_replication_group_seeds='" + gr_seed + "'",False)
    
    if clusterAdminPassword is None:
        clusterAdminPassword = shell.prompt("\nPlease provide password for " + clusterAdmin + " : ",{'type': 'password'})

    if recovery_user is None:
        recovery_user = clusterAdmin
        recovery_password = clusterAdminPassword
        # result = _check_distributed_recovery_user()
        # if not result:
        #    return False
    # time.sleep(10)
    i = 1
    while i > 0:
       result = _run_sql("Select count(1) from performance_schema.replication_connection_status b where b.channel_name='group_replication_recovery' and service_state='ON'", False)
       i = result[0][0]
    _run_sql("CHANGE MASTER TO MASTER_USER='{}', MASTER_PASSWORD='{}' FOR CHANNEL 'group_replication_recovery';".format(recovery_user, recovery_password),False)
    return True

def _set_all_grseed_replicas(gr_seed, new_gr_seed, clusterAdmin, clusterAdminPassword):
    x=shell.get_session()
    for node in _get_other_node():
        host, port = node.split(':')

        print("\n\033[1mConfiguring node '" + host + ":" + port + ":\033[0m")
        try:
            y=shell.open_session("{}@{}:{}".format(shell.parse_uri(x.get_uri())['user'],host, int(port)-10), clusterAdminPassword)
            shell.set_session(y)
        except:
            print("\033[1mINFO: \033[0m Unable to connect to '" + host + ":" + port + "', SKIPPED!")
        _install_plugin("group_replication", "group_replication.so")
        _set_grseed_replicas(new_gr_seed, shell.parse_uri(x.get_uri())['user'] )
    shell.set_session(x)
    _set_grseed_replicas(new_gr_seed, shell.parse_uri(x.get_uri())['user'])
    print("\n\033[1mAll nodes are set to work with this new node \033[0m\n")

def _get_host_port(connectionStr):
    if (connectionStr.find("@") != -1):
        connectionStr = connectionStr.replace("@", " ").split()[1]
    if (connectionStr.find("localhost") != -1 or connectionStr.find("127.0.0.1") != -1):
        clusterAdmin, clusterAdminPassword, hostname, port = _session_identity("current")
        port = connectionStr.replace(":"," ").split()[1]
        connectionStr = hostname + ":" + port
    return connectionStr

def _start_group_replication_all(clusterAdmin, clusterAdminPassword):
    x=shell.get_session()
    _start_group_replication(True)
    for node in _get_other_node():
        if shell.parse_uri(node)["port"] > 10000:
            n = node[:-1]
        else:
            n = shell.parse_uri(node)["host"] + ":" + str(shell.parse_uri(node)["port"] - 10)
        try:
            print("\033[1mINFO: \033[0m Starting Group Replication on '" + node + "'")
            y=shell.open_session(clusterAdmin + "@" + n, clusterAdminPassword)
            shell.set_session(y)
            _start_group_replication(False)
        except:
            print("\033[1mINFO: \033[0m Unable to connect to '" + node + "', SKIPPED!")
    shell.set_session(x)

def _create_or_add(ops, connectionStr, group_replication_group_name, group_replication_group_seeds):
    global clusterAdminPassword
    global grAllowList

    clusterAdmin = shell.parse_uri(shell.get_session().get_uri())['user']
    if (ops == "ADD" or ops == "CLONE"):
        CA, CAP, local_hostname, local_port = _session_identity("current")
        x=shell.get_session()
        try:
            y = shell.open_session(connectionStr, clusterAdminPassword)
        except:
            print("\033[1mINFO: \033[0m Unable to convert '" + connectionStr + "', SKIPPED!")
            return
        clusterAdmin = shell.parse_uri(y.get_uri())['user']
        shell.set_session(y)
        if not _check_report_host():
            return
    result = _run_sql('set global super_read_only=off',False)
    try:
        result = _run_sql("set persist_only skip_slave_start=on", False)
    except:
        print("\033[1mINFO: \033[0m Ensure skip-slave-start in Option File")
    _install_plugin("group_replication", "group_replication.so")
    result = _run_sql("set persist group_replication_group_name='" + group_replication_group_name + "'",False)
    result = _run_sql("set persist group_replication_start_on_boot='ON'",False)
    result = _run_sql("set persist group_replication_bootstrap_group=off",False)
    result = _run_sql("set persist group_replication_recovery_use_ssl=1",False)
    result = _run_sql("set persist group_replication_ssl_mode='REQUIRED'",False)
    result = _run_sql("set persist group_replication_consistency='BEFORE_ON_PRIMARY_FAILOVER'", False)
    try:
        result = _run_sql("set persist group_replication_ip_allowlist = '" + grAllowList + "'",False)
    except:
       try:
         print("Set group_replication_ip_whitelist to " + ip_whitelist + "\n")
         result = _run_sql("set persist group_replication_ip_whitelist = '" + ip_whitelist + "'", False)
       except:
         print("Unable to set group_replication_ip_allowlist nor group_replication_ip_whitelist")

    hostname = _check_report_host()
    result = _run_sql("set persist group_replication_local_address='{}:{}'".format(hostname, int(shell.parse_uri(shell.get_session().get_uri())['port'])+10),False)

    result = _set_grseed_replicas(group_replication_group_seeds, clusterAdmin)

    if not result:
        return False
    if ops == "CLONE":
        print("\n\033[1mINFO:\033[0m Clone to " + connectionStr)
        if clusterAdminPassword is None:
            clusterAdminPassword = shell.prompt("Enter the password for {} : ".format(connectionStr),{'type': 'password'})
        _clone(local_hostname + ":" + local_port,clusterAdmin, clusterAdminPassword)
    if ops == "CREATE":
        _start_group_replication(True)
    else:
        if ops == "ADD":
            print("\n\033[1mINFO:\033[0m Start incremental recovery on " + connectionStr)
            _start_group_replication(False)
        shell.set_session(x)
        if ops == "CLONE":
            result = _run_sql("set sql_log_bin=0", False)
            if _check_local_role() != "PRIMARY":
                result = _run_sql("set global super_read_only=off", False)
            result = _run_sql("revoke BACKUP_ADMIN on *.* from " + clusterAdmin + ";", False)
            _remove_plugin('clone')
            if _check_local_role() != "PRIMARY":
                result = _run_sql("set global super_read_only=on", False)
            result = _run_sql("set sql_log_bin=1", False)
    return True

def _define_gr_name():
    result = _run_sql("select uuid()",False)
    return result[0][0]

def _get_gr_name():
    result = _run_sql("show variables like 'group_replication_group_name'",False)
    return result[0][1]

def _install_plugin(plugin_name, plugin_file):
    result = _run_sql("select count(1) from information_schema.plugins where plugin_name='" + plugin_name + "'",False)
    if result[0][0] == 0:
        result = _run_sql("set global super_read_only=off", False)
        result = _run_sql("INSTALL PLUGIN " + plugin_name + " SONAME '" + plugin_file + "';",False)

def _remove_plugin(plugin_name):
    result = _run_sql("select count(1) from information_schema.plugins where plugin_name='" + plugin_name + "'",False)
    if result[0] != "0":
        result = _run_sql("uninstall PLUGIN " + plugin_name + ";",False)

def _clone(source, cloneAdmin, cloneAdminPassword):
    clusterAdmin, clusterAdminPassword, hostname, port = _session_identity("current")
    _install_plugin("clone", "mysql_clone.so")
    result = _run_sql("set global clone_valid_donor_list='" + source + "';",False)
    print("Clone database is started ...")
    result = _run_sql("set global super_read_only=off;",False)
    _host = shell.parse_uri(cloneAdmin + '@' + source)['host']
    _port = shell.parse_uri(cloneAdmin + '@' + source)['port']
    result = _run_sql("clone instance from " + cloneAdmin + "@'" + _host + "':" + str(_port) + " identified by '" + cloneAdminPassword + "'", False)
    restart_status = False
    while not restart_status:
        time.sleep(10)
        shell.reconnect()
        connect_status = str(shell.status())
        if connect_status.find('Not Connected') == -1:
            if _check_local_role() != "PRIMARY":
                result = _run_sql("set global super_read_only=off", False)
            _remove_plugin('clone')
            result = _run_sql("set sql_log_bin=0", False)
            result = _run_sql("revoke BACKUP_ADMIN on *.* from " + clusterAdmin + ";", False)
            result = _run_sql("set sql_log_bin=1", False)
            if _check_local_role() != "PRIMARY":
                result = _run_sql("set global super_read_only=on", False)
            restart_status = True

def _checkIfAsyncFailoverImplemented(channel_name):
    try:
        result = _run_sql("select repl_user from mysql_gr_replication_metadata.channel;",False)
        repl_user=result[0][0]
    except:
        print("\n\033[1mINFO:\033[0m Multi Cluster replication is not set \n")
        return False
    r = _run_sql("select count(1)  from mysql.replication_asynchronous_connection_failover where channel_name='" + channel_name + "'", False)
    if r[0][0] == 0:
        return False
    else:
        return True

@plugin_function("group_replication.checkInstanceConfiguration")
def checkInstanceConfiguration():
    print("\033[1mValidating MySQL instance for use in a Group Replication...\033[0m\n")

    hostname = _check_report_host()
    if hostname == "None":
        print('\n\033[1mERROR:\033[0m Report host is not setup. Please add Report host to system variable and restart instance to continue \n')
    else:
        print('\nReport Host is set to ' + hostname + '\n')

    result = _run_sql("show grants", False)
    user_ready=False
    for i in range(len(result)):
        print(result[i][0])
        if "mysql_innodb_cluster_metadata" in result[i][0]:
            user_ready=True
    if not user_ready:
        print('\n\033[1mERROR:\033[0m This user is not ready for Cluster, please run dba.configureInstance if you have not run this \n')
        return False
    else:
        print('\nThis user is suiteable for configuring a Group Replication ... \n')

    result = _run_sql("show variables like 'server_id'",False)
    server_id=result[0][1]
    if int(server_id) < 2:
        print("\033[1mERROR:\033[0m Current server_id is " + server_id + ", please set a unique number for server_id greater than 1")
    result = _run_sql("show variables like 'gtid_mode'",False)
    gtid_mode=result[0][1]
    if gtid_mode != 'ON':
        print("\033[1mERROR:\033[0m Current GTID_MODE is " + gtid_mode + ", please set GTID_MODE to 'ON'")
    result = _run_sql("show variables like 'enforce_gtid_consistency'",False)
    enforce_gtid_consistency=result[0][1]
    if enforce_gtid_consistency != 'ON':
        print("\033[1mERROR:\033[0m Current enforce-gtid-consistency is " + enforce_gtid_consistency + ", please set enforce-gtid-consistency to 'ON'")
    if (int(server_id) > 1 and gtid_mode=='ON' and enforce_gtid_consistency=='ON'):
        print("\n\033[1mINFO:\033[0m System variables are ready for a group replication")
        print("\n\033[1mINFO:\033[0m To avoid ISSUES, you must run your instance with skip-slave-start=ON")
        print("\033[1mINFO:\033[0m Consider to put skip-slave-start on the option file (my.cnf) \n")
        return True
    else:
        return False

# Group Replication Functions

@plugin_function("group_replication.status")
def status(session=None):
    """
    Check Group Replication Status.
    This function prints the status of Group Replication
    Args:
        session (object): The optional session object used to query the
            database. If omitted the MySQL Shell's current session will be used.
    """
    try:
        dba.get_cluster()
        print("\n\033[1mINFO:\033[0m InnoDB Cluster \n")
        return
    except:
        try:
            result = _run_sql("show variables like 'group_replication_group_name'",False)
            print("\n\033[1mINFO:\033[0m Group Replication Group Name : " + result[0][1])
        except:
            print("\n\033[1mERROR:\033[0m Group Replication is not configured \n")
            return

    if session is None:
        session = shell.get_session()
        if session is None:
            print("No session specified. Either pass a session object to this "
                  "function or connect the shell to a database")
            return

    print("\n\033[1mRegistered Members on this node :\033[0m")
    print(shell.parse_uri(session.get_uri())["host"] + ":" + str(shell.parse_uri(session.get_uri())["port"]))
    try:
        host_list = _get_other_node()
        if len(host_list) != 0:
            for secNode in host_list:
                if shell.parse_uri(secNode)["port"] > 10000:
                    print(secNode[:-1])
                else:
                    print(shell.parse_uri(secNode)["host"] + ":" + str(shell.parse_uri(secNode)["port"] - 10))
    except:
        print("\033[1mINFO:\033[0m Failed to retrieve all members")
    print("\n\033[1mGroup Replication Member Status :\033[0m")
    return shell.get_session().run_sql("select * from performance_schema.replication_group_members where channel_name='group_replication_applier';")

@plugin_function("group_replication.showChannel")
def showChannel(session=None):
    """
    Group Replication's Channels' Status.
    This function prints the status of Group Replication's channels
    Args:
        session (object): The optional session object used to query the
            database. If omitted the MySQL Shell's current session will be used.
    """
    if session is None:
        session = shell.get_session()
        if session is None:
            print("No session specified. Either pass a session object to this "
                  "function or connect the shell to a database")
            return

    try:
        result = _run_sql("select channel_name, host, port, weight from mysql.replication_asynchronous_connection_failover order by channel_name, host, port",False)
        if len(result)>0:
            print("\n\033[1mReplication Asynchronous Connection Failover Nodes: \033[0m\n")
            for row in range(len(result)):
                print(result[row])
        else:
            print("\n\033[1mINFO:\033[0m Replication Asynchronous Connection Failover is not IMPLEMENTED !\n")
    except:
        print("\n\033[1mINFO:\033[0m Replication Asynchronous Connection Failover requires minimum 8.0.22\n")

    print("\n\033[1mChannel Status: \033[0m\n")
    return shell.get_session().run_sql("Select a.channel_name, a.host, a.port, a.user, b.service_state Replica_IO, c.service_state Replica_SQL from performance_schema.replication_connection_configuration a, performance_schema.replication_connection_status b, performance_schema.replication_applier_status c where a.channel_name=b.channel_name and a.channel_name=c.channel_name")

@plugin_function("group_replication.setPrimaryInstance")
def setPrimaryInstance(connectionStr):
    """
    Set PRIMARY instance for the Group Replication.
    This function sets a node in the Group Replication to be a PRIMARY instance 
    Args:
        connectionStr (string): uri clusterAdmin:clusterAdminPassword@hostname:port
    """
    global clusterAdminPassword

    if not checkInstanceConfiguration():
        return "Please login using the Cluster Admin"

    x = shell.get_session()
    connectionStr = _get_host_port(connectionStr)

    clusterAdmin = shell.parse_uri(shell.get_session().get_uri())['user']

    if clusterAdminPassword is None:
            clusterAdminPassword = shell.prompt('Please provide password for ' + clusterAdmin + ': ',{"type":"password"})

    try:
        y=shell.open_session(clusterAdmin + "@" + connectionStr, clusterAdminPassword)
        shell.set_session(y)
    except:
        shell.set_session(x)
        print('ERROR: Password is not valid !')
        return

    shell.set_session(x)

    if _check_local_role() != "PRIMARY":
        current_primary = _run_sql("select concat(member_host,':',member_port) from performance_schema.replication_group_members where channel_name='group_replication_applier' and member_role='PRIMARY'", False)
        try:
            c=shell.open_session(clusterAdmin + '@' + current_primary[0][0], clusterAdminPassword)
            shell.set_session(c)
        except:
            shell.set_session(x)
            print('ERROR: unable to connect to PRIMARY server !')
            return        

    new_primary = _run_sql("SELECT member_id FROM performance_schema.replication_group_members where channel_name='group_replication_applier' and concat(member_host,':',member_port)='" + connectionStr + "'",False)
    
    try:
        start_channel_name=[]
        if len(_list_all_channel()) != 0:
            for channel_name in _list_all_channel():
                start_channel_name.append(list(channel_name))
                result = _run_sql("stop replica for channel '" + channel_name[0] + "'", False)
        result = _run_sql("select group_replication_set_as_primary('" + new_primary[0][0] + "')",False)
        shell.set_session(y)
        if len(start_channel_name) != 0:
            for channel_name in start_channel_name:
                print(channel_name[0])
                result = _run_sql("start replica for channel '" + channel_name[0] + "'", False)
    except:
        print("ERROR: the server is not part of Group Replication or is not running or unable to connect to the current PRIMARY server, aborting !")
    shell.set_session(x)

    return status()

@plugin_function("group_replication.removeInstance")
def removeInstance(connectionStr):
    """
    Remove instance from group replication
    This function remove an instance from an existing Group Replication
    Args:
        connectionStr (string): uri clusterAdmin:clusterAdminPassword@hostname:port
    """
    global clusterAdminPassword
    global autoFlipProcess

    if autoFlipProcess is None:
        p = shell.prompt("\nDo you want to remove '" + connectionStr + "' from the Group Replication ? (y/N) ",{'defaultValue': "N"}).upper()
    else:
        p = "Y"
    
    if p == "N":
        return

    clusterAdmin, foo, hostname, port = _session_identity("current")
    if clusterAdminPassword is None:
        try:
           if shell.parse_uri(connectionStr)['password'] == "":
              clusterAdminPassword = shell.prompt("Please provide the password for \033[96m'" + clusterAdmin + "'\033[0m : ", {"type":"password"}) 
           else:
              clusterAdminPassword=shell.parse_uri(connectionStr)['password']
        except:
           clusterAdminPassword = shell.prompt("Please provide the password for \033[96m'" + clusterAdmin + "'\033[0m : ", {"type":"password"})

    if p == "Y":
        connectionStr = _get_host_port(connectionStr)
        print("\n\033[1mINFO:\033[0m Removing instance '" + connectionStr + "'")
        local_instance = shell.get_session()
        try:
            remote_instance = shell.open_session(clusterAdmin + "@" + connectionStr, clusterAdminPassword)
            shell.set_session(remote_instance)
            report_host = _check_report_host()
            report_port = str(_check_report_port())
            shell.set_session(local_instance)
            
            check = _run_sql("select count(1) from performance_schema.replication_group_members where channel_name='group_replication_applier' and member_host='" +  report_host + "' and member_port=" + report_port, False)
            if check != "0":
                shell.set_session(remote_instance)
                result = _run_sql("stop group_replication",False)
                result = _run_sql("reset persist group_replication_group_name",False)
                result = _run_sql("reset persist group_replication_start_on_boot",False)
                result = _run_sql("reset persist group_replication_bootstrap_group",False)
                result = _run_sql("reset persist group_replication_local_address",False)
                result = _run_sql("reset persist group_replication_group_seeds",False)
                try:
                    result = _run_sql("RESTART", False)
                except:
                    print("\n\033[1mERROR:\033[0m Restart server failed (mysqld is not managed by supervisor process)\n")
            shell.set_session(local_instance)
            for node in _get_other_node():
                try:
                    if shell.parse_uri(node)["port"] > 10000:
                        n = node[:-1]
                    else:
                        n = shell.parse_uri(node)["host"] + ":" + str(shell.parse_uri(node)["port"] - 10)

                    if n != report_host + ":" + report_port:
                        print("\n\033[96m*****\033[0m\n")
                        print("\033[1mINFO:\033[0m \033[96mResync Group Replication Members on " + n + "\033[0m")
                        y=shell.open_session(clusterAdmin + "@" + n, clusterAdminPassword)
                        shell.set_session(y)
                        syncLocalMembers()
                except:
                    print("\033[1mINFO:\033[0m Unable to connect to '" + n + "', SKIPPED\n!")

            print("\n\033[96m*****\033[0m\n")
            print("\033[1mINFO:\033[0m Resync \033[96mLocal\033[0m Group Replication Members")
            shell.set_session(local_instance)
            syncLocalMembers()
        except:
            print("\n\033[1mERROR:\033[0m Unable to connect to " + connectionStr)
            shell.set_session(local_instance)
    else:
        print("\n\033[1mINFO:\033[0m Instance removal is cancelled \n")


@plugin_function("group_replication.dissolve")
def dissolve():
  """
  Dissolve group replication
  This function removes existing Group Replication
  """
  global clusterAdminPassword
  global autoFlipProcess

  import time

  if not checkInstanceConfiguration():
    print('\n\033[1mERROR:\033[0m Instance is not a Group Replciation or User is not a cluster admin\n')
    return
  try:
    x = shell.get_session()
    clusterAdmin, foo, hostname, port = _session_identity("current")
    if clusterAdminPassword is None:
        clusterAdminPassword = shell.prompt("Please provide the password for \033[96m'" + clusterAdmin + "'\033[0m : ", {"type":"password"})
    for node in _get_other_node():
       try:
           if shell.parse_uri(node)["port"] > 10000:
               n = node[:-1]
           else:
               n = shell.parse_uri(node)["host"] + ":" + str(shell.parse_uri(node)["port"] - 10)
           removeInstance(clusterAdmin + "@" + n)
       except:
           print("\033[1mINFO: \033[0m Unable to connect to '" + node + "', SKIPPED!")
    shell.set_session(x)
    print("We need to RESTART MySQL ...")
    removeInstance(str(x).strip("<ClassicSession:>"))
    print("Waiting for MySQL restart ...")
    restart_status = False
    while not restart_status:
        time.sleep(10)
        shell.reconnect()
        connect_status = str(shell.status())
        if connect_status.find('Not Connected') == -1:
            restart_status = True
  except:
     print("\033[1mERROR: \033[0m This instance is not part of a group replication")

@plugin_function("group_replication.create")
def create():
    """
    Create MySQL Group Replication
    This function creates a Group Replication environment
    """
    global grAllowList
    global convert_to_gr
    global autoFlipProcess

    if not convert_to_gr:
        try:
            result = _run_sql("show variables like 'group_replication_group_name'",False)
            z = result[0][1]
            if z != "":
                print("\n\033[1mINFO:\033[0m Group Replication Group Name : " + z)
                print("\n\033[1mERROR:\033[0m Unable to create on existing Group Replication \033[0m\n")
                return
        except:
            print("\n")

    if not checkInstanceConfiguration():
        return
    else:
        if autoFlipProcess is None:
            print("\n\033[1mConfiguring Group Replication ... \033[0m\n")
            print("Please ensure you started this instance with skip-slave-start")
            x=shell.prompt("Do you want to continue (Y/n): ",{"defaultValue":"Y"}).upper()
            if x != "Y":
                print("\n\033[1mGroup Replication Creation Aborted !\033[0m")
                return
            else:
                if grAllowList is not None:
                    p = shell.prompt("\nDo you want to set group_replication_ip_allowlist to " + grAllowList + " ? (Y/n) ",{'defaultValue': "Y"}).upper()
                    if p == "N":
                        grAllowList = shell.prompt('Please provide group_replication_ip_allowlist :')
                else:
                    grAllowList = shell.prompt('Please provide group_replication_ip_allowlist :')
    if _check_report_host():
        clusterAdmin, foo, hostname, port = _session_identity("current")
        gr_seed = "{}:{}".format(hostname, int(port) + 10)
        try:
            result = _create_or_add("CREATE",gr_seed, _define_gr_name(), gr_seed)
            print("\n\033[1mGroup Replication Creation is successful ! \033[0m\n")
            return status()
        except:
            print("\n\033[1mERROR:\033[0m Group Replication Creation Aborted ! \n")
            return
    else:
        print("\n\033[1mERROR:\033[0m Failed in checking report host. Group Replication Creation Aborted !\n")

@plugin_function("group_replication.addInstance")
def addInstance(connectionStr):
    """
    Add instance to group replication
    This function adds an instance to an existing Group Replication
    Args:
        connectionStr (string): uri clusterAdmin:clusterAdminPassword@hostname:port
    """
    global convert_to_gr
    global clusterAdminPassword
    global autoFlipProcess
    global autoCloneProcess
    global grAllowList
    global clusterAdmin

    x = shell.get_session()

    try:
        clusterAdminPassword=shell.parse_uri(connectionStr)['password']
        y = shell.open_session(connectionStr)
        shell.set_session(y)
    except:
        try:
            clusterAdmin = shell.parse_uri(shell.get_session().get_uri())['user']
            connectionStr = clusterAdmin + "@" + _get_host_port(connectionStr)
            if clusterAdminPassword is None:
                clusterAdminPassword = shell.prompt("Please provide the password for " + clusterAdmin + ": ",{'type': 'password'})
            y = shell.open_session(connectionStr, clusterAdminPassword)
            shell.set_session(y)
        except:
            print("\n\033[1mERROR:\033[0m Unable to connect to '\033[1m" + connectStr + "\033[0m'\n")
            return

    if not convert_to_gr:
        try:
            result = _run_sql("show variables like 'group_replication_group_name'",False)
            z = result[0][1]
            if z != "":
                print("\n\033[1mINFO:\033[0m Group Replication Group Name : " + z)
                print("\n\033[1mERROR:\033[0m Unable to add instance on existing Group Replication \033[0m\n")
                shell.set_session(x)
                return
        except:
            print("\n")

    if not checkInstanceConfiguration():
        print("\n\033[1mERROR:\033[0m Group Replication Adding Instance Aborted ! \033[0m\n")
        shell.set_session(x)
        return

    shell.set_session(x)
    print("\n\033[1mConfiguring Group Replication ... \033[0m\n")
    print("Please ensure you started this instance with skip-slave-start")

    if autoFlipProcess is None:
        x=shell.prompt("Do you want to continue (Y/n): ",{"defaultValue":"Y"}).upper()
        if x != "Y":
            print("\n\033[1mGroup Replication Adding Instance Aborted !\033[0m")
            return
        if grAllowList is not None:
            p = shell.prompt("\nDo you want to set group_replication_ip_allowlist to " + grAllowList + " ? (Y/n) ",{'defaultValue': "Y"}).upper()
            if p == "N":
                grAllowList = shell.prompt('Please provide group_replication_ip_allowlist : ')
        else:
            grAllowList = shell.prompt('Please provide group_replication_ip_allowlist :') 

    clusterAdmin, foo, hostname, port = _session_identity("current")

    print("A new instance will be added to the Group Replication. Depending on the amount of data on the group this might take from a few seconds to several hours. \n")

    if autoFlipProcess is None:
        clone_sts = shell.prompt("Please select a recovery method [C]lone/[I]ncremental recovery/[A]bort (default Clone): ").upper()
    else:
        #if autoCloneProcess is None:
        clone_sts = "I"
        # else:
        #    clone_sts = "C"

    if (clone_sts == "C" or clone_sts == "" or clone_sts == " "):
        clone_sts = "CLONE"
    else:
        if clone_sts == "I":
            clone_sts = "ADD"
        else:
            clone_sts = "A"
            print("Adding instance is aborted")
    if clone_sts != "A":
        old_gr_seed = _get_group_replication_seed()
        add_gr_node = connectionStr
        add_gr_seed = "{}:{}".format(_get_host_port(connectionStr).split(':')[0], int(_get_host_port(connectionStr).split(':')[1])+10)
        if old_gr_seed.find(add_gr_seed) != -1:
            new_gr_seed = old_gr_seed
        else:
            new_gr_seed = old_gr_seed + "," + add_gr_seed
        if clone_sts == "CLONE":
            if _check_local_role() != "PRIMARY":
                result = _run_sql("set global super_read_only=off;", False)
            result = _run_sql("set sql_log_bin=0", False)
            result = _run_sql("grant BACKUP_ADMIN on *.* to " + clusterAdmin + ";", False)
            result = _run_sql("set sql_log_bin=1", False)
            _install_plugin("clone", "mysql_clone.so")
            if _check_local_role() != "PRIMARY":
                result = _run_sql("set global super_read_only=on;", False)
        x=shell.get_session()
        shell.set_session(x)
        _set_all_grseed_replicas(old_gr_seed, new_gr_seed, clusterAdmin, clusterAdminPassword)
        _create_or_add(clone_sts,add_gr_node,_get_gr_name(), new_gr_seed)
    return status()

@plugin_function("group_replication.syncLocalMembers")
def syncLocalMembers():
    """
    Synchronize group_replication_group_seeds variable as the plugin metadata
    This function makes group_replication_group_seeds consistent with performance_schema.replication_group_members
    """
    result = _run_sql("select concat(member_host,':',member_port) from performance_schema.replication_group_members where channel_name='group_replication_applier'", False)
    if len(result) != 0:
        group_replication_group_members=''
        for node in result:
            group_replication_group_members=group_replication_group_members + ',' + shell.parse_uri(node[0])["host"] + ':' + str(shell.parse_uri(node[0])["port"] + 10)
        result = _run_sql("set persist group_replication_group_seeds='" + group_replication_group_members[1:] + "'",False)
        print("\n\033[1mINFO:\033[0m Group Replication members is synched")
    return status()

@plugin_function("group_replication.convertToIC")
def convertToIC():
    result = _run_sql("select channel_name from performance_schema.replication_applier_configuration where channel_name not like '%group%replication%' limit 1", False)
    if len(result) != 0:
        print("Convert to InnoDB Cluster with cluster name = " + result[0][0])
        clusterName=result[0][0]
    else:
        print("\nIf this group replication is a DR cluster with an InnoDB Cluster running on PROD, \n")
        print("WARNING : It is important to set InnoDB Cluster name to be the same as the original cluster name \n")
        clusterName=shell.prompt("Please provide InnoDB Cluster name : ")
    if clusterName != "":
        GRToIC(clusterName)

def GRToIC(clusterName):
    """
    Convert From Group Replication to InnoDB Cluster
    This function converts a Group Replication environment to MySQL InnoDB Cluster
    Args:
        clusterName (string): Any name for your InnoDB Cluster
    """
    x=shell.get_session()
    if _check_local_role() != "PRIMARY":
        current_primary = _run_sql("select concat(member_host,':',member_port) from performance_schema.replication_group_members where channel_name='group_replication_applier' and member_role='PRIMARY'",False)
        cp_user=shell.prompt('Please provide user to connect to current PRIMARY node (' + current_primary[0][0] + '): ')
        try:
            c=shell.open_session(cp_user + '@' + current_primary[0][0])
            shell.set_session(c)
        except:
            shell.set_session(x)
            print('ERROR: unable to connect to PRIMARY server !')

    msg_output = "0"
    _stop_other_replicas()
    _drop_ic_metadata()
    dba.create_cluster(clusterName, {"adoptFromGR":True, "force":True, "consistency":"BEFORE_ON_PRIMARY_FAILOVER"})
    msg_output = "Successful conversion from Group Replication to InnoDB Cluster"
    shell.set_session(x)
    return msg_output

@plugin_function("group_replication.adoptFromIC")
def adoptFromIC():
    """
    Convert From InnoDB Cluster to native Group Replication
    This function converts a MySQL InnoDB Cluster to a native Group Replication environment
    """
    global convert_to_gr
    global autoFlipProcess
    global clusterAdminPassword

    try:
        dba.get_cluster()
    except:
        print('\n\033[1mINFO:\033[0m Failed to convert, this is not an InnoDB Cluster\n')
        return

    if not autoFlipProcess:
        p = shell.prompt("\nAre you sure to convert this cluster into Group Replication ? (y/N) ",{'defaultValue': "N"}).upper()
        if p == "N":
            print("\033[1mINFO: \033[0m Operation is aborted !\n")
            return

    c_primary=""
    x=shell.get_session()
    if _check_local_role() != "PRIMARY":
        current_primary = _run_sql("select concat(member_host,':',member_port) from performance_schema.replication_group_members where channel_name='group_replication_applier' and member_role='PRIMARY'",False)
        cp_user=shell.prompt('Please provide user to connect to current PRIMARY node (' + current_primary[0][0] + '): ')
        try:
            c=shell.open_session(cp_user + '@' + current_primary[0][0])
            c_primary=current_primary[0][0]
            shell.set_session(c)
        except:
            shell.set_session(x)
            print('ERROR: unable to connect to PRIMARY server !')

    clusterAdmin, foo, hostname, port = _session_identity("current")

    host_list = _get_other_node()

    dba.get_cluster().dissolve({"interactive":False})
    convert_to_gr = True
    print("\n\033[96m*****\033[0m\n")
    print("\033[96mINFO: Create Group Replication on " + c_primary + "\033[0m")
    create()
    convert_to_gr = False
    if len(host_list) != 0:
        for secNode in host_list:
            print("\n\n\033[96m*****\033[1m\n")
            if shell.parse_uri(secNode)["port"] > 10000:
                try:
                    print('\033[1mINFO:\033[0m \033[96mAdding instance ' + secNode[:-1] +"\033[0m")
                    convert_to_gr = True
                    addInstance(clusterAdmin + "@" + secNode[:-1])
                    convert_to_gr = False
                except:
                    print("\033[1mINFO: \033[0m Unable to convert '" + node + "', SKIPPED!")
            else:
                try:
                    print('\033[1mINFO:\033[0m \033[96mAdding instance ' + shell.parse_uri(secNode)["host"] + ":" + str(shell.parse_uri(secNode)["port"] - 10) + "\033[0m")
                    convert_to_gr=True
                    addInstance(clusterAdmin + "@" + shell.parse_uri(secNode)["host"] + ":" + str(shell.parse_uri(secNode)["port"] - 10))
                    convert_to_gr=False
                except:
                    print("\033[1mINFO: \033[0m Unable to convert '" + node + "', SKIPPED!")
    _drop_ic_metadata()
    msg_output = "Successful conversion from InnoDB Cluster to Group Replication\n"
    shell.set_session(x)
    return msg_output

@plugin_function("group_replication.rebootGRFromCompleteOutage")
def rebootGRFromCompleteOutage():
   """
   Startup Group Replication
   This function starts Group Replication
   """
   if not checkInstanceConfiguration():
       return

   clusterAdmin, clusterAdminPassword, hostname, port = _session_identity("current")
   print("\nUsername for distributed recovery is " + clusterAdmin)
   clusterAdminPassword = shell.prompt('Please provide password for ' + clusterAdmin + ': ',{"type":"password"})
   x=shell.get_session()

   try:
       y=shell.open_session(clusterAdmin + "@" + hostname + ":" + port, clusterAdminPassword)
       shell.set_session(y)
   except:
       print("\n\033[1mERROR:\033[0m Password mismatch \033[0m\n")
       return

   local_gtid = _get_gtid()
   process_sts = "Y"
   for node in _get_other_node():
       try:
           if shell.parse_uri(node)["port"] > 10000:
               n = node[:-1]
           else:
               n = shell.parse_uri(node)["host"] + ":" + str(shell.parse_uri(node)["port"] - 10)
           y=shell.open_session(clusterAdmin + "@" + n, clusterAdminPassword)
           shell.set_session(y)
           remote_gtid = _get_gtid()
           if _compare_gtid(local_gtid, remote_gtid) != 1:
               process_sts = "N"
       except:
           print("\033[1mINFO: \033[0m Unable to connect to '" + node + "', SKIPPED!")

   if process_sts == "Y":
       shell.set_session(x)
       print("This node is suitable to start Group Replication")
       print("Process may take a while ...")
       _start_group_replication_all(clusterAdmin, clusterAdminPassword)
       print("Reboot Group Replication process is completed")
   else:
       print("Node was not a PRIMARY, try another node")
   return status()

@plugin_function("group_replication.setPrimaryCluster")
def setPrimaryCluster(conn):
    global clusterAdmin
    global clusterAdminPassword

    if checkInstanceConfiguration():
        
        if _check_local_role() != "PRIMARY":
            print("\nPlease do on PRIMARY node .. \n")
            return

        try:
            dba.get_cluster()
            v_continue = 0
        except:
            v_continue = 1

        if v_continue == 0:
            print('\n\033[1mERROR:\033[0m Set Primary Cluster replication has to be done on Group Replication \n')
            return

        clusterAdmin = shell.parse_uri(shell.get_session().get_uri())['user'] 
        if clusterAdminPassword is None:
            clusterAdminPassword = shell.prompt('Please provide password for ' + clusterAdmin + ': ',{"type":"password"})
        primaryHost = shell.parse_uri(conn)['host']
        primaryPort = str(shell.parse_uri(conn)['port'])
        x=shell.get_session()
        try:
            y=shell.open_session(clusterAdmin + "@" + primaryHost + ":" + primaryPort, clusterAdminPassword)
            shell.set_session(y)
            cluster_nodes = _run_sql("select a.cluster_name, b.address from mysql_innodb_cluster_metadata.clusters a, mysql_innodb_cluster_metadata.instances b order by b.instance_id", False)
            PrimaryClusterName = cluster_nodes[0][0] 
        except:
            shell.set_session(x)
            print("\n\033[1mERROR:\033[0m Primary Cluster Host cannot be contacted \033[0m\n")
            return
        shell.set_session(x)

        try:
            result = _run_sql("stop replica for channel '" + PrimaryClusterName + "'", False)
        except:
            print("\n\033[1mINFO:\033[0m Create a new replication to PRIMARY Cluster \033[0m\n")    
        
        connectionFailover = True
        try:
            result = _run_sql("change master to master_host='" + primaryHost + "', master_port=" + primaryPort + ", master_user='" + clusterAdmin + "', master_password='" + clusterAdminPassword + "', master_ssl=1, master_auto_position=1, get_master_public_key=1, SOURCE_CONNECTION_AUTO_FAILOVER=1, master_connect_retry=3, master_retry_count=3 for channel '" + PrimaryClusterName + "'", False)
            for i in range(len(cluster_nodes)):
                result = _run_sql("select asynchronous_connection_failover_add_source('" + PrimaryClusterName + "','" + shell.parse_uri(cluster_nodes[i][1])['host'] + "'," + str(shell.parse_uri(cluster_nodes[i][1])['port']) + ",''," + str(90-10*i) + ")", False)

        except:
            connectionFailover = False
            result = _run_sql("change master to master_host='" + primaryHost + "', master_port=" + primaryPort + ", master_user='" + clusterAdmin + "', master_password='" + clusterAdminPassword + "', master_ssl=1, master_auto_position=1, get_master_public_key=1 for channel '" + PrimaryClusterName + "'", False)
        
        result = _run_sql("start replica for channel '" + PrimaryClusterName + "'", False)

        try:
            for node in _get_other_node():
                try:
                    if shell.parse_uri(node)["port"] > 10000:
                        n = node[:-1]
                    else:
                        n = shell.parse_uri(node)["host"] + ":" + str(shell.parse_uri(node)["port"] - 10)
                    y=shell.open_session(clusterAdmin + "@" + n, clusterAdminPassword)
                    shell.set_session(y)
                    if connectionFailover:
                        result = _run_sql("change master to master_host='" + primaryHost + "', master_port=" + primaryPort + ", master_user='" + clusterAdmin + "', master_password='" + clusterAdminPassword + "', master_ssl=1, master_auto_position=1, get_master_public_key=1, SOURCE_CONNECTION_AUTO_FAILOVER=1, master_connect_retry=3, master_retry_count=3 for channel '" + PrimaryClusterName + "'", False)
                        for i in range(len(cluster_nodes)):
                            result = _run_sql("select asynchronous_connection_failover_add_source('" + PrimaryClusterName + "','" + shell.parse_uri(cluster_nodes[i][1])['host'] + "'," + str(shell.parse_uri(cluster_nodes[i][1])['port']) + ",''," + str(90-10*i) + ")", False)
                    else:
                        result = _run_sql("change master to master_host='" + primaryHost + "', master_port=" + primaryPort + ", master_user='" + clusterAdmin + "', master_password='" + clusterAdminPassword + "', master_ssl=1, master_auto_position=1, get_master_public_key=1 for channel '" + PrimaryClusterName + "'", False)
                except:
                    print("\033[1mINFO: \033[0m Unable to connect to '" + node + "', SKIPPED!")
            shell.set_session(x)
            result = _run_sql("set global super_read_only=on", False)
        except:
            print("\n\033[1mERROR:\033[0m Instance is not ready for Group Replication\n")
    else:
        print("\n\033[1mERROR:\033[0m Instance is not ready for Group Replication\n")
    return showChannel()

@plugin_function("group_replication.stopPrimaryCluster")
def stopPrimaryCluster():
    
    if checkInstanceConfiguration():
        try:
            result = _run_sql("select distinct cluster_name from mysql_innodb_cluster_metadata.clusters", False)    
            PrimaryClusterName = result[0][0]
            result = _run_sql("stop replica for channel '" + PrimaryClusterName + "'", False)
        except:
            print("\n\033[1mERROR:\033[0m No PRIMARY Cluster is available\n")
    return showChannel()

@plugin_function("group_replication.claimPrimaryCluster")
def claimPrimaryCluster():
    """
    Auto Cloning from InnoDB Cluster to Group Replication
    This function is used to Clone PRIMARY Node of InnoDB Cluster to all Nodes of Group Replication
    USING SINGLE API COMMAND
    """
    import time

    global clusterAdminPassword
    global recovery_user
    global recovery_password
    global autoFlipProcess
    global autoCloneProcess
    global grAllowList 

    if not checkInstanceConfiguration():
        print('\n\033[1mERROR:\033[0m Instance is not a Group Replication or User is not a cluster admin\n')
        return

    try:
        dba.get_cluster()
        v_continue = 0
    except:
        v_continue = 1

    if v_continue == 0:
        print('\n\033[1mERROR:\033[0m DB Cloning has to be executed on the Group Replication\n')
        return

    if _check_local_role() != 'PRIMARY':
        print('\n\033[1mERROR:\033[0m DB Cloning has to be executed from PRIMARY node \n')
        return

    autoFlipProcess = True
    autoCloneProcess = True

    clusterAdmin, foo, hostname, port = _session_identity("current")
    clusterAdminPassword = shell.prompt("Please provide the password for '" + clusterAdmin + "' : ", {'type':'password'})
    recovery_user = clusterAdmin
    recovery_password = clusterAdminPassword

    x = shell.get_session()

    result = _run_sql("select address from mysql_innodb_cluster_metadata.instances order by instance_id limit 1", False)
    cluster_name = _run_sql("select cluster_name from mysql_innodb_cluster_metadata.clusters limit 1", False)

    try:
        y = shell.open_session(clusterAdmin + "@" + result[0][0], clusterAdminPassword)
        shell.set_session(y)
    except:
        shell.set_session(x)
        print('\n\033[1mERROR:\033[0m Cluster Admin Password mismatch !')
        return

    grAllowList = shell.prompt('Please provide group_replication_ip_allowlist : ')

    current_primary = _run_sql("select concat(member_host,':',member_port) from performance_schema.replication_group_members where channel_name='group_replication_applier' and member_role='PRIMARY'",False)
    y=shell.open_session(clusterAdmin + '@' + current_primary[0][0], clusterAdminPassword)
    shell.set_session(y)

    result = _run_sql("set global super_read_only=off", False)
    adoptFromIC()

    shell.set_session(x)
    # stopPrimaryCluster()

    result = _run_sql("set global super_read_only=off", False)
    GRToIC(cluster_name[0][0])

    shell.set_session(y)
    setPrimaryCluster(hostname + ":" + port)

    shell.set_session(x)

    autoFlipProcess = False
