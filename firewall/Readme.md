# MySQL Enterprise Firewall management and utilities.
    
## A collection of functions to:

1. Install MySQL Enterprise Firewall plugin on single database, SOURCE-REPLICA, and MySQL InnoDB Cluster / Group Replication databases Automatically USING SINGLE API COMMAND
2. Inject a Firewall Rule for particular database users without going through 'RECORDING' phase. Once the firewall rule is injected, the FIREWALL_MODE for those users are automatically set to 'OFF'. If target databases are MySQL InnoDB Cluster or Group Replication, injecting a firewall rule is done only on PRIMARY node, and this new firewall fule will be applied to ALL NODES Automatically.
3. Bulk Upload and Import multiple Firewall Rules for database users without going through 'RECORDING' phase. Once all firewall rules are imported, the FIREWALL_MODE for those users are automatically set to 'OFF'. If target databases are MySQL InnoDB Cluster or Group Replication, importing Firewall RUles are done one-time on PRIMARY node, and those new firewall rules will be applied to ALL NODES Automatically.
4. Set or change FIREWALL MODE to 'OFF', 'RESET', 'RECORDING', 'DETECTING', 'PROTECTING' across MySQL InnoDB Cluster / Group Replication automatically WITH USING SINGLE API COMMAND. 

This method is distributed as Open Source in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

## Plugin Installation

CREATE new FOLDER $HOME/.mysqlsh/plugins/firewall/

DOWNLOAD init.py and enterprise_firewall.py from https://github.com/tripplea-sg/mysqlsh/edit/main/firewall </br>
COPY both files into $HOME/.mysqlsh/plugins/firewall/
