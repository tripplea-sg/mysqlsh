# MySQL Enterprise Audit management and utilities.
    
## A collection of functions to:

Install MySQL Enterprise Audit plugin on single database, AND All MySQL InnoDB Cluster / Group Replication databases Automatically USING SINGLE API COMMAND </br>

## DISCLAIMER
This method is distributed as Open Source in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

## Plugin Installation

CREATE new FOLDER $HOME/.mysqlsh/plugins/audit/

DOWNLOAD init.py and enterprise_audit.py from https://github.com/tripplea-sg/mysqlsh/edit/main/audit </br>
COPY both files into $HOME/.mysqlsh/plugins/audit/

## Tutorial

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
