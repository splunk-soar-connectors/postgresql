This app will ignore the HTTP_PROXY and HTTPS_PROXY environment variables, as it does not use HTTP
to connect to the database.

The PostgreSQL driver is provided by the Splunk SOAR platform. This app does not package a psycopg2 wheel.

This app will use **public** as default schema if no schema provided.

The **make request** action uses the configured PostgreSQL connection to execute SQL, without an HTTP endpoint. Set `endpoint` to SQL and supply bound values through either `query_parameters` or `body` as a JSON list, JSON object, or CSV string. GET, HEAD, and OPTIONS skip the connector's commit, like run query with `no_commit` enabled; they do not enforce a read-only transaction, and explicit SQL transaction commands are passed through unchanged. POST, PUT, PATCH, and DELETE commit on success. The asset's TLS settings control certificate verification.

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
