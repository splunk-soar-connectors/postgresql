# Copyright (c) 2026 Splunk Inc.
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
from contextlib import ExitStack

from soar_sdk.exceptions import ActionFailure

from .assets import Asset


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


def create_connection(asset: Asset):
    """Connect using the asset's credentials and legacy TLS settings."""
    other = {}
    if asset.other:
        try:
            other = json.loads(asset.other)
        except json.JSONDecodeError as e:
            raise ActionFailure("'other' is invalid") from e
        if not isinstance(other, dict):
            raise ActionFailure("'other' must be a JSON object")

    unsupported_options = sorted(set(other) - ALLOWED_OTHER_OPTIONS)
    if unsupported_options:
        raise ActionFailure("'other' contains unsupported connection parameter(s): " + ", ".join(unsupported_options))
    other["sslmode"] = "verify-full" if asset.verify_server_cert else "require"

    # SOAR supplies the driver at runtime; the SDK builder imports without it.
    import psycopg2

    try:
        with ExitStack() as stack:
            if asset.ssl_root_cert:
                certificate = stack.enter_context(tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".pem"))
                certificate.write(asset.ssl_root_cert)
                certificate.flush()
                other["sslrootcert"] = certificate.name
            return psycopg2.connect(user=asset.username, password=asset.password, dbname=asset.database, host=asset.host, **other)
    except (psycopg2.Error, OSError, TypeError, ValueError) as e:
        raise ActionFailure("Database connection failed") from e
