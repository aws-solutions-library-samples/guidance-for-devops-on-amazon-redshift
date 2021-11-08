import configparser
config = configparser.ConfigParser()
# file_dir = os.path.dirname(__file__)
# sys.path.append(file_dir)
from RedshiftEphemeral import RedshiftEphemeral

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
    rollforward_section_list = section_list[:indexes[0]]
    for item in rollback_section_list:
        for k,v in config_file_dict[item].items():
            print(k,v)
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
        objectNameFinal =  list(dict.fromkeys(objectName))
        objectTypeFinal = list(dict.fromkeys(objectType))
        print(objectName)
        print(objectType)
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

if __name__ == "__main__":
    op_dict = read_config_file('../query_redshift_api.ini')
    object_name, object_type = identify_objects_for_rollback(op_dict,'DDL_v02')
    ddl_list = rename_objects_for_backup(object_name,object_type,rollback_section='DDL_v02')
    print(ddl_list)
    #forward execution statement
    #check the config file until the section until roll back is issued
    #Extract all statements for object seqeuntially
    #Return a list with the statements to be executed
