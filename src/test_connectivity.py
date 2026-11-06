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
from soar_sdk.abstract import SOARClient
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from .asset import Asset
from .auth import get_session


logger = getLogger()


def run_test_connectivity(soar: SOARClient, asset: Asset) -> None:
    try:
        with get_session(asset) as session:
            try:
                session._cursor.execute("SELECT version();")
            except Exception as e:
                raise ActionFailure(f"Test Connectivity Failed. Error string: '{e}'") from e

            for row in session._cursor:
                logger.progress("Using: %s", row)

            logger.progress("Test Connectivity Passed")
            soar.set_message("Test Connectivity Passed")
    except ActionFailure as e:
        if not e.message.startswith("Test Connectivity Failed"):
            logger.progress(e.message)
            raise ActionFailure("Test Connectivity Failed") from e
        raise
