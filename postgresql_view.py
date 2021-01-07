# File: postgresql_view.py
# Copyright (c) 2017-2021 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

def display_query_results(provides, all_results, context):

    headers = []
    adjusted_names = {}

    headers_set = set()
    for summary, action_results in all_results:
        for result in action_results:
            header_data = result.get_data()

    if header_data:
        headers += list(header_data[0].keys())

    if not headers_set:
        headers_set.update(headers)
    headers = sorted(headers_set)

    context['results'] = results = []
    context['headers'] = headers

    for summary, action_results in all_results:
        for result in action_results:
            table = {}
            table['data'] = table_data = []
            data = result.get_data()
            for item in data:
                row = []
                for h in headers:
                    row.append({ 'value': item.get(adjusted_names.get(h, h)) })
                table_data.append(row)
            results.append(table)

    return 'postgresql_run_query.html'
