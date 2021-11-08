import boto3
import pandas as pd
import numpy as np
pd.set_option('display.max_colwidth', -1)
import configparser

config = configparser.ConfigParser()

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
    return dict_x

def return_formed_query(config_file_name,section_name=None,query_id=None):
    dict_parsed = read_config_file(config_file_name)
    print(dict_parsed)
    val = []
    if query_id != None: query_id = query_id.lower() #convert to lower case
    try:
        if section_name == None: # parse dictionary based on the values passsed
            for section in dict_parsed:
                for key in dict_parsed[section]:
                    val.append(dict_parsed[section][key])
        else:
            if query_id == None:
                for v in dict_parsed[section_name].values():
                    val.append(v)
            else:
                v = dict_parsed[section_name][query_id]
                val.append(v)
    except Exception as e:
        print(e)
    print(val)
    return val

if __name__ == "__main__":
    return_formed_query('../query_redshift_api.ini', 'DML_v01')

