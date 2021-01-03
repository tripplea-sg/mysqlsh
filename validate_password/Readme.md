# MySQL PASSWORD VALIDATION management and utilities.
    
## A collection of functions to:

Install PASSWORD VALIDATION plugin on single database, 
AND All MySQL InnoDB Cluster / Group Replication databases 
Automatically USING SINGLE API COMMAND

Set PASSWORD VALIDATION  Policy on single database,
AND All MySQL InnoDB Cluster / Group Replication databases 
Automatically USING SINGLE API COMMAND

## Plugin Installation

CREATE new FOLDER $HOME/.mysqlsh/plugins/validate_password/
</br></br>
DOWNLOAD init.py and password_validation.py from https://github.com/tripplea-sg/mysqlsh/edit/main/validate_password  </br>
COPY both files into $HOME/.mysqlsh/plugins/validate_password/

## Tutorial

To install the PASSWORD VALIDATION plugin on single database and MySQL InnoDB Cluster / Group Replication

                mysqlsh > validate_password.installPlugin()
          
To set PASSWORD VALIDATION policies on single database and MySQL InnoDB Cluster / Group Replication

                mysqlsh > validate_password.setPolicy()

On a multi-cluster environment (InnoDB Cluster replication to Group Replication), the PASSWORD VALIDATION plugin has to be installed on both, separately.

            1. On PRIMARY node of InnoDB Cluster as Cluster SOURCE

                mysqlsh > validate_password.installPlugin()

            2. On PRIMARY node of Group Replication as Cluster REPLICA

                mysqlsh > validate_password.installPlugin()

On a multi-cluster environment (InnoDB Cluster replication to Group Replication, set PASSWORD VALIDATIONpolicy has to be executed on both, separately.

            1. On PRIMARY node of InnoDB Cluster as Cluster SOURCE

                mysqlsh > validate_password.setPolicy()

            2. On PRIMARY node of Group Replication as Cluster REPLICA

                mysqlsh > validate_password.setPolicy()
