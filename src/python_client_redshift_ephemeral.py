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
import copy, json
import re
import unittest
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

global exec_pointer,val_l,val  #[0] -> section name , [1] query_id name
exec_pointer,val_l,val = [],[],[]


s3 = boto3.resource('s3')
#configuration
s3_bucket = 'jeetesh-redshiftdevops-cendelete'
execution_pointer_path_name='exec_pointer/exec_pointer.json'
test_pointer_path_name='test_ini/test_pointer.json'

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
    return_formed_query(*args)

def identify_objects_for_rollback(config_file_dict,rollback_section):
    #Identify sections after the rollback to section
    section_list = []
    stmt = ''
    objectName = []
    objectType = []
    for k,v in config_file_dict.items():
        section_list.append(k)
    #Iterate across identified sections to extract objects/tables
    indexes = [i for i, x in enumerate(section_list) if x == rollback_section]
    rollback_section_list = section_list[indexes[0]:]
    #rollforward_section_list = section_list[:indexes[0]]
    for item in rollback_section_list:
        for k,v in config_file_dict[item].items():
            stmt = v
            object_operation = stmt.split(' ')[0]
            if stmt.split(' ')[1].lower() == 'table':
                object_type = 'table'
                if "." in stmt:
                    x = ((stmt.split(' ')[2]).split(".")[1]).split("(")[0]
                else:
                    x = (stmt.split(' ')[2]).split("(")[0]
            else:
                object_type = stmt.split(' ')[3]
                if "." in stmt:
                    x = ((stmt.split(' ')[4]).split(".")[1]).split("(")[0]
                else:
                    x = (stmt.split(' ')[4]).split("(")[0]
            if x not in objectName:
                objectName.append(x)
                objectType.append(object_type)
        return objectName, objectType


def rename_objects_for_backup(object_name,object_type,rollback_section):
    #generate backup script for naming the table
    backup_stmt = []
    rollforward_stmt = []
    for i in range (0,len(object_type)):
            if object_type[i].lower() == 'table':
                backup_stmt.append('Alter table ' + object_name[i] + ' rename to ' + object_name[i] + '_bckup_' + str(time.time_ns()) +';') #allow multiple executions.
    #call procedure to redeploy DDL until the rollback section.
    for section in config.sections():
        if section != rollback_section:
            for key, val in config.items(section):
                for i in object_name:
                    if i in val and (('create' in val) or ('alter' in val)):
                        rollforward_stmt.append(val)
                    else:
                        None
    #return rollforward_stmt
    rollforward_stmt_final = list(dict.fromkeys(rollforward_stmt))
    return backup_stmt,rollforward_stmt_final

def read_config_file_rollback(config_file_name):
    config.read(config_file_name)
    dict_x = {}  # empty dictionary
    try:
        for section in config.sections():
            dict_x[section] ={} # add a new section for the dictionary
            for key, val in config.items(section):
                dict_x[section][key] = val
    except Exception as e:
        print(e)
    return dict_x

#need to have a way to read and write a datastructure from s3
def read_and_write_execution_pointer(operation,listname,bucketname,path_name=None):
    bucket = s3.Bucket(bucketname)
    if operation == 'read':
        obj = s3.Object(bucketname, path_name)
        result = obj.get()['Body'].read()
        return_pointer = result.decode("utf-8")
        return return_pointer
    else:
        try:
            jsonstr = json.dumps(listname)
            print(jsonstr)
            bucket = bucketname
            path = path_name
            s3.Bucket(bucket).put_object(Key=path, Body=jsonstr)
            print('upload successfully completed')
        except Exception as e:
            print("Unexpected error: %s" % e)
        return


#return a list from s3 data
def parse_list(s):
    final = [re.sub(r"[^a-zA-Z0-9_]+", '', k) for k in s.split(",")]
    i = 0
    final_list = []
    for i in range (0,len(final)-1):
        l = []
        if i < len(final):
            l.extend((final[i],final[i+1]))
            final.pop(i+1)
        i = i + 1
        final_list.append((l))
    final = list(filter(None,final_list))
    return final


#convert config file to a dictionary
def read_config_file(config_file_name=None, pointer_name=None):
    pointer = pointer_name
    config.clear()
    config.read(config_file_name)
    dict_x = {}  # empty dictionary
    try:
        for section in config.sections():
            dict_x[section] ={} # add a new section for the dictionary
            for key1, val1 in config.items(section):
                dict_x[section][key1] = val1
            #Read execution pointer delete unwanted keys and return
            a = {}
            a = copy.deepcopy(dict_x)
            for item in pointer:
                for key, val in a.items():
                    if key == item[0]:
                        for k, v in val.items():
                            if k == item[1]:
                                del(dict_x[key][k])

        print(dict_x)
        return dict_x
    except Exception as e:
        print(e)



def return_formed_query(operation=None,config_file_name=None,section_name=None,query_id=None,output=None,clusterconfigfile=None,clusterconfigparm=None,pointer=None):
    dict_parsed = read_config_file(config_file_name, pointer_name=pointer)
    val_l = []
    l_t_exec_pointer = []
    val = []
    if query_id != None: query_id = query_id.lower() #convert to lower case
    try:
        if operation == 'rollforward':
            if section_name == 'ALL': # parse dictionary based on the values passsed
                for section in dict_parsed:
                    for key in dict_parsed[section]:
                        val_l.append(dict_parsed[section][key])
                        l_t_exec_pointer.append([section, key])
                pointer.extend(l_t_exec_pointer)
            else:
                if query_id == 'ALL' or query_id == 'all':
                    for v in dict_parsed[section_name].values():
                        val_l.append(v)
                else:
                    v = dict_parsed[section_name][query_id]
                    val_l.append(v)
            val= val_l
        else:
            print('entered rollbackward loop')
            dict_parsed = read_config_file_rollback(config_file_name)
            #identify objects to be rolledback
            object_name, object_type = identify_objects_for_rollback(dict_parsed, section_name)
            ddl_list = rename_objects_for_backup(object_name, object_type, rollback_section=section_name)
            # Execute alter statements on the database
            val_l = ddl_list[0]
            val_l.extend((ddl_list[1]))
            print(val_l)
            #remove all entries in the execution pointer after the rollback value.
            #determine index value of the 1st occurence
            #substring and remove all entries until the end of the list
            index_val = -1
            for item in pointer:
                for items in item:
                    if section_name in items and index_val ==-1:
                        index_val = pointer.index(item)
            rollback_pointer= pointer[0:index_val] #generate new pointer value
            pointer = rollback_pointer
            val = val_l
    except Exception as e:
        print(e)
    return val,pointer


# def read_config_file(config_file_name):
#     config.read(config_file_name)
#     dict_x = {}  # empty dictionary
#     try:
#         for section in config.sections():
#             dict_x[section] ={} # add a new section for the dictionary
#             for key, val in config.items(section):
#                 dict_x[section][key] = val
#     except Exception as e:
#         print(e)
#     #print(dict_x)
#     return dict_x
#
# # return formatted query for execution
# def return_formed_query(operation=None,config_file_name=None,section_name=None,query_id=None,output=None,clusterconfigfile=None,clusterconfigparm=None):
#     dict_parsed = read_config_file(config_file_name)
#     #print(dict_parsed)
#     #val = []
#     if query_id != None: query_id = query_id.lower() #convert to lower case
#     try:
#         if operation == 'rollforward':
#             #print(section_name)
#             if section_name == 'ALL': # parse dictionary based on the values passsed
#                 for section in dict_parsed:
#                     for key in dict_parsed[section]:
#                         val.append(dict_parsed[section][key])
#             else:
#                 if query_id == 'ALL' or query_id == 'all':
#                     for v in dict_parsed[section_name].values():
#                         val.append(v)
#                 else:
#                     v = dict_parsed[section_name][query_id]
#                     val.append(v)
#         else:
#            # Check on steps for rollback execution
#             if query_id == 'None':
#                 v = dict_parsed[section_name].values()
#             else:
#                 v = dict_parsed[section_name][query_id]
#             val.append(v)
#     except Exception as e:
#         print(e)
#     #val.append('abc')
#     print(val)
#     return val

def validate_test_case(test_case_num,output,expected_output):
    try:
        assert output == expected_output
        print("verify results of test case:" + test_case_num)
    except Exception as e:
        print(e)
    return


def create_cluster_and_execute_query(clusterconfigfile, clusterconfigparm,output):
    c1 = RedshiftEphemeral(clusterconfigfile, clusterconfigparm)
    #c1.create_cluster()
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
    #Read pointer object from s3
    exec_pointer_str = read_and_write_execution_pointer(operation='read', listname='exec_pointer.json',
                                                    bucketname=s3_bucket,path_name=execution_pointer_path_name)
    exec_pointer = parse_list(exec_pointer_str)
    print('*********************************************')
    print('execution_pointer', exec_pointer)
    print('*********************************************')
    exec_pointer_new = return_formed_query(operation=sys.argv[1],config_file_name=sys.argv[2],section_name=sys.argv[3]
                                           ,query_id=sys.argv[4],output=sys.argv[5],clusterconfigfile=sys.argv[6],clusterconfigparm=sys.argv[7]
                                           ,pointer=exec_pointer)

    print('DDL statement to execute:',exec_pointer_new[0])
    print('Execution pointer:', exec_pointer_new[1])
    #write updated execution pointer to S3
    read_and_write_execution_pointer(operation='write', listname=exec_pointer_new[1],
                                     bucketname=s3_bucket,
                                     path_name=execution_pointer_path_name)

    #execute statement to capture
    x = exec_pointer_new[0]
    for i in range(len(x)):
        result = c1.execute_sql(x[i], 'statement id')
        print('============statement', i, 'execution results============================')
        if result == None:
            print('No results - statement executed successfully')
        else:
            df2 = c1.convert_results_to_df(result)
            if df2.empty != True:
                if output == 'f':
                    dir = uuid.uuid4().hex.upper()[0:6]
                    os.mkdir('output_data'+'/'+dir)
                    filename = 'output_data' +'/' + dir+ '/' + 'sql_stmt_' + str(i)
                    df2.to_csv(filename, index=False,header=False,quoting=csv.QUOTE_NONE,escapechar=' ')
                else:
                    print(df2)
            else:
                print('No result returned, please verify statement execution:', x[i])
    print('================query execution successfully completed====================================')
    time.sleep(10)
    #Execute test cases and capture result
    print('=======================Executing test cases=============================================')
    test_pointer_str = read_and_write_execution_pointer(operation='read', listname='test_pointer.json',
                                                    bucketname=s3_bucket,path_name=test_pointer_path_name)
    test_pointer = parse_list(test_pointer_str)
    print('test pointer', test_pointer)
    test_pointer_new = return_formed_query(operation='rollforward',config_file_name='test_cases.ini',section_name='TESTSUITE_v01' #[TESTSUITE_v01] contains testcases
                                           ,query_id='ALL',output='s',clusterconfigfile=None,clusterconfigparm=None
                                           ,pointer=test_pointer)
    test_pointer_new_results = return_formed_query(operation='rollforward',config_file_name='test_cases.ini',section_name='RESULTS' #[RESULTS] contains testcase results
                                           ,query_id='ALL',output='s',clusterconfigfile=None,clusterconfigparm=None
                                           ,pointer=test_pointer)
    #execute statement to capture
    x = test_pointer_new[0]

    for i in range(len(x)):
        result = c1.execute_sql(x[i], 'statement id')
        print('============statement', i, 'execution results============================')
        if result == None:
            print('No results - statement executed successfully')
        else:
            df2 = c1.convert_results_to_df(result)
            df2_value = df2.iloc[:,0].values.tolist()
            df2_value_list = [str(j) for j in df2_value]
            print('expected_output',test_pointer_new_results[0][i])
            print('output',df2_value_list[0])
            print('test_case_num',str(i))
            validate_test_case(output=df2_value_list[0],expected_output=test_pointer_new_results[0][i],test_case_num=str(i))
            if df2.empty != True:
                if output == 'f':
                    dir = uuid.uuid4().hex.upper()[0:6]
                    os.mkdir('output_data'+'/'+dir)
                    filename = 'output_data' +'/' + dir+ '/' + 'sql_stmt_' + str(i)
                    df2.to_csv(filename, index=False,header=False,quoting=csv.QUOTE_NONE,escapechar=' ')
            else:
                print('No result returned, please verify statement execution:', x[i])
    print('================Test case execution successfully completed======================')
    #write updated execution pointer to S3
    read_and_write_execution_pointer(operation='write', listname=[],
                                     bucketname=s3_bucket,
                                     path_name=test_pointer_path_name)
    #delete cluster
    #y = c1.delete_cluster()

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
        # adding random characters for testing
if __name__ == "__main__":
    main()
    #testing