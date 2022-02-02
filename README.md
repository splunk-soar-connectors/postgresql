[comment]: # "Auto-generated SOAR connector documentation"
# PostgreSQL

Publisher: Splunk  
Connector Version: 2\.0\.17  
Product Vendor: PostgreSQL  
Product Name: PostgreSQL  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app supports investigative actions against a PostgreSQL database

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2017-2022 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
This app will ignore the HTTP_PROXY and HTTPS_PROXY environment variables, as it does not use HTTP
to connect to the database.

This app will use **public** as default schema if no schema provided.

For more details on configuration parameter 'JSON Object of other libpq connection parameters',
please visit the [LibPQ Connection Parameters Page](http://initd.org/psycopg/docs/module.html) .

User can provide a JSON object comprising of the libpq connection parameters in addition to
username, password, and dbname which are already available in configuration of the asset. This JSON
object's value will be used in establishing the connection with the PostgreSQL server.

Below are the ports used by PostgresSQL-Server.

|         Service Name            | Port | Transport Protocol |
|---------------------------------|------|--------------------|
|          **PostgresSQL-Server** | 5432 | tcp                |
|          **PostgresSQL-Server** | 5432 | udp                |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a PostgreSQL asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**host** |  required  | string | Hostname or IP address
**username** |  required  | string | Username
**password** |  required  | password | Password
**database** |  required  | string | Database
**other** |  optional  | string | JSON Object of other libpq connection parameters

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[run query](#action-run-query) - Run a query against a table or tables in the database  
[list columns](#action-list-columns) - List the columns of a table  
[list tables](#action-list-tables) - List the tables in the database  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'run query'
Run a query against a table or tables in the database

Type: **investigate**  
Read only: **False**

It is recommended to use the <b>format\_vars</b> parameter when applicable\. For example, if you wanted to find a specific IP, you could set the <b>query</b> to a formatted string, like "select \* from my\_hosts where ip = %s" \(note the use of %s\), and set <b>format\_vars</b> to the IP address\. This will ensure the inputs are safely sanitized and avoid SQL injection attacks\. Regardless of the type of input it's expecting, the only format specifier which should be used is %s\.<br>Setting <b>no\_commit</b> will make it so the App does not commit any changes made to the database \(so you can ensure it's a read only query\)\.<br><br>The <b>format\_vars</b> parameter accepts a comma seperated list\. You can escape commas by surrounding them in double quotes, and escape double quotes with a backslash\. Assuming you have a list of values for the format vars, you can employ this code in your playbooks to properly format it into a string\:<br> <code>format\_vars\_str = ','\.join\(\['"\{\}"'\.format\(str\(x\)\.replace\('\\\\', '\\\\\\\\'\)\.replace\('"', '\\\\"'\)\) for x in format\_vars\_list\]\)</code>\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** |  required  | Query string | string |  `sql query` 
**format\_vars** |  optional  | Comma separated list of variables | string | 
**no\_commit** |  optional  | Do not commit changes to database | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.format\_vars | string | 
action\_result\.parameter\.no\_commit | boolean | 
action\_result\.parameter\.query | string |  `sql query` 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.summary\.total\_rows | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list columns'
List the columns of a table

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table\_name** |  required  | Name of table | string |  `postgres table name` 
**table\_schema** |  optional  | Table schema | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.table\_name | string |  `postgres table name` 
action\_result\.parameter\.table\_schema | string | 
action\_result\.data | string | 
action\_result\.data\.\*\.character\_maximum\_length | numeric | 
action\_result\.data\.\*\.character\_octet\_length | numeric | 
action\_result\.data\.\*\.character\_set\_catalog | string | 
action\_result\.data\.\*\.character\_set\_name | string | 
action\_result\.data\.\*\.character\_set\_schema | string | 
action\_result\.data\.\*\.collation\_catalog | string | 
action\_result\.data\.\*\.collation\_name | string | 
action\_result\.data\.\*\.collation\_schema | string | 
action\_result\.data\.\*\.column\_default | string | 
action\_result\.data\.\*\.column\_name | string | 
action\_result\.data\.\*\.data\_type | string | 
action\_result\.data\.\*\.datetime\_precision | string | 
action\_result\.data\.\*\.domain\_catalog | string |  `domain` 
action\_result\.data\.\*\.domain\_name | string |  `domain` 
action\_result\.data\.\*\.domain\_schema | string |  `domain` 
action\_result\.data\.\*\.dtd\_identifier | string | 
action\_result\.data\.\*\.generation\_expression | string | 
action\_result\.data\.\*\.identity\_cycle | string | 
action\_result\.data\.\*\.identity\_generation | string | 
action\_result\.data\.\*\.identity\_increment | string | 
action\_result\.data\.\*\.identity\_maximum | string | 
action\_result\.data\.\*\.identity\_minimum | string | 
action\_result\.data\.\*\.identity\_start | string | 
action\_result\.data\.\*\.interval\_precision | string | 
action\_result\.data\.\*\.interval\_type | string | 
action\_result\.data\.\*\.is\_generated | string | 
action\_result\.data\.\*\.is\_identity | string | 
action\_result\.data\.\*\.is\_nullable | string | 
action\_result\.data\.\*\.is\_self\_referencing | string | 
action\_result\.data\.\*\.is\_updatable | string | 
action\_result\.data\.\*\.maximum\_cardinality | string | 
action\_result\.data\.\*\.numeric\_precision | numeric | 
action\_result\.data\.\*\.numeric\_precision\_radix | numeric | 
action\_result\.data\.\*\.numeric\_scale | numeric | 
action\_result\.data\.\*\.ordinal\_position | numeric | 
action\_result\.data\.\*\.scope\_catalog | string | 
action\_result\.data\.\*\.scope\_name | string | 
action\_result\.data\.\*\.scope\_schema | string | 
action\_result\.data\.\*\.table\_catalog | string | 
action\_result\.data\.\*\.table\_name | string |  `postgres table name` 
action\_result\.data\.\*\.table\_schema | string | 
action\_result\.data\.\*\.udt\_catalog | string | 
action\_result\.data\.\*\.udt\_name | string | 
action\_result\.data\.\*\.udt\_schema | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list tables'
List the tables in the database

Type: **investigate**  
Read only: **True**

Describes the structure of a table in the database by displaying information about its columns\. The only tables which it will be able to query for must have a name composed of only alphanumeric characters \+ '\_' and '$'\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table\_schema** |  optional  | Table schema | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.table\_schema | string | 
action\_result\.data | string | 
action\_result\.data\.\*\.commit\_action | string | 
action\_result\.data\.\*\.is\_insertable\_into | string | 
action\_result\.data\.\*\.is\_typed | string | 
action\_result\.data\.\*\.reference\_generation | string | 
action\_result\.data\.\*\.self\_referencing\_column\_name | string | 
action\_result\.data\.\*\.table\_catalog | string | 
action\_result\.data\.\*\.table\_name | string |  `postgres table name` 
action\_result\.data\.\*\.table\_schema | string | 
action\_result\.data\.\*\.table\_type | string | 
action\_result\.data\.\*\.user\_defined\_type\_catalog | string | 
action\_result\.data\.\*\.user\_defined\_type\_name | string | 
action\_result\.data\.\*\.user\_defined\_type\_schema | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 