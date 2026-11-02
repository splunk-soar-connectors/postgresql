**Unreleased**

* Converted the connector to the Splunk SOAR SDK while retaining the existing PostgreSQL actions and query result widget.
* Added a PostgreSQL SQL-backed make request action with methods that skip or perform the connector's commit. The app continues to use the SOAR platform's PostgreSQL driver.
* Added per-asset POSTGRESQL_DISABLE_TLS support, allowing PostgreSQL connections without TLS when explicitly enabled in the asset Advanced settings. TLS remains enabled by default.
