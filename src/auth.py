# Copyright (c) 2017-2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar

from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from .asset import Asset


try:
    import psycopg2
except ImportError:  # SOAR provides psycopg2 at runtime, but the SDK build environment does not.
    psycopg2 = None


logger = getLogger()
ALLOWED_OTHER_OPTIONS = frozenset(
    {
        "application_name",
        "client_encoding",
        "connect_timeout",
        "keepalives",
        "keepalives_count",
        "keepalives_idle",
        "keepalives_interval",
        "options",
        "port",
        "sslmode",
        "target_session_attrs",
    }
)
DISABLE_TLS_ENV_VAR = "POSTGRESQL_DISABLE_TLS"
_action_scope = ContextVar("postgresql_action_scope", default=None)


def create_connection(asset: Asset):
    """Use the legacy libpq options and the configured PostgreSQL asset."""
    if asset.other:
        try:
            other = json.loads(asset.other)
        except Exception as e:
            raise ActionFailure("'other' is invalid") from e
        if not isinstance(other, dict):
            raise ActionFailure("'other' must be a JSON object")
    else:
        other = {}

    unsupported_options = sorted(set(other) - ALLOWED_OTHER_OPTIONS)
    if unsupported_options:
        raise ActionFailure("'other' contains unsupported connection parameter(s): " + ", ".join(unsupported_options))

    asset_env = (asset.model_extra or {}).get("_reserved_environment_variables") or {}
    disable_tls = (asset_env.get(DISABLE_TLS_ENV_VAR) or {}).get("value")
    use_tls = str(disable_tls).strip().lower() not in ("true", "1", "yes")
    other["sslmode"] = ("verify-full" if asset.verify_server_cert else "require") if use_tls else "disable"

    certificate = None
    try:
        if use_tls and asset.ssl_root_cert:
            certificate = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".pem")
            certificate.write(asset.ssl_root_cert)
            certificate.flush()
            other["sslrootcert"] = certificate.name
        if psycopg2 is None:
            raise ImportError("SOAR's PostgreSQL driver is unavailable")
        return psycopg2.connect(user=asset.username, password=asset.password, dbname=asset.database, host=asset.host, **other)
    except Exception as e:
        raise ActionFailure("Database connection failed") from e
    finally:
        if certificate is not None:
            certificate.close()


class PostgresqlSession:
    """One connection and cursor for a PostgreSQL action run."""

    def __init__(self, asset: Asset):
        self.asset = asset
        self._connection = None
        self._cursor = None

    def connect(self):
        self._connection = create_connection(self.asset)
        try:
            self._cursor = self._connection.cursor()
        except Exception as e:
            self.close()
            raise ActionFailure("Database connection failed") from e
        logger.progress("Database connection established")
        return self

    def close(self):
        for resource in (self._cursor, self._connection):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    pass
        self._cursor = self._connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()


@contextmanager
def action_scope():
    """Keep the connection until every parameter in the action has run."""
    scope = {}
    token = _action_scope.set(scope)
    try:
        yield
    finally:
        if session := scope.get("session"):
            session.close()
        _action_scope.reset(token)


@contextmanager
def get_session(asset: Asset):
    scope = _action_scope.get()
    if scope is None:
        with PostgresqlSession(asset) as session:
            yield session
    else:
        if "session" not in scope:
            scope["session"] = PostgresqlSession(asset).connect()
        yield scope["session"]
