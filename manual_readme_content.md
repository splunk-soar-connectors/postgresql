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
