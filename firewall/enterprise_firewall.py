from mysqlsh.plugin_manager import plugin, plugin_function
import mysqlsh
import time

shell = mysqlsh.globals.shell
dba = mysqlsh.globals.dba

def _check_plugin(plugin_name):
    result = shell.get_session().run_sql("select plugin_name from information_schema.plugins")
    if result.has_data():
       for i in result.fetch_all():
           if plugin_name in str(list(i)):
                print("\n\033[1mINFO:\033[0m Plugin " + plugin_name + " is already installed \n")
                return True
    return False

def _install_plugin(plugin_name, plugin_file):
    if not _check_plugin(plugin_name):
        try:
            if _check_super_read_only() == "ON":
                shell.get_session().run_sql("set global super_read_only=off")
                shell.get_session().run_sql("install plugin " + plugin_name + " soname '" + plugin_file + "'")
                shell.get_session().run_sql("set global super_read_only=on")
            else:
                shell.get_session().run_sql("install plugin " + plugin_name + " soname '" + plugin_file + "'")
            return True
        except:
            print("\n\033[1mERROR:\033[0m Unable to install plugin " + plugin_name + " on " + shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + "\n")
            return False
    else:
        return True

def _check_super_read_only():
    return str(list(shell.get_session().run_sql("show variables like 'super_read_only'").fetch_all()[0])).strip("[']").strip("', 'super_read_only")

def _list_secondary_nodes():
    result = shell.get_session().run_sql("select concat(member_host,':',member_port) from performance_schema.replication_group_members where member_role<>'PRIMARY'")
    list_output = []
    if result.has_data():
        for row in result.fetch_all():
            list_output.append(str(list(row)).strip("[']"))
        return list_output
    else:
        return '0' 

def _get_plugin_file_location():
    return str(list(shell.get_session().run_sql("show variables like 'lc_messages_dir'").fetch_all()[0])).strip("[']").strip("', 'lc_messages_dir")

def _init_firewall_plugin(dbUser, executePrimary):
    import os

    x = shell.get_session()
    result = _list_secondary_nodes()
    if len(result) > 0 or executePrimary:
        print('Grant create on mysql.* to ' + dbUser)
        os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'grant create on mysql.* to " + dbUser + "'")
    if len(result) > 0:
        dbPassword = shell.prompt("Please provide the password for '" + dbUser + "' : ", {'type':'password'})
        for row in range(len(result)):
            try:
                y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                shell.set_session(y)
            except:
                print("\033[1mERROR:\033[0m Unable to connect to " + result[row] + "\n")
                shell.set_session(x)
                return False
            shell.get_session().run_sql('set global super_read_only=off')
            shell.get_session().run_sql('set sql_log_bin=0')
            shell.get_session().run_sql('CREATE TABLE IF NOT EXISTS mysql.firewall_whitelist( USERHOST VARCHAR(80) NOT NULL, RULE text NOT NULL, ID INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY) engine= InnoDB')
            shell.get_session().run_sql("CREATE TABLE IF NOT EXISTS mysql.firewall_users( USERHOST VARCHAR(80) PRIMARY KEY, MODE ENUM ('OFF', 'RECORDING', 'PROTECTING', 'RESET', 'DETECTING') DEFAULT 'OFF') engine= InnoDB")
            shell.get_session().run_sql('set sql_log_bin=1')
            shell.get_session().run_sql('set global super_read_only=on')
            if (_install_plugin('mysql_firewall','firewall.so') and _install_plugin('mysql_firewall_whitelist','firewall.so') and _install_plugin('mysql_firewall_users','firewall.so')):
                print("\n\033[92mINFO:\033[0m plugin installed on " + result[row])
            else:
                print("\n\033[1mERROR:\033[0m Unable to install Firewall plugin on " + result[row] + "\n")
                shell.set_session(x)
                return False
        shell.set_session(x)
    if executePrimary:
        shell.get_session().run_sql('set sql_log_bin=0')
        shell.get_session().run_sql('CREATE TABLE IF NOT EXISTS mysql.firewall_whitelist( USERHOST VARCHAR(80) NOT NULL, RULE text NOT NULL, ID INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY) engine= InnoDB')
        shell.get_session().run_sql("CREATE TABLE IF NOT EXISTS mysql.firewall_users( USERHOST VARCHAR(80) PRIMARY KEY, MODE ENUM ('OFF', 'RECORDING', 'PROTECTING', 'RESET', 'DETECTING') DEFAULT 'OFF') engine= InnoDB")
        shell.get_session().run_sql('set sql_log_bin=1')
        print('Revoke create on mysql.* from ' + dbUser)
        os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'revoke create on mysql.* from " + dbUser + "'")
        if (_install_plugin('mysql_firewall','firewall.so') and _install_plugin('mysql_firewall_whitelist','firewall.so') and _install_plugin('mysql_firewall_users','firewall.so')):
            return True
        else:
            return False
    else:
        if len(result) > 0:
            print('Revoke create on mysql.* from ' + dbUser)
            os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'revoke create on mysql.* from " + dbUser + "'")
    return True

def _install_firewall_plugin(dbUser):
    import os

    if _init_firewall_plugin(dbUser, False):
        os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'source " + _get_plugin_file_location() + "linux_install_firewall.sql; create database if not exists mysql_security_metadata; create table if not exists mysql_security_metadata.firewall_whitelist (userhost varchar(80), rule text, id int auto_increment primary key); grant all privileges on mysql_security_metadata.* to " + dbUser + ";'")
        print("\n\033[1mINFO:\033[0m Firewall plugin installation is SUCCESSFUL ! \n")
    else:
        print("\n\033[1mERROR:\033[0m: Firewall plugin installation is ABORTED !")

def _set_persist_all_nodes(dbUser, dbPassword, variable_name, variable_value):
    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
            for row in range(len(result)):
                y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                shell.set_session(y)
                try:
                    shell.get_session().run_sql("set persist " + variable_name + "='" + variable_value + "'")
                except:
                    shell.get_session().run_sql("set persist " + variable_name + "=" + variable_value)
        shell.set_session(x)
        try:
            shell.get_session().run_sql("set persist " + variable_name + "='" + variable_value +"'")
        except:
            shell.get_session().run_sql("set persist " + variable_name + "=" + variable_value)
        return True
    except:
        print("\n\033[1mERROR:\033[0m Unable to persist " + variable_name + " with variable value = " + variable_value)
        shell.set_session(x)
        return False

def _show_variables(variable_name):
    result = shell.get_session().run_sql("show variables like '" + variable_name + "'")
    list_output = []
    if result.has_data():
        for row in result.fetch_all():
            list_output.append(str(list(row)).strip("[']").strip(variable_name).strip("', '"))
        return list_output[0]
    else:
        return '0'

def _check_if_system_variables_admin_assigned():
    result = shell.get_session().run_sql("show grants")
    if result.has_data():
        for i in result.fetch_all():
            if ("SYSTEM_VARIABLES_ADMIN" in str(list(i))) or ("SUPER" in str(list(i))):
                return True
    return False

def _check_if_cluster_admin_is_required():
    result = shell.get_session().run_sql("select count(1) from performance_schema.replication_group_members")
    for i in result.fetch_all():
        return str(list(i)).strip("[]")

def _check_if_user_has_cluster_admin():
    result = shell.get_session().run_sql("show grants")
    if result.has_data():
        for i in result.fetch_all():
            if "mysql_innodb_cluster_metadata" in str(list(i)):
                return True
    return False

def _check_if_current_user_have_privilege():
    result = shell.get_session().run_sql("show grants")
    if result.has_data():
        for i in result.fetch_all():
            if (("*.*" in str(list(i))) or ("`mysql`.*" in str(list(i)))):
                if "INSERT" in str(list(i)):
                    if _check_if_system_variables_admin_assigned():
                        if _check_if_cluster_admin_is_required() != "0":
                            if _check_if_user_has_cluster_admin():
                                return True
                        else:
                            return True
    return False

def _check_if_localhost():
    if shell.parse_uri(shell.get_session().get_uri())['host'] == "localhost":
        return True
    else:
        return False

def _master_checks():
    if _check_super_read_only() == 'ON':
        print("\n\033[1mERROR:\033[0m unable to continue because super-read-only is ENABLED \n")
        return False
    if not _check_if_current_user_have_privilege():
        print("\n\033[1mERROR:\033[0m username may not have enough privilege to install a plugin or change system variables")
        print("\n\033[1mINFO:\033[0m If MySQL InnoDB Cluster or Group Replication, please ensure to use Cluster Admin to connect \n")
        return False
    return True

def _check_user_existance(dbUser):
    result = shell.get_session().run_sql("select count(1) from mysql.user where concat(user,'@',host)='" + dbUser + "'")
    if result.has_data():
       for i in result.fetch_all():
           return str(list(i)).strip("[]")

def _list_firewall_users():
    return shell.get_session().run_sql("SELECT USERHOST, MODE FROM INFORMATION_SCHEMA.MYSQL_FIREWALL_USERS")

def _list_firewall_rules(dbUser):
    return shell.get_session().run_sql("SELECT RULE FROM INFORMATION_SCHEMA.MYSQL_FIREWALL_WHITELIST WHERE USERHOST = '" + dbUser + "'")

def _sp_set_firewall_mode(dbUser,FirewallMode):
    try:
        shell.get_session().run_sql("CALL mysql.sp_set_firewall_mode('" + dbUser + "', '" + FirewallMode + "')")
        if FirewallMode == 'DETECTING':
            shell.get_session().run_sql('set persist log_error_verbosity=3')
        else:
            shell.get_session().run_sql('set persist log_error_verbosity=2')
        return True
    except:
        if FirewallMode == 'DETECTING':
            shell.get_session().run_sql('set persist log_error_verbosity=3')
        else:
            shell.get_session().run_sql('set persist log_error_verbosity=2')
        return False

def _all_sp_set_firewall_mode(adminUser, dbUser,FirewallMode):
    x = shell.get_session()
    if not _sp_set_firewall_mode(dbUser,FirewallMode):
        print("\n\033[1mERROR:\033[0m Unable to set Firewall Mode to user " + dbUser + ", ABORTING ! \n")
        return
    else:
        print("\n\033[1mINFO:\033[0m Firewall mode is set to " + FirewallMode + " on localhost")
    result = _list_secondary_nodes()
    if len(result) > 0:
        dbPassword = shell.prompt("Please provide the password for '" + adminUser + "' : ", {'type':'password'})
        for row in range(len(result)):
            try:
               y = shell.open_session(adminUser + "@" + result[row], dbPassword)
               shell.set_session(y)
               if FirewallMode == "RECORDING":
                    FirewallMode = "OFF"
               _sp_set_firewall_mode(dbUser,FirewallMode)
               print("\033[1mINFO:\033[0m Firewall mode is set to " + FirewallMode + " on " + result[row])
            except:
                print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED !")
    shell.set_session(x)

def _read_firewall_whitelist(dbUser,sqlText):
    try:
        shell.get_session().run_sql("select read_firewall_whitelist('" + dbUser + "', normalize_statement('" + sqlText + "'))")
        return True
    except:
        return False

def _sp_reload_firewall_rules(dbUser):
    try:
        shell.get_session().run_sql("call mysql.sp_reload_firewall_rules('" + dbUser + "')")
        return True
    except:
        return False

def _sp_reload_user_mode(dbUser):
    try:
        result = shell.get_session().run_sql("select mode from mysql.firewall_users where userhost='" + dbUser + "'")
        list_output = []
        if result.has_data():
            for row in result.fetch_all():
                list_output.append(str(list(row)).strip("[']"))
            z = shell.get_session().run_sql("select read_firewall_users('" + dbUser + "','" + list_output[0] + "')")
        else:
            return False
    except:
        return False

def _flush_firewall_rules(dbUser):
    try:
        _sp_reload_firewall_rules(dbUser)
        _sp_reload_user_mode(dbUser)
        x = shell.get_session()
        result = _list_secondary_nodes()
        if len(result) > 0:
            adminPassword = shell.prompt("Please provide the password for '" + shell.parse_uri(shell.get_session().get_uri())['user'] + "' : ", {'type':'password'})
            for row in range(len(result)):
                try:
                    y = shell.open_session(shell.parse_uri(shell.get_session().get_uri())['user'] + "@" + result[row], adminPassword)
                    shell.set_session(y)
                    _sp_reload_firewall_rules(dbUser) 
                    _sp_reload_user_mode(dbUser)
                except:
                    print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED !")
        shell.set_session(x)
        return True
    except:
        print("\n\033[1mERROR:\033[0m Flush Firewall Rule for user " + dbUser + " is FAILED, ABORTED ! \n")
        return False

def _exec_inject_firewall_rules(adminUser, adminPassword, dbUser, sqlText):
    _sp_set_firewall_mode(dbUser,'OFF')
    x = shell.get_session()
    result = _list_secondary_nodes()
    if len(result) > 0:
       for row in range(len(result)):
           try:
                y = shell.open_session(adminUser + "@" + result[row], adminPassword)
                shell.set_session(y)
                _sp_set_firewall_mode(dbUser,'OFF')
           except:
                print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED ! \n")
    shell.set_session(x)
    if _read_firewall_whitelist(dbUser, sqlText):
        _sp_set_firewall_mode(dbUser,'OFF')
        if len(result) > 0:
            for row in range(len(result)):
                try:
                    y = shell.open_session(adminUser + "@" + result[row], adminPassword)
                    shell.set_session(y)
                    _sp_reload_firewall_rules(dbUser)
                except:
                    print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED !")
    shell.set_session(x)

def _inject_firewall_rules(dbUser, sqlText):
    adminUser = shell.parse_uri(shell.get_session().get_uri())['user']
    adminPassword = ''
    result = _list_secondary_nodes()
    if len(result) > 0:
        adminPassword = shell.prompt("Please provide the password for '" + adminUser + "' : ", {'type':'password'})
    _exec_inject_firewall_rules(adminUser, adminPassword, dbUser, sqlText)

def _prepare_bulk_inject_firewall_rules(adminUser):
    x = shell.get_session()
    try:
        y = shell.open_session('root@localhost:' + str(shell.parse_uri(shell.get_session().get_uri())['port']))
        shell.set_session(y)
        shell.get_session().run_sql('create database if not exists mysql_security_metadata')
        shell.get_session().run_sql('create table if not exists mysql_security_metadata.firewall_whitelist (userhost varchar(80), rule text, id int auto_increment primary key)')
        shell.get_session().run_sql('grant all privileges on mysql_security_metadata.* to ' + adminUser)
        shell.set_session(x)
        print("\n\033[96mInterface table: MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST is successfully CREATED ! \033[0m\n")
        return True
    except:
        shell.set_session(x)
        return False

def _drop_bulk_inject_firewall_rules():
    try:
        shell.get_session().run_sql('drop table if exists mysql_security_metadata.firewall_whitelist')
        shell.get_session().run_sql('drop database if exists mysql_security_metadata')
        return True
    except:
        return False

def _bulk_inject_firewall_rules_read_user():
    try:
        result = shell.get_session().run_sql("select distinct userhost from mysql_security_metadata.firewall_whitelist")
        list_output = []
        if result.has_data():
            for row in result.fetch_all():
                print('Userhost = ' + str(list(row)).strip("[']"))
                list_output.append(str(list(row)).strip("[']"))
            print("\nExecuting bulk import ... \n")
            return list_output
        else:
            return '0'
    except:
        return '0'

def _bulk_inject_firewall_rules_read_sql(dbUser):
    result = shell.get_session().run_sql("select rule from mysql_security_metadata.firewall_whitelist where userhost='" + dbUser + "'")
    list_output = []
    if result.has_data():
        for row in result.fetch_all():
            list_output.append(str(list(row)).strip("[]")[1:][:-1])
        return list_output
    else:
        return '0'

def _exec_bulk_inject_firewall_rules():
    adminUser = shell.parse_uri(shell.get_session().get_uri())['user']
    adminPassword = ''
    print("\n\033[1mINFO:\033[0m List of users : ")
    list_user = _bulk_inject_firewall_rules_read_user()
    if len(list_user) > 0:
        result = _list_secondary_nodes()
        if len(result) > 0:
            adminPassword = shell.prompt("Please provide the password for '" + adminUser + "' : ", {'type':'password'})
        for row in range(len(list_user)):
            list_sqltext = _bulk_inject_firewall_rules_read_sql(list_user[row])
            if len(list_sqltext) > 0:
                for sqlno in range(len(list_sqltext)):
                    _exec_inject_firewall_rules(adminUser, adminPassword, list_user[row], list_sqltext[sqlno])
        return True
    else:
        return False

def _warning():
    print("\n\033[96mWARNING, If this is SOURCE-REPLICA environment :\033[0m")
    print("Please run \033[94mfirewall.flushUser('<username>')\033[0m immediately on REPLICA !")
    print("\n\033[96mWARNING, If this is Multi-Cluster environment (InnoDB Cluster replication to Group Replication) :\033[0m")
    print("Please run \033[94mfirewall.flushUser('<username>')\033[0m immediately on the PRIMARY NODE of Group Replication !\n")

@plugin_function("firewall.installPlugin")
def installPlugin():
    """
    MySQL Enterprise Firewall Plugin Installation

    A function to:

        Install MySQL Enterprise Firewall plugin on the stand-alone database and InnoDB Cluster / Group Replication

        If Target Databases are MySQL InnoDB Cluster or Group Replication, this function will install MySQL Enterprise Firewall plugin automatically on ALL Nodes

    """
    if _master_checks() and not _check_plugin('MYSQL_FIREWALL'):
        if _check_if_localhost():
            _install_firewall_plugin(shell.parse_uri(shell.get_session().get_uri())['user'])
        else:
            print("\n\033[1mERROR:\033[0m unable to execute from REMOTE, please use localhost to connect \n")

@plugin_function("firewall.initPluginOnReplica")
def initPluginOnReplica():
    """
    MySQL Enterprise Firewall Plugin FILE installation on REPLICA

    A function to:

        Install Firewall plugin FILE on the REPLICA of a SOURCE-REPLICA Environment

            1. On REPLICA

                mysqlsh > firewall.initPluginOnReplica()

            2. On SOURCE

                mysqlsh > firewall.installPlugin()

        Install Firewall plugin FILE on a Multi-Cluster Environment. When MySQL Group Replication is running as a Cluster REPLICA, before running firewall.installPlugin() on InnoDB Cluster as Cluster SOURCE to install MySQL Enterprise Firewall, please run first this function on the Group Replication. This function will install Firewall plugin FILE automatically on ALL Group Replication's Nodes

            1. On PRIMARY node of Group Replication as a Cluster REPLICA
                mysqlsh > firewall.initPluginOnReplica()

            2. On PRIMARY node of InnoDB Cluster as a Cluster SOURCE
                mysqlsh > firewall.installPlugin()

    """
    if _master_checks() and not _check_plugin('MYSQL_FIREWALL'):
        if _check_if_localhost():
            if _init_firewall_plugin(shell.parse_uri(shell.get_session().get_uri())['user'], True):
                print("\n\033[1mINFO:\033[0m Firewall plugin FILE installation is SUCCESSFUL ! \n")
            else:
                print("\n\033[1mERROR:\033[0m Firewall plugin FILE installation is ABORTED ! \n")
        else:
            print("\n\033[1mERROR:\033[0m unable to execute from REMOTE, please use localhost to connect \n")

@plugin_function("firewall.listUsersMode")
def listUsersMode():
    """
    List of All Registered Firewall Users

    A function to:

        show list of users and current firewall modes

    """
    if _check_plugin('MYSQL_FIREWALL'):
        print("\033[96mList of Firewall Users and their Modes : \033[0m")
        return _list_firewall_users()

@plugin_function("firewall.listRules")
def listRules(dbUser):
    """
    List Firewall Rules for a user

    A function to:

        list all SQL statement in the Whitelist for a user

    Args:
        dbUser (string): The Username

    """
    if _check_plugin('MYSQL_FIREWALL'):
        if _check_user_existance(dbUser) == "1":
            print("\033[096mList of Firewall Rules for user " + dbUser + " : \033[0m")
            return _list_firewall_rules(dbUser)
        else:
            print("\n\033[1mERROR:\033[0m User " + dbUser + " is NOT EXIST, ABORTED ! \n")

@plugin_function("firewall.setUserMode")
def setUserMode(dbUser,FirewallMode):
    """
    Set User's Firewall Mode

    A function to:

        set User's Firewall Mode

    Args:
        dbUser (string): The Username.
        FirewallMode (string): Firewall Mode [OFF, RESET, RECORDING, DETECTING, PROTECTING]

    """
    listOfStrings = ['OFF' , 'RESET', 'RECORDING', 'DETECTING', 'PROTECTING']
    if _master_checks() and _check_plugin('MYSQL_FIREWALL') and _check_user_existance(dbUser) == "1" and FirewallMode in listOfStrings:
        _all_sp_set_firewall_mode(shell.parse_uri(shell.get_session().get_uri())['user'],dbUser,FirewallMode)
        _warning()
    else:
        print("\n\033[1mERROR:\033[0m User " + dbUser + " is NOT EXIST, ABORTED ! \n")

@plugin_function("firewall.injectUserRule")
def injectUserRule(dbUser,sqlText):
    """
    Inject a Firewall Rule for a User

    A function to:

        add SQL statement to Firewall Whitelist for a user without going through RECORDING stage

    Args:
        dbUser (string): The Username
        sqlText (string): SQL statement to be added

    """
    if _master_checks() and _check_user_existance(dbUser) == "1" and _check_plugin('MYSQL_FIREWALL'):
        _inject_firewall_rules(dbUser, sqlText)
        _warning()
    else:
        print("\n\033[1mERROR:\033[0m Please check if FIREWALL plugin is installed, ABORTED ! \n")

@plugin_function("firewall.importInterface")
def importInterface():
    """
    Import Firewall Rules from Firewall Rules Interface Tables

    A function to:

        Read table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST and load the content to MYSQL.FIREWALL_WHITELIST and INFORMATION_SCHEMA.MYSQL_FIREWALL_WHITELIST

    """
    if _master_checks() and _check_plugin('MYSQL_FIREWALL'):
        if not _exec_bulk_inject_firewall_rules():
            print("\n\033[1mERROR:\033[0m Please Check Interface Table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST, ABORTED ! \n")
            print("Run security.addFirewallInterface() if the interface table is MISSING \n")
        else:
            _warning()
    else:
        print("\n\033[1mERROR:\033[0m Please check if FIREWALL plugin is installed, ABORTED !\n")

@plugin_function("firewall.flushUser")
def flushUser(dbUser):
    """
    Flush Firewall Mode and Firewall Rules for a User

    A function to:

        Reload and updates the firewall user profile cache

    Args:
        dbUser (string): The Username

    """
    if _master_checks() and _check_plugin('MYSQL_FIREWALL') and _check_user_existance(dbUser) == "1" and _flush_firewall_rules(dbUser):
        print("\n\033[1mINFO:\033[0m Flush User Rules is SUCCESSFUL ! \n")
