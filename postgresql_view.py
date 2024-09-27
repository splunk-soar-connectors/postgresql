# File: postgresql_view.py
#
# Copyright (c) 2017-2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
def display_query_results(provides, all_results, context):

    context["results"] = results = []

    adjusted_names = {}

    for summary, action_results in all_results:
        for result in action_results:
            headers_set = set()
            table = dict()
            table["data"] = rows = []
            data = result.get_data()
            if data:
                headers_set.update(data[0].keys())
            headers = sorted(headers_set)
            table["headers"] = headers

            for item in data:
                row = []

                for h in headers:
                    row.append({"value": item.get(adjusted_names.get(h, h))})
                rows.append(row)
            results.append(table)

    return "postgresql_run_query.html"
