#    Plugin for MySQL Enterprise Firewall Management and Utility
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


from mysqlsh.plugin_manager import plugin, plugin_function

@plugin
class firewall:
    """
    MySQL Enterprise Firewall management and utilities.
    
    A collection of functions to:

        Install MySQL Enterprise Firewall plugin on single database, SOURCE-REPLICA, and MySQL InnoDB Cluster / Group Replication databases Automatically USING SINGLE API COMMAND

        Inject a Firewall Rule for particular database users without going through 'RECORDING' phase. Once the firewall rule is injected, the FIREWALL_MODE for those users are automatically set to 'OFF'. If target databases are MySQL InnoDB Cluster or Group Replication, injecting a firewall rule is done only on PRIMARY node, and this new firewall fule will be applied to ALL NODES Automatically.

        Bulk Upload and Import multiple Firewall Rules for database users without going through 'RECORDING' phase. Once all firewall rules are imported, the FIREWALL_MODE for those users are automatically set to 'OFF'. If target databases are MySQL InnoDB Cluster or Group Replication, importing Firewall RUles are done one-time on PRIMARY node, and those new firewall rules will be applied to ALL NODES Automatically.

        Set or change FIREWALL MODE to 'OFF', 'RESET', 'RECORDING', 'DETECTING', 'PROTECTING' across MySQL InnoDB Cluster / Group Replication automatically WITH USING SINGLE API COMMAND.

        To install MySQL Enterprise Firewall on Single database, simply run
        
            mysqlsh > firewall.installPlugin()

        To install MySQL Enterprise Firewall on MySQL InnoDB Cluster / Group Replication, simply run on PRIMARY node. The Plugin will be installed on All Nodes automatically.

            mysqlsh > firewall.installPlugin()
        
        To install MySQL Enterprise Firewall on a SOURCE-REPLICA environment, some steps are required to be executed in sequence

            1. On REPLICA

                mysqlsh > firewall.initPluginOnReplica()

            2. On SOURCE

                mysqlsh > firewall.installPlugin()

        On a SOURCE-REPLICA environment, once MySQL Enterprise Firewall plugin is INSTALLED, Installing Firewall Rules has to be executed on SOURCE, and the CHANGE of Firewall Rules will be propagated by the PLUGIN to the REPLICA. 

        To install MySQL Enterprise Firewall on a multi-cluster environment (MySQL InnoDB Cluster replication to MySQL Group Replication), some steps are required to be executed in sequence

            1. On PRIMARY Node of MySQL Group Replication as Cluster REPLICA
                
                mysqlsh > firewall.initPluginOnReplica()

            2. On PRIMARY Node of MySQL InnoDB Cluster as Cluster SOURCE
                
                mysqlsh > firewall.installPlugin()

        On a multi-cluster environment (MySQL InnoDB Cluster replication to MySQL Group Replication), once MySQL Enteprise Firewall plugin is INSTALLED, Installing Firewall Rules has to be executed on the PRIMARY node of MySQL InnoDB Cluster, and the CHANGE of Firewall Rules will be propagated by the PLUGIN to ALL NODES.
        
        Available REPORTs below can be executed on ALL NODES and will report FIREWALL SETUP only on that nodes

            1. To LIST All FIREWALL USERS and their FIREWALL MODEs

                mysqlsh > firewall.listUsersMode()

            2. To LIST All FIREWALL RULES for a USER

                mysqlsh > firewall.listRules('fwuser@%')

        To SET FIREWALL MODEs or INJECT FIREWALL RULES, login to MySQL (if target databases are InnoDB Cluster or Group Replication, then Connect only to the PRIMARY node, and the CHANGE will be propagated AUTOMATICALLY to ALL NODES) 

            Set FIREWALL_MODE to 'OFF'

                mysqlsh > firewall.setUserMode('fwuser@%','OFF')

            Set FIREWALL_MODE to 'RECORDING'
                
                mysqlsh > firewall.setUserMode('fwuser@%','RECORDING')

            Set FIREWALL_MODE to 'DETECTING'

                mysqlsh > firewall.setUserMode('fwuser@%','DETECTING')

            Set FIREWALL_MODE to 'PROTECTING'

                mysqlsh > firewall.setUserMode('fwuser@%','PROTECTING')

            Reset FIREWALL_MODE

                mysqlsh > firewall.setUserMode('fwuser@%','RESET')

        To INJECT a FIREWALL_RULE, run the following from PRIMARY node

            mysqlsh > firewall.injectUserRule('fwuser@%',"select * from sakila.customer")

        To BUILK LOAD and IMPORT FIREWALL Rules, run the following from PRIMARY node

            1. LOAD your FIREWALL RULES and USERS into the Firewall Interface Table

            2. IMPORT FIREWALL RULES from Firewall Interface Table

                mysqlsh > firewall.importInterface()

        On SOURCE-REPLICA environment or Multi-Cluster environment (InnoDB Cluster / SOURCE replication to Group Replication / Cluster REPLICA), the changes on FIREWALL_MODE and FIREWALL_RULES do not applied immediately on REPLICA or Cluster REPLICA. To activate FIREWALL_MODE and FIREWALL_RULES on REPLICA or Cluster REPLICA, connect to REPLICA or PRIMARY NODE of the Cluster REPLICA, and issue flushUser

            mysqlsh > firewall.flushUser('fwuser@%')

    """

from firewall import enterprise_firewall
