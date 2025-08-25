# PostgreSQL

Publisher: Splunk <br>
Connector Version: 2.0.19 <br>
Product Vendor: PostgreSQL <br>
Product Name: PostgreSQL <br>
Minimum Product Version: 6.2.1

This app supports investigative actions against a PostgreSQL database

This app will ignore the HTTP_PROXY and HTTPS_PROXY environment variables, as it does not use HTTP
to connect to the database.

This app will use **public** as default schema if no schema provided.

For more details on configuration parameter 'JSON Object of other libpq connection parameters',
please visit the [LibPQ Connection Parameters Page](http://initd.org/psycopg/docs/module.html) .

User can provide a JSON object comprising of the libpq connection parameters in addition to
username, password, and dbname which are already available in configuration of the asset. This JSON
object's value will be used in establishing the connection with the PostgreSQL server.

Below are the ports used by PostgresSQL-Server.

|         Service Name | Port | Transport Protocol |
|---------------------------------|------|--------------------|
|          **PostgresSQL-Server** | 5432 | tcp |
|          **PostgresSQL-Server** | 5432 | udp |

### Configuration variables

This table lists the configuration variables required to operate PostgreSQL. These variables are specified when configuring a PostgreSQL asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**host** | required | string | Hostname or IP address |
**username** | required | string | Username |
**password** | required | password | Password |
**database** | required | string | Database |
**other** | optional | string | JSON Object of other libpq connection parameters |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[run query](#action-run-query) - Run a query against a table or tables in the database <br>
[list columns](#action-list-columns) - List the columns of a table <br>
[list tables](#action-list-tables) - List the tables in the database

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run query'

Run a query against a table or tables in the database

Type: **investigate** <br>
Read only: **False**

It is recommended to use the <b>format_vars</b> parameter when applicable. For example, if you wanted to find a specific IP, you could set the <b>query</b> to a formatted string, like "select * from my_hosts where ip = %s" (note the use of %s), and set <b>format_vars</b> to the IP address. This will ensure the inputs are safely sanitized and avoid SQL injection attacks. Regardless of the type of input it's expecting, the only format specifier which should be used is %s.<br>Setting <b>no_commit</b> will make it so the App does not commit any changes made to the database (so you can ensure it's a read only query).<br><br>The <b>format_vars</b> parameter accepts a comma seperated list. You can escape commas by surrounding them in double quotes, and escape double quotes with a backslash. Assuming you have a list of values for the format vars, you can employ this code in your playbooks to properly format it into a string:<br> <code>format_vars_str = ','.join(['"{}"'.format(str(x).replace('\\\\', '\\\\\\\\').replace('"', '\\\\"')) for x in format_vars_list])</code>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query string | string | `sql query` |
**format_vars** | optional | Comma separated list of variables | string | |
**no_commit** | optional | Do not commit changes to database | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.format_vars | string | | 10 |
action_result.parameter.no_commit | boolean | | False |
action_result.parameter.query | string | `sql query` | select * from test_table |
action_result.data | string | | |
action_result.summary | string | | |
action_result.summary.total_rows | numeric | | |
action_result.message | string | | Successfully ran query |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list columns'

List the columns of a table

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of table | string | `postgres table name` |
**table_schema** | optional | Table schema | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.table_name | string | `postgres table name` | users |
action_result.parameter.table_schema | string | | myschema |
action_result.data | string | | |
action_result.data.\*.character_maximum_length | numeric | | 32 |
action_result.data.\*.character_octet_length | numeric | | |
action_result.data.\*.character_set_catalog | string | | |
action_result.data.\*.character_set_name | string | | |
action_result.data.\*.character_set_schema | string | | |
action_result.data.\*.collation_catalog | string | | |
action_result.data.\*.collation_name | string | | |
action_result.data.\*.collation_schema | string | | |
action_result.data.\*.column_default | string | | |
action_result.data.\*.column_name | string | | user_name |
action_result.data.\*.data_type | string | | character |
action_result.data.\*.datetime_precision | string | | |
action_result.data.\*.domain_catalog | string | `domain` | |
action_result.data.\*.domain_name | string | `domain` | |
action_result.data.\*.domain_schema | string | `domain` | |
action_result.data.\*.dtd_identifier | string | | 1 |
action_result.data.\*.generation_expression | string | | |
action_result.data.\*.identity_cycle | string | | |
action_result.data.\*.identity_generation | string | | |
action_result.data.\*.identity_increment | string | | |
action_result.data.\*.identity_maximum | string | | |
action_result.data.\*.identity_minimum | string | | |
action_result.data.\*.identity_start | string | | |
action_result.data.\*.interval_precision | string | | |
action_result.data.\*.interval_type | string | | |
action_result.data.\*.is_generated | string | | NEVER |
action_result.data.\*.is_identity | string | | NO |
action_result.data.\*.is_nullable | string | | YES |
action_result.data.\*.is_self_referencing | string | | NO |
action_result.data.\*.is_updatable | string | | YES |
action_result.data.\*.maximum_cardinality | string | | |
action_result.data.\*.numeric_precision | numeric | | |
action_result.data.\*.numeric_precision_radix | numeric | | |
action_result.data.\*.numeric_scale | numeric | | |
action_result.data.\*.ordinal_position | numeric | | 1 |
action_result.data.\*.scope_catalog | string | | |
action_result.data.\*.scope_name | string | | |
action_result.data.\*.scope_schema | string | | |
action_result.data.\*.table_catalog | string | | postgres |
action_result.data.\*.table_name | string | `postgres table name` | users |
action_result.data.\*.table_schema | string | | public |
action_result.data.\*.udt_catalog | string | | postgres |
action_result.data.\*.udt_name | string | | bpchar |
action_result.data.\*.udt_schema | string | | pg_catalog |
action_result.summary | string | | |
action_result.message | string | | Successfully listed all columns |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tables'

List the tables in the database

Type: **investigate** <br>
Read only: **True**

Describes the structure of a table in the database by displaying information about its columns. The only tables which it will be able to query for must have a name composed of only alphanumeric characters + '\_' and '$'.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_schema** | optional | Table schema | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.table_schema | string | | myschema |
action_result.data | string | | |
action_result.data.\*.commit_action | string | | |
action_result.data.\*.is_insertable_into | string | | YES |
action_result.data.\*.is_typed | string | | NO |
action_result.data.\*.reference_generation | string | | |
action_result.data.\*.self_referencing_column_name | string | | |
action_result.data.\*.table_catalog | string | | postgres |
action_result.data.\*.table_name | string | `postgres table name` | users |
action_result.data.\*.table_schema | string | | public |
action_result.data.\*.table_type | string | | BASE TABLE |
action_result.data.\*.user_defined_type_catalog | string | | |
action_result.data.\*.user_defined_type_name | string | | |
action_result.data.\*.user_defined_type_schema | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully listed all tables |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
