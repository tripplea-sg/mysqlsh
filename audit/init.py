#    Plugin for MySQL Enterprise Audit Management and Utility
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
class audit:
    """
    MySQL Enterprise Audit management and utilities.
    
    A collection of functions to:

        Install MySQL Enterprise Audit plugin on single database, AND All MySQL InnoDB Cluster / Group Replication databases Automatically USING SINGLE API COMMAND

        To install MySQL Enterprise Audit on Single database, simply run
        
            mysqlsh > audit.installPlugin()

        To install MySQL Enterprise Audit on MySQL InnoDB Cluster / Group Replication, simply run on PRIMARY node. The Plugin will be installed on All Nodes automatically.

            mysqlsh > audit.installPlugin()
        
        To install MySQL Enterprise Audit on a SOURCE-REPLICA environment, some steps are required to be executed in sequence

            1. On REPLICA

                mysqlsh > audit.initPluginOnReplica()

            2. On SOURCE

                mysqlsh > audit.installPlugin()

        To install MySQL Enterprise Audit on a multi-cluster environment (MySQL InnoDB Cluster replication to MySQL Group Replication), some steps are required to be executed in sequence

            1. On PRIMARY Node of MySQL Group Replication as Cluster REPLICA
                
                mysqlsh > audit.initPluginOnReplica()

            2. On PRIMARY Node of MySQL InnoDB Cluster as Cluster SOURCE
                
                mysqlsh > audit.installPlugin()

        On a multi-cluster environment (MySQL InnoDB Cluster replication to MySQL Group Replication), once MySQL Enteprise Audit plugin is INSTALLED, Audit Policy has to be setup from the PRIMARY node of MySQL InnoDB Cluster.
    """

from audit import enterprise_audit
