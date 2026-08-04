**Unreleased**

* Restrict the PostgreSQL other field to supported non-file libpq parameters and replace the ssl_root_cert host path with an uploaded PEM file, requiring affected assets to upload their trusted CA again.
* Return generic PostgreSQL connection failures to action callers instead of exposing underlying driver exception details.
