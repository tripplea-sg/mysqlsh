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

def _init_audit_plugin(dbUser, executePrimary):
    x = shell.get_session()
    result = _list_secondary_nodes()
    if len(result) > 0:
        dbPassword = shell.prompt("Please provide the password for '" + dbUser + "' : ", {'type':'password'})
        for row in range(len(result)):
            try:    
                y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                shell.set_session(y)
                if _install_plugin('audit_log','audit_log.so'):
                    print("\n\033[92mINFO:\033[0m plugin installed on " + result[row])
                else:
                    print("\n033[1mERROR:\033[0m Unable to install Audit plugin on " + result[row] + "\n")
                    shell.set_session(x)
                    return False
            except:
                print("\033[1mERROR:\033[0m Unable to connect to " + result[row] + "\n")
                shell.set_session(x)
                return False
        shell.set_session(x)
    if executePrimary:
        _install_plugin('audit_log', 'audit_log.so')
    return True

def _install_audit_plugin(dbUser):
    import os

    if _init_audit_plugin(dbUser, False):
        os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql --verbose=0 -e 'source " + _get_plugin_file_location() + "audit_log_filter_linux_install.sql'")
        print("\n\033[1mINFO:\033[0m Audit plugin installation is SUCCESSFUL ! \n")
    else:
        print("\n\033[1mERROR:\033[0m Audit plugin installation is ABORTED ! \n")

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
    if not _check_if_localhost():
        print("\n\033[1mERROR:\033[0m unable to execute from REMOTE, please use localhost to connect \n")
        return False
    return True

@plugin_function("audit.installPlugin")
def installPlugin():
    """
    MySQL Enterprise Audit Plugin Installation

    A function to:

        Install MySQL Enterprise Audit plugin on the stand-alone database and InnoDB Cluster / Group Replication

        If Target Databases are MySQL InnoDB Cluster or Group Replication, this function will install MySQL Enterprise Audit plugin automatically on ALL Nodes

    """
    if _master_checks():
        _install_audit_plugin(shell.parse_uri(shell.get_session().get_uri())['user'])

@plugin_function("audit.initPluginOnClusterReplica")
def initPluginOnReplica():
    """
    Audit Plugin FILE Installation on A Multi-Cluster Environment

    A function to:

        Install Audit plugin FILE on the REPLICA of a SOURCE-REPLICA Environment
        
            1. On REPLICA
            
                mysqlsh > audit.initPluginOnReplica()
            
            2. On SOURCE
            
                mysqlsh > audit.installPlugin()
        
        Install Audit plugin FILE on a Multi-Cluster Environment. When MySQL Group Replication is running as a Cluster REPLICA, before running audit.installPlugin() on InnoDB Cluster as Cluster SOURCE to install MySQL Enterprise Audit, please run first this function on the Group Replication. This function will install Audit plugin FILE automatically on ALL Group Replication's Nodes

            1. On PRIMARY node of Group Replication as a Cluster REPLICA

                mysqlsh > audit.initPluginOnReplica()

            3. On PRIMARY node of InnoDB Cluster as a Cluster SOURCE

                mysqlsh > audit.installPlugin()
    """
    if _master_checks() and not _check_plugin('audit_log'):
        if _init_audit_plugin(shell.parse_uri(shell.get_session().get_uri())['user'], True):
            print("\n\033[1mINFO:\033[0m Audit plugin FILE installation is SUCCESSFUL ! \n")
        else:
            print("\n\033[1mERROR:\033[0m Audit plugin FILE installation is ABORTED ! \n")

