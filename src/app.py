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

from soar_sdk.abstract import SOARClient
from soar_sdk.app import App

from .actions import register_actions
from .asset import Asset
from .auth import action_scope
from .test_connectivity import run_test_connectivity


class PostgresqlApp(App):
    """Keep one PostgreSQL connection for a complete SDK action run."""

    def handle(self, raw_input_data: str, handle: int | None = None) -> str:
        data = json.loads(raw_input_data)
        if data.get("identifier") == "run_query":
            for param in data.get("parameters", []):
                if isinstance(param.get("format_vars"), (int, float)):
                    param["format_vars"] = str(param["format_vars"])
                if param.get("no_commit") in (None, ""):
                    param["no_commit"] = False
            raw_input_data = json.dumps(data)

        with action_scope():
            return super().handle(raw_input_data, handle=handle)


app: App = PostgresqlApp(
    name="PostgreSQL",
    app_type="information",
    logo="logo_postgresql.svg",
    logo_dark="logo_postgresql_dark.svg",
    product_vendor="PostgreSQL",
    product_name="PostgreSQL",
    publisher="Splunk",
    appid="958012c1-4ad4-4e94-9ad2-6a0ffe053532",
    min_phantom_version="7.0.0",
    fips_compliant=True,
    asset_cls=Asset,
)


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """Validate the asset configuration for connectivity using supplied configuration"""
    run_test_connectivity(soar, asset)


register_actions(app)


if __name__ == "__main__":
    app.cli()
