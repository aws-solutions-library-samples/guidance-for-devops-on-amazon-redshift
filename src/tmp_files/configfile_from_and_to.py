import configparser
config = configparser.ConfigParser(interpolation=None)

global val
global l_section_name
global l_query_id
l_section_name = []
l_query_id = []
val=[]

l_section_name.append('DDL_v02') #from
l_section_name.append('DDL_v05') #to , value in to is included as well.

l_query_id.extend(('query0','query2')) #selected query id , to query id is included
l_query_id.extend(('query0','query0')) #all query id

print('l_section_name',l_section_name)
print('l_query_id',l_query_id)

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

#parse list and return only neede queries
def list_seg(l,start_val,end_val):
    start_index=l.index(start_val)
    end_index=l.index(end_val)
    if end_index < len(l):
        end_index= end_index+1
    else:
        end_index=end_index
    new_list = l[start_index:end_index]
    #print('new_list is:',new_list)
    return new_list

# return formatted query for execution
def return_formed_query(operation=None,config_file_name=None,section_name=None,query_id=None,output=None,clusterconfigfile=None,clusterconfigparm=None):
    dict_parsed = read_config_file(config_file_name)
    if query_id != None: query_id = query_id.lower() #convert to lower case
    try:
        final_queries = []
        val = []
        if operation == 'rollforward':
                if l_section_name[0] == 'ALL' and l_section_name[0] == 'ALL' : # parse dictionary based on the values passsed
                    for section in dict_parsed:
                        for key in dict_parsed[section]:
                            val.append(dict_parsed[section][key])
                    print(val)
                elif l_section_name[1] == 'ALL':
                        section_name_start = l_section_name[0]
                        z = list(dict_parsed).index(section_name_start)
                        for i, (k,v) in enumerate (dict_parsed.items()):
                            # print(i)
                            # print(k,v)
                            if i >=z:
                                #print(i)
                                val.append(v)
                        print(val)
                # else:
                #     v = dict_parsed[section_name][query_id]
                #     val.append(v)
                else:
                    #read sections to be processed
                    for section in l_section_name:
                        l_total_query_id = []

                        start_val = l_query_id[2*l_section_name.index(section)]
                        end_val   = l_query_id[2*l_section_name.index(section) + 1]
                        # 0,0 -> 0; 0,1 -> 0,1; 0,3 -> 0,1,2,3
                        for items in config.sections():
                            if items == section:
                                for key, val in config.items(section):
                                     #print(key)
                                     l_total_query_id.append(key)
                        z = list_seg(l_total_query_id,start_val, end_val)
                        print('value of z is:', z)
                        val = ''
                        for queryid in z:
                            final_queries.append((dict_parsed[section][queryid]))
                        # final_queries = final_queries + val
                        print(final_queries)
                        return final_queries


        #if operation == 'rollforward':


        # if operation == 'rollforward':
        #     if section_name == 'ALL': # parse dictionary based on the values passsed
        #         for section in dict_parsed:
        #             for key in dict_parsed[section]:
        #                 val.append(dict_parsed[section][key])
        #     else:
        #         if query_id == 'ALL' or query_id == 'all':
        #             for v in dict_parsed[section_name].values():
        #                 val.append(v)
        #         else:
        #             v = dict_parsed[section_name][query_id]
        #             val.append(v)
        # else:
        #    # Check on steps for rollback execution
        #     if query_id == 'None':
        #         v = dict_parsed[section_name].values()
        #     else:
        #         v = dict_parsed[section_name][query_id]
        #val.append(v)
    except Exception as e:
        print(e)





if __name__=="__main__":
    y = read_config_file('../query_redshift_api.ini')
    #print(y)
    return_formed_query(operation='rollforward', config_file_name='../query_redshift_api.ini', section_name='DDL_v02', query_id='ALL', output=None, clusterconfigfile=None, clusterconfigparm=None)