# File: postgresql_connector.py
# Copyright (c) 2017-2021 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

# Phantom App imports
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

try:
    # Fix Library Import
    # NOTE: These need to be loaded in this order
    from ctypes import cdll
    if hasattr(BaseConnector, 'get_phantom_home'):
        home_dir = BaseConnector._get_phantom_home()
    else:
        home_dir = '/opt/phantom'
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libkeyutils-1-ff31573b.2.so')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libresolv-2-c4c53def.5.so')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libsepol-b4f5b513.so.1')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libselinux-cf8f9094.so.1')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libkrb5support-d7ce89d4.so.0.1')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libresolv-2-c4c53def.5.so')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libk5crypto-622ef25b.so.3.1')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libcom_err-beb60336.so.2.1')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libkrb5-fb0d2caa.so.3.3')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libz-a147dcb0.so.1.2.3')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libgssapi_krb5-174f8956.so.2.2')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libcrypto-aa58ed98.so.1.0.2k')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libssl-cdf7ba29.so.1.0.2k')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/liblber-2-14d46c3c.4.so.2.10.7')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libsasl2-e96a0dbf.so.2.0.22')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libldap_r-2-3a9294b6.4.so.2.10.7')
    cdll.LoadLibrary(home_dir + '/usr/lib64/python2.7/site-packages/psycopg2/.libs/libpq-9c51d239.so.5.9')
except:
    pass

# Usage of the consts file is recommended
# from postgresql_consts import *
import csv
import json
import psycopg2
import requests
from datetime import date, datetime


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class PostgresqlConnector(BaseConnector):

    def __init__(self):
        super(PostgresqlConnector, self).__init__()

    def _initialize_error(self, msg, exception=None):
        if self.get_action_identifier() == "test_connectivity":
            self.save_progress(msg)
            self.save_progress(str(exception))
            self.set_status(phantom.APP_ERROR, "Test Connectivity Failed")
        else:
            self.set_status(phantom.APP_ERROR, msg, exception)
        return phantom.APP_ERROR

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        host = config['host']
        username = config['username']
        password = config['password']
        database = config['database']
        other = config.get('other')

        if other:
            try:
                other_dict = json.loads(other)
            except Exception as e:
                return self._initialize_error("'other' is invalid", e)
        else:
            other_dict = {}

        try:
            self._connection = psycopg2.connect(
                user=username, password=password,
                dbname=database, host=host,
                **other_dict
            )
            self._cursor = self._connection.cursor()
        except Exception as e:
            return self._initialize_error("db login error", e)
        self.save_progress("Database connection established")
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        query = "SELECT version();"
        try:
            self._cursor.execute(query)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Test Connectivity Failed", e
            )

        for row in self._cursor:
            self.save_progress("Using: {}".format(row))

        self.save_progress('Test Connectivity Passed')
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_format_vars(self, param):
        format_vars = param.get('format_vars')
        if format_vars:
            format_vars = next(csv.reader([format_vars], quotechar='"', skipinitialspace=True, escapechar='\\'))
        return format_vars

    def _handle_run_query(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        query = param['query']
        format_vars = self._get_format_vars(param)
        try:
            self._cursor.execute(query, format_vars)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Error running query", e
            )

        if not param.get('no_commit', False):
            try:
                self._connection.commit()
            except Exception as e:
                return action_result.set_status(
                    phantom.APP_ERROR, "Unable to commit changes", e
                )

        # Transform output to include column names
        try:
            columns = self._cursor.description

            result = []
            for value in self._cursor.fetchall():
                info = {}
                for index, column in enumerate(value):
                    if isinstance(column, (datetime, date)):
                        column = column.isoformat()
                    info[columns[index][0]] = column
                result.append(info)
        except Exception as e:
            # This probably means it was a query like an insert or something that didn't return any rows
            self.debug_print("Unable to retrieve results from query: {}".format(str(e)))
            result = []

        for row in result:
            action_result.add_data(row)

        summary = action_result.update_summary({})
        if self._cursor.rowcount > 0:
            summary['total_rows'] = self._cursor.rowcount
        else:
            summary['total_rows'] = 0

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully ran query")

    def _handle_list_columns(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        table_name = param['table_name']
        table_schema = param.get('table_schema', 'public')

        # First check if table exists
        query = "SELECT * FROM information_schema.tables WHERE table_name = %s and table_schema = %s;"
        try:
            self._cursor.execute(query, (table_name, table_schema))
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Error listing columns", e
            )

        results = self._cursor.fetchall()
        if len(results) == 0:
            return action_result.set_status(phantom.APP_ERROR, "The specified table could not be found")

        # Check the columns
        query = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS where table_name = %s and table_schema = %s;"
        try:
            self._cursor.execute(query, (table_name, table_schema))
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Error listing columns", e
            )

        columns = self._cursor.description
        result = [{columns[index][0]:column for index, column in enumerate(value)} for value in self._cursor.fetchall()]

        for row in result:
            action_result.add_data(row)
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed all columns")

    def _handle_list_tables(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        table_schema = param.get('table_schema', 'public')

        # Check for existance of table schema
        query = "select * from information_schema.schemata where schema_name = %s;"
        try:
            self._cursor.execute(query, (table_schema,))
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Error retrieving schemata", e
            )

        results = self._cursor.fetchall()
        if len(results) == 0:
            return action_result.set_status(phantom.APP_ERROR, "No matching table schemas could be found")

        # Check for tables
        query = "select * from information_schema.tables where table_schema = %s;"
        try:
            self._cursor.execute(query, (table_schema,))
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, "Error listing tables", e
            )

        # Transform output to include column names
        columns = self._cursor.description
        result = [{columns[index][0]:column for index, column in enumerate(value)} for value in self._cursor.fetchall()]

        for row in result:
            action_result.add_data(row)
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed all tables")

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'run_query':
            ret_val = self._handle_run_query(param)

        elif action_id == 'list_columns':
            ret_val = self._handle_list_columns(param)

        elif action_id == 'list_tables':
            ret_val = self._handle_list_tables(param)

        return ret_val


if __name__ == '__main__':

    import pudb
    import argparse

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if (username is not None and password is None):

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if (username and password):
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = PostgresqlConnector()
        connector.print_progress_message = True

        if (session_id is not None):
            in_json['user_session_token'] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)
