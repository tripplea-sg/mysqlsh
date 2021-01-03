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


def _install_firewall_plugin(dbUser):
    import os

    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
            print('Grant create on mysql.* to ' + dbUser)
            os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'grant create on mysql.* to " + dbUser + "'")
            dbPassword = shell.prompt("Please provide the password for '" + dbUser + "' : ", {'type':'password'})
            for row in range(len(result)):
                y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                shell.set_session(y)
                
                shell.get_session().run_sql('set global super_read_only=off')
                shell.get_session().run_sql('set sql_log_bin=0')
                shell.get_session().run_sql('CREATE TABLE IF NOT EXISTS mysql.firewall_whitelist( USERHOST VARCHAR(80) NOT NULL, RULE text NOT NULL, ID INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY) engine= InnoDB')
                shell.get_session().run_sql("CREATE TABLE IF NOT EXISTS mysql.firewall_users( USERHOST VARCHAR(80) PRIMARY KEY, MODE ENUM ('OFF', 'RECORDING', 'PROTECTING', 'RESET', 'DETECTING') DEFAULT 'OFF') engine= InnoDB")
                shell.get_session().run_sql('set sql_log_bin=1')
                shell.get_session().run_sql('set global super_read_only=on')

                if (_install_plugin('mysql_firewall','firewall.so') and _install_plugin('mysql_firewall_whitelist','firewall.so') and _install_plugin('mysql_firewall_users','firewall.so')):
                    print("\n\033[92mINFO:\033[0m plugin installed on " + result[row])
                else:
                    print("\n\033[1mERROR:\033[0m Firewall plugin installation is ABORTED !")
                    shell.set_session(x)
                    return
            shell.set_session(x)
            print('Revoke create on mysql.* from ' + dbUser)
            os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'revoke create on mysql.* from " + dbUser + "'")
        os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'source " + _get_plugin_file_location() + "linux_install_firewall.sql'")
    except:
        print("\n\033[1mERROR:\033[0m: Firewall plugin installation is ABORTED !")
        shell.set_session(x)
        return

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

def _install_password_validation_plugin(dbUser):
    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
            dbPassword = shell.prompt("Please provide the password for '" + dbUser + "' : ", {'type':'password'})
            for row in range(len(result)):
                y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                shell.set_session(y)
                if _install_plugin('validate_password','validate_password.so'):
                    print("\n\033[92mINFO:\033[0m plugin installed on " + result[row])
        shell.set_session(x)
        _install_plugin('validate_password','validate_password.so')
    except:
        print("\n\033[1mERROR:\033[0m: 'Validate Password' plugin installation is ABORTED !")
        shell.set_session(x)
        return
    print("\n\033[1mINFO:\033[0m 'Validate Password' plugin is installed successfully\n")

def _install_audit_plugin(dbUser):
    import os

    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
            dbPassword = shell.prompt("Please provide the password for '" + dbUser + "' : ", {'type':'password'})
            for row in range(len(result)):
                y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                shell.set_session(y)
                if _install_plugin('audit_log','audit_log.so'):
                    print("\n\033[92mINFO:\033[0m plugin installed on " + result[row])
                else:
                    print("\n033[1mERROR:\033[0m Audit Plugin installation is ABORTED !")
                    shell.set_session(x)
                    return
        shell.set_session(x)
        os.system("mysqlsh root@localhost:" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " --sql -e 'source " + _get_plugin_file_location() + "audit_log_filter_linux_install.sql'")
    except:
        print("\n\033[1mERROR:\033[0m Audit plugin installation is ABORTED !")
        shell.set_session(x)
        return

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
    if not _check_if_localhost():
        print("\n\033[1mERROR:\033[0m unable to execute from REMOTE, please use localhost to connect \n")
        return False
    return True

def _set_validate_password_check_user_name(dbUser, dbPassword):
    print("\n\033[96mVariable Name : validate_password_check_user_name\033[0m")
    print(shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " = " + _show_variables('validate_password_check_user_name'))
    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
             for row in range(len(result)):
                try:
                    y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                    shell.set_session(y)
                    print(shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " = " + _show_variables('validate_password_check_user_name'))
                except:
                    print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED !")
        shell.set_session(x)
        new_value = shell.prompt("Enter new value for validate_password_check_user (1=ON, 2=OFF, 0=Unchanged) : ", {'defaultValue':'0'})
        if new_value != '0':
            if new_value == '1':
                if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_check_user_name','ON'):
                    print("\n\033[1mINFO:\033[0m validate_password_check_user_name value is 'ON' \n")
            if new_value == '2':
               if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_check_user_name','OFF'):
                    print("\n\033[1mINFO:\033[0m validate_password_check_user_name value is 'OFF' \n")
        else:
            print("\n\033[1mINFO:\033[0m validate_password_check_user_name value is UNCHANGED !\n")
    except:
        print("\n\033[1mERROR:\033[0m unable to set validate_password_check_user_name !")

def _check_numeric(new_value):
    try:
        z = int(new_value)
        return True
    except:
        print("\033[1mERROR:\033[0m INVALID NUMERIC Value, SKIPPED ! \n")
        return False

def _set_validate_password_length(dbUser, dbPassword):
    print("\n\033[96mVariable Name : validate_password_length\033[0m")
    print(shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " = " + _show_variables('validate_password_length'))
    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
             for row in range(len(result)):
                try:
                    y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                    shell.set_session(y)
                    print(shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " = " + _show_variables('validate_password_length'))
                except:
                    print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED !")
        shell.set_session(x)
        new_value = shell.prompt("Enter new NUMERIC value for validate_password_length (default: 8) : ", {'defaultValue':'8'})
        if _check_numeric(new_value):
            if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_length',new_value):
                print("\n\033[1mINFO:\033[0m validate_password_check_user_name value is '" + new_value + "' \n")
    except:
        print("\n\033[1mERROR:\033[0m unable to set validate_password_check_user_name !")

def _set_validate_password_policy(dbUser, dbPassword):
    print("\n\033[96mVariable Name : validate_password_policy\033[0m")
    print(shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " = " + _show_variables('validate_password_policy'))
    x = shell.get_session()
    result = _list_secondary_nodes()
    try:
        if len(result) > 0:
             for row in range(len(result)):
                try:
                    y = shell.open_session(dbUser + "@" + result[row], dbPassword)
                    shell.set_session(y)
                    print(shell.parse_uri(shell.get_session().get_uri())['host'] + ":" + str(shell.parse_uri(shell.get_session().get_uri())['port']) + " = " + _show_variables('validate_password_policy'))
                except:
                    print("\n\033[1mINFO:\033[0m Unable to connect to " + result[row] + ", SKIPPED !")
        shell.set_session(x)
        new_value = shell.prompt("Enter new value for validate_password_policy (0=LOW, 1=MEDIUM, 2=HIGH) : ", {'defaultValue':'1'})
        if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_policy',new_value):
            shell.set_session(x)    
            print("\n\033[1mINFO:\033[0m validate_password_policy value is '" + _show_variables('validate_password_policy') + "' \n")
        _set_validate_password_length(dbUser,dbPassword)
        return new_value
    except:
        print("\n\033[1mERROR:\033[0m unable to set validate_password_check_user_name !")
        shell.set_session(x)
        return "0"

def _set_validate_password_others(dbUser, dbPassword):
    print("\n\033[96mVariable Name : \033[0m")
    print("- validate_password_mixed_case_count")
    print("- validate_password_number_count")
    print("- validate_password_special_char_count")
    print("- validate_password_dictionary_file \n")
    
    mixed_case_count_value = shell.prompt("Enter new NUMERIC value for validate_password_mixed_case_count (default: 1) : ", {'defaultValue':'1'})
    if not _check_numeric(mixed_case_count_value):
        mixed_case_count_value = '1'

    number_count_value = shell.prompt("Enter new NUMERIC value for validate_password_number_count (default: 1) : ", {'defaultValue':'1'})
    if not _check_numeric(number_count_value):
        number_count_value = '1'

    special_char_count_value = shell.prompt("Enter new NUMERIC value for validate_password_special_char_count (default: 1) : ", {'defaultValue':'1'})
    if not _check_numeric(special_char_count_value):
        mixed_case_count_value = '1'

    dictionary_file = shell.prompt("Enter new value for validate_password_dictionary_file (default: '') : ", {'defaultValue':''})

    if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_mixed_case_count', mixed_case_count_value):
        print("\n\033[1mINFO:\033[0m validate_password_mixed_case_count value is '" + mixed_case_count_value + "' \n")
    
    if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_number_count', number_count_value):
        print("\n\033[1mINFO:\033[0m validate_password_mixed_case_count value is '" + number_count_value + "' \n")

    if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_special_char_count', special_char_count_value):
        print("\n\033[1mINFO:\033[0m validate_password_special_char_count value is '" + special_char_count_value + "' \n")

    if _set_persist_all_nodes(dbUser, dbPassword, 'validate_password_dictionary_file', dictionary_file):
        print("\n\033[1mINFO:\033[0m validate_password_dictionary_file value is '" + dictionary_file + "' \n")

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
                list_output.append(str(list(row)).strip("[']"))
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

@plugin_function("security.installPasswordValidationPlugin")
def installPasswordValidationPlugin():
    if _master_checks() and not _check_plugin('validate_password'):
        _install_password_validation_plugin(shell.parse_uri(shell.get_session().get_uri())['user'])

@plugin_function("security.installAuditPlugin")
def installAuditPlugin():
    if _master_checks() and not _check_plugin('audit_log'):
        _install_audit_plugin(shell.parse_uri(shell.get_session().get_uri())['user'])

@plugin_function("security.installFirewallPlugin")
def installFirewallPlugin():
    if _master_checks() and not _check_plugin('MYSQL_FIREWALL'):
        _install_firewall_plugin(shell.parse_uri(shell.get_session().get_uri())['user'])

@plugin_function("security.setPasswordValidationPolicy")
def setPasswordValidationPolicy():
    if _master_checks():
        if _check_plugin('validate_password'):
            result = _list_secondary_nodes()
            dbUser = shell.parse_uri(shell.get_session().get_uri())['user']
            if len(result) > 0:
                dbPassword = shell.prompt("Please provide the password for '" + dbUser + "' : ", {'type':'password'})
            else:
                dbPassword = ""
            _set_validate_password_check_user_name(dbUser, dbPassword)
            if _set_validate_password_policy(dbUser, dbPassword) != "0":
                _set_validate_password_others(dbUser, dbPassword)
        else:
            print("\n\033[1mERROR:\033[0m Validate Password plugin is NOT INSTALLED\n")

@plugin_function("security.listFirewallUsers")
def listFirewallUsers():
    if _check_plugin('MYSQL_FIREWALL'):
        print("\033[96mList of Firewall Users and their Modes : \033[0m")
        return _list_firewall_users() 

@plugin_function("security.listFirewallRules")
def listFirewallRules(dbUser):
    if _check_plugin('MYSQL_FIREWALL'):
        if _check_user_existance(dbUser) == "1":
            print("\033[096mList of Firewall Rules for user " + dbUser + " : \033[0m")
            return _list_firewall_rules(dbUser)
        else:
            print("\n\033[1mERROR:\033[0m User " + dbUser + " is NOT EXIST, ABORTED ! \n")

@plugin_function("security.spSetFirewallMode")
def spSetFirewallMode(dbUser,FirewallMode):
    if _master_checks() and _check_user_existance(dbUser) == "1" and _check_plugin('MYSQL_FIREWALL'):
        listOfStrings = ['OFF' , 'RESET', 'RECORDING', 'DETECTING', 'PROTECTING']
        if _master_checks() and _check_plugin('MYSQL_FIREWALL') and FirewallMode in listOfStrings:
            _all_sp_set_firewall_mode(shell.parse_uri(shell.get_session().get_uri())['user'],dbUser,FirewallMode)
    else:
        print("\n\033[1mERROR:\033[0m User " + dbUser + " is NOT EXIST, ABORTED ! \n")

@plugin_function("security.injectFirewallRule")
def injectFirewallRule(dbUser,sqlText):
    if _master_checks() and _check_user_existance(dbUser) == "1" and _check_plugin('MYSQL_FIREWALL'):
        _inject_firewall_rules(dbUser, sqlText)
    else:
        print("\n\033[1mERROR:\033[0m Please check if FIREWALL plugin is installed, ABORTED ! \n")

@plugin_function("security.addFirewallInterface")
def addFirewallInterface():
    if _master_checks() and _check_plugin('MYSQL_FIREWALL'):
        if not _prepare_bulk_inject_firewall_rules(shell.parse_uri(shell.get_session().get_uri())['user']):
            print("\n\033[1mERROR:\033[0m Unable to create Interface Table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST, ABORTED ! \n")
        else:
            print("\n\033[91mINFO: Populate Interface Table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST for Firewall Rules Import \033[0m\n")
    else:
        print("\n\033[1mERROR:\033[0m Please check if FIREWALL plugin is installed, ABORTED !\n")

@plugin_function("security.dropFirewallInterface")
def dropFirewallInterface():
    if _master_checks() and _check_plugin('MYSQL_FIREWALL'):
        if _drop_bulk_inject_firewall_rules():
            print("\n\033[1mINFO:\033[0m DROPPED Interface Table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST, SUCCESSFUL ! \n")
        else:
            print("\n\033[1mERROR:\033[0m Unable to DROP Interface Table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST, ABORTED ! \n")
    else:
        print("\n\033[1mERROR:\033[0m Please check if FIREWALL plugin is installed, ABORTED !\n")

@plugin_function("security.importFirewallInterface")
def importFirewallInterface():
    if _master_checks() and _check_plugin('MYSQL_FIREWALL'):
        if not _exec_bulk_inject_firewall_rules():
            print("\n\033[1mERROR:\033[0m Please Check Interface Table MYSQL_SECURITY_METADATA.FIREWALL_WHITELIST, ABORTED ! \n")
            print("Run security.addFirewallInterface() if the interface table is MISSING \n")
    else:
        print("\n\033[1mERROR:\033[0m Please check if FIREWALL plugin is installed, ABORTED !\n")

