# File: postgresql_view.py
# Copyright (c) 2017-2021 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

def display_query_results(provides, all_results, context):

    context['results'] = results = []

    adjusted_names = {}

    for summary, action_results in all_results:
        for result in action_results:
            headers_set = set()
            table = dict()
            table['data'] = rows = []
            data = result.get_data()
            if data:
                headers_set.update(data[0].keys())
            headers = sorted(headers_set)
            table['headers'] = headers

            for item in data:
                row = []

                for h in headers:
                    row.append({ 'value': item.get(adjusted_names.get(h, h)) })
                rows.append(row)
            results.append(table)

    return 'postgresql_run_query.html'
