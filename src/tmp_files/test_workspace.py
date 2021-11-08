import configparser

write_config = configparser.ConfigParser(interpolation=None)


#write_config.set("Section1","name","Jane")
def create_config_files(input_file_name, output_file_name,obj_type):
    cfgfile = open(output_file_name,'w')

    #read the output file created by extraction proces
    with open (input_file_name) as infile:
        content = infile.read()
        content = content.replace('\n','')
        content = content.replace('  ', ' ')
        content = content.replace('   ', ' ')
        if obj_type == 'view' or obj_type == 'table':
            content_split = content.split('create ')
        if obj_type == 'sp':
            content_split = content.split('; ')
        #input_file_name.close()
    #Create a config file
    count = 0
    for item in content_split:
        count = count + 1
        if obj_type == 'view' or obj_type =='table':
            item = 'create ' + item
        else:
            if obj_type == 'sp':
                #item = 'BEGIN ' + item
                 item = item
        if obj_type == 'view':
            section_name = 'view' + str(count)
        elif obj_type == 'table':
            section_name = 'table' + str(count)
        else: section_name = 'sp' + str(count)
        name = 'query' + str(count)
        write_config.add_section(section_name)
        write_config.set(section_name, name, item)

    write_config.write(cfgfile)
    cfgfile.close()
    print('Total num of items:', len(content_split))
    print("Total count of ;",count)

if __name__ == "__main__":
    #create_config_files('f_sql_stmt_0','view.ini','view')
    #create_config_files('f_sql_stmt_1','tables.ini','table')
    create_config_files('f_sql_stmt_3', 'functions.ini', 'sp')