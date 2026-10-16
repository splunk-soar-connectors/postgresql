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
from soar_sdk.asset import AssetField, BaseAsset, FieldCategory


class Asset(BaseAsset):
    host: str = AssetField(description="Hostname or IP address", required=True, category=FieldCategory.CONNECTIVITY)
    username: str = AssetField(description="Username", required=True, category=FieldCategory.CONNECTIVITY)
    password: str = AssetField(description="Password", required=True, sensitive=True, category=FieldCategory.CONNECTIVITY)
    database: str = AssetField(description="Database", required=True, category=FieldCategory.CONNECTIVITY)
    other: str | None = AssetField(
        description="JSON object of supported non-file libpq connection parameters. The verify_server_cert setting overrides sslmode",
        required=False,
        category=FieldCategory.CONNECTIVITY,
    )
    verify_server_cert: bool = AssetField(
        description="Verify the PostgreSQL server certificate and hostname",
        required=False,
        default=True,
        category=FieldCategory.CONNECTIVITY,
    )
    ssl_root_cert: str | None = AssetField(
        description="PEM file containing trusted certificate authority certificates. When omitted, libpq uses its default root certificate file",
        required=False,
        is_file=True,
        category=FieldCategory.CONNECTIVITY,
    )
