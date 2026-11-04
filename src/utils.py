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
import csv
from datetime import date, datetime


def get_format_vars(format_vars):
    if format_vars:
        format_vars = next(csv.reader([format_vars], quotechar='"', skipinitialspace=True, escapechar="\\"))
    return format_vars


def deduplicate_column_names(columns):
    names = []
    used = set()
    for index, column in enumerate(columns):
        base_name = column[0] or f"column_{index}"
        name = base_name
        suffix = index
        while name in used:
            name = f"{base_name}__duplicate_{suffix}"
            suffix += 1
        names.append(name)
        used.add(name)
    return names


def get_rows(cursor):
    columns = cursor.description
    result = []
    if columns is not None:
        column_names = deduplicate_column_names(columns)
        for value in cursor.fetchall():
            info = {}
            for index, column in enumerate(value):
                if isinstance(column, (datetime, date)):
                    column = column.isoformat()
                info[column_names[index]] = column
            result.append(info)
    return columns, result
