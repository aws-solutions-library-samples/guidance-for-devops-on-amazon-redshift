# val_type_dc.py

import dataclasses
import sys
from typing import List, Any
import configparser
config = configparser.ConfigParser(interpolation=None)
import pandas as pd
import numpy as np
import csv
import time
import os, sys
import boto3
import uuid
#from rollback import rollback
# file_dir = os.path.dirname(__file__)
# sys.path.append(file_dir)
from RedshiftEphemeral import RedshiftEphemeral

USAGE = f"Usage: python {sys.argv[0]} [--help] | operation configfile section_name query_id output clusterconfigfile clusterconfigparm\n\n" \
        f"operation: rollforward or rollback\n" \
        f"config_file: configuration file\n" \
        f"section: section in query file\n" \
        f"query_id: statement query_id\n" \
        f"output:f or s \n" \
        f"clusterconfigfile:f or s \n" \
        f"clusterconfigparm:f or s \n" \



@dataclasses.dataclass
class Arguments:
    operation:   str
    config_file: str
    section_name:     str
    query_id:    str
    output: str
    clusterconfigfile: str  #cluster configuration file
    clusterconfigparm: str  #cluster configuration parameter


global val
val= []
s3_client = boto3.client('s3')



def check_type(obj):
    parm = ''
    for field in dataclasses.fields(obj):
        value = getattr(obj, field.name)
        print(
            f"Value: {value}, "
            f"Expected type {field.type} for {field.name}, "
            f"got {type(value)}"
        )
        if type(value) != field.type:
            print("Type Error")

def validate(args: List[str]):
    if len(args) == 7: # check for argument length
        try:
            arguments = Arguments(*args)
        except TypeError:
            raise SystemExit(USAGE)
    else:
        raise SystemExit(USAGE)
    check_type(arguments)
    #print(arguments)
    #print(*args)
    return_formed_query(*args)

def read_config_file(config_file_name):
    config.read(config_file_name)
    dict_x = {}  # empty dictionary
    try:
        for section in config.sections():
            dict_x[section] ={} # add a new section for the dictionary
            for key, val in config.items(section):
                dict_x[section][key] = val
    except Exception as e:
        print(e)
    #print(dict_x)
    return dict_x

# return formatted query for execution
def return_formed_query(operation=None,config_file_name=None,section_name=None,query_id=None,output=None,clusterconfigfile=None,clusterconfigparm=None):
    dict_parsed = read_config_file(config_file_name)
    #print(dict_parsed)
    #val = []
    if query_id != None: query_id = query_id.lower() #convert to lower case
    try:
        if operation == 'rollforward':
            #print(section_name)
            if section_name == 'ALL': # parse dictionary based on the values passsed
                for section in dict_parsed:
                    for key in dict_parsed[section]:
                        val.append(dict_parsed[section][key])
            else:
                if query_id == 'ALL' or query_id == 'all':
                    for v in dict_parsed[section_name].values():
                        val.append(v)
                else:
                    v = dict_parsed[section_name][query_id]
                    val.append(v)
        else:
           # Check on steps for rollback execution
            if query_id == 'None':
                v = dict_parsed[section_name].values()
            else:
                v = dict_parsed[section_name][query_id]
            val.append(v)
    except Exception as e:
        print(e)
    #val.append('abc')
    print(val)
    return val

def create_cluster_and_execute_query(clusterconfigfile, clusterconfigparm,output):
    c1 = RedshiftEphemeral(clusterconfigfile, clusterconfigparm)
    c1.create_cluster()
    df1 = c1.extract_cluster_properties()
    print(df1)
    # declare a list of sql statements
    x = []
    res = None
    # test with a hello world script execution to check cluster availability state
    print('================Beginning execution of sql statement =====================')
    time.sleep(30)
    i = 0
    j = 0
    while i < 100:
        if j > 95:
            break
        elif res != None:
            j = j + 1
        else:
            i = i + 1
            res = c1.execute_sql("""select 'hello_world!'""", 'stmt_id')
    if j < 95:
        print('Cluster issues please investigate current cluster state')
        return

    print('================Ending execution of sql statement =====================')
    x = val
    for i in range(len(x)):
        df2 = pd.DataFrame()
        result = c1.execute_sql(x[i], 'statement id')
        # print(result)
        print('============statement', i, 'execution results============================')
        # print(result)
        if result == None:
            print('No results - statement executed successfully')
        else:
            df2 = c1.convert_results_to_df(result)
            if not df2.empty:
                if output == 'f':
                    dir = uuid.uuid4().hex.upper()[0:6]
                    os.mkdir('output_data'+'/'+dir)
                    filename = 'output_data' +'/' + dir+ '/' + 'sql_stmt_' + str(i)
                    df2.to_csv(filename, index=False,header=False,quoting=csv.QUOTE_NONE,escapechar=' ')
                else:
                    print(df2)
            else:
                print('No result returned, please verify statement execution:', x[i])
    print('================query execution successfully completed========')
    time.sleep(10)
    #delete cluster
    y = c1.delete_cluster()

def data_export_to_s3(configfile,configparm,s3_bucket_name):
    c2 = RedshiftEphemeral(configfile, configparm)
    data_export_sql_stmt = """select table_schema ,table_name from information_schema.tables 
                                  where table_schema not in ('pg_internal','pg_catalog') and table_type = 'BASE TABLE'"""

    result = c2.execute_sql(data_export_sql_stmt,'statement id')
    df3 = c2.convert_results_to_df(result)
    l_schema_table = df3.values.tolist()

    for items in l_schema_table:
        str = 'COPY ' + items[1] + ' from ' + "'s3://testfolder/" + items[0] + "'"+ ' iam_role ' + "'role_name'" + ' region ' + "'us-west-2'"
        print(str)


    #print(l_table)
        #run query to identify each table name
        #run a loop to read each object and create seperate threads for executing the unload command
        #


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(USAGE)

    if args[0] == "--help":
        print(USAGE)
    else:
        validate(args)
        create_cluster_and_execute_query(clusterconfigfile=sys.argv[6], clusterconfigparm=sys.argv[7],output=None)
        #data_export_to_s3(configfile='dw_config.ini', configparm='DWH',s3_bucket_name=None)
if __name__ == "__main__":
    main()