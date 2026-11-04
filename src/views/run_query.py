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
from soar_sdk.views.template_renderer import get_template_renderer, get_templates_dir


def display_query_results(provides, all_results, context):
    context["results"] = results = []
    for _, action_results in all_results:
        for result in action_results:
            data = result.get_data()
            headers = sorted(data[0].keys()) if data else []
            rows = [[{"value": item.get(header)} for header in headers] for item in data]
            results.append({"headers": headers, "data": rows})

    context["prerender"] = True
    renderer = get_template_renderer("jinja", get_templates_dir(globals()))
    return renderer.render_template("postgresql_run_query.html", context)
