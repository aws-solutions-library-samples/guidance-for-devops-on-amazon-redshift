import configparser
from configparser import SafeConfigParser
config = configparser.ConfigParser(interpolation=None)
import boto3
import json
import re
import copy
import io
s3 = boto3.resource('s3')

global exec_pointer  #[0] -> section name , [1] query_id name
exec_pointer = []

global val_l
val_l = []

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
            #print(k,v)
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
        # print(objectName)
        # print(objectType)
        return objectName, objectType


def rename_objects_for_backup(object_name,object_type,rollback_section):
    #generate backup script for naming the table
    backup_stmt = []
    rollforward_stmt = []
    for i in range (0,len(object_type)):
            if object_type[i].lower() == 'table':
                backup_stmt.append('Alter table ' + object_name[i] + ' rename to ' + object_name[i] + '_bckup' + ';')
    print(backup_stmt)
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
    return rollforward_stmt_final

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
    #print(final)
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
    #print(exec_pointer)
    pointer = pointer_name
    config.clear()
    config.read(config_file_name)
    dict_x = {}  # empty dictionary
    try:
        for section in config.sections():
            #print(section)
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

        return dict_x
    except Exception as e:
        print(e)



def return_formed_query(operation=None,config_file_name=None,section_name=None,query_id=None,output=None,clusterconfigfile=None,clusterconfigparm=None,pointer=None):
    dict_parsed = read_config_file(config_file_name, pointer_name=pointer)
    val_l = []
    l_t_exec_pointer = []
    l_pointer = []
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
        else:
            dict_parsed = read_config_file_rollback(config_file_name)
            #identify objects to be rolledback
            object_name, object_type = identify_objects_for_rollback(dict_parsed, section_name)
            ddl_list = rename_objects_for_backup(object_name, object_type, rollback_section=section_name)
            val_l = ddl_list
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
    except Exception as e:
        print(e)
    return val_l,pointer


if __name__=="__main__":
    exec_pointer_str = read_and_write_execution_pointer(operation='read', listname='exec_pointer.json',
                                                    bucketname='jeetesh-redshiftdevops-cendelete',path_name="exec_pointer/exec_pointer.json")
    # test_pointer_str = read_and_write_execution_pointer(operation='read', listname='test_pointer.json',
    #                                                 bucketname='jeetesh-redshiftdevops-cendelete',path_name="testpointer/test_pointer.json")
    exec_pointer = parse_list(exec_pointer_str)
    #print(exec_pointer)
    #test_pointer = parse_list(test_pointer_str)
    # exec_pointer_new = return_formed_query(operation='rollforward',config_file_name='query_redshift_api.ini',section_name='ALL'
    #                                        ,query_id='ALL',output=None,clusterconfigfile=None,clusterconfigparm=None
    #                                        ,pointer=exec_pointer)

    # print('DDL statement to execute:',exec_pointer_new[0])
    # print('Execution pointer:', exec_pointer_new[1])
    # Read and write test pointer
    # test_pointer_str = read_and_write_execution_pointer(operation='read', listname='test_pointer.json',
    #                                  bucketname='jeetesh-redshiftdevops-cendelete',
    #                                  path_name="test_ini/test_pointer.json")
    # test_pointer = parse_list(test_pointer_str)
    # print('new read of value',parse_list(test_pointer_str))
    # test_pointer_new = return_formed_query(operation='rollforward',config_file_name='test_cases.ini',section_name='ALL'
    #                                        ,query_id='ALL',output=None,clusterconfigfile=None,clusterconfigparm=None
    #                                        ,pointer=test_pointer)
    # #print output
    # print('DDL statement to execute:',test_pointer_new[0])
    # print('Execution pointer:', test_pointer_new[1])
    # #Finally, write entry into the file
    # test_pointer_str = read_and_write_execution_pointer(operation='write', listname='test_pointer.json',
    #                                  bucketname='jeetesh-redshiftdevops-cendelete',
    #                                  path_name="test_ini/test_pointer.json")

    rollback_pointer_new = return_formed_query(operation='rollback', config_file_name='../query_redshift_api.ini', section_name='DDL_v02'
                                               , query_id='ALL', output=None, clusterconfigfile=None, clusterconfigparm=None
                                               , pointer=exec_pointer)
    print('rollback statement to execute:', rollback_pointer_new[0])
    print('new pointer value',rollback_pointer_new[1])