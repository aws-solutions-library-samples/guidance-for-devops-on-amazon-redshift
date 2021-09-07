import getopt, pgdb, json, csv, os, sys, time
from getpass import getpass

'''
host = input("Cluster Host: ")
db = input("Database Name: ")
user = input("User: ")
port = input("Port: ")
password = getpass("Password: ")
'''

import os
import psycopg2
import codecs

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

codecs.register_error("strict", codecs.ignore_errors)

result_directory = "/result_data/"
host = os.environ["PROD_REDSHIFT_HOST"]
db = os.environ["PROD_REDSHIFT_DB"]
user = os.environ["PROD_REDSHIFT_USERNAME"]
port = "5439"
password = os.environ["PGPASSWORD"]

f = open('config.json')
data = json.load(f)

dir = result_directory + 'data-' + time.strftime('%Y%m%d%H%M%S')
os.makedirs(dir)

# conn = pgdb.connect(database=db, host=host, user=user, password=password, port=port)
conn = psycopg2.connect(database=db, host=host, user=user, password=password, port=port)
conn.set_client_encoding('UTF8')


cur = conn.cursor()
for name in data["Sections"]:
    section = data["Sections"][name]
    print("Executing SQL: " + section["SQL"])
    cur.execute(section["SQL"])
    results = cur.fetchall()
    with open(dir+"/"+name+".csv", 'w') as f:
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC, quotechar='\'')
        colnames = [desc[0] for desc in cur.description]
        writer.writerow(colnames)
        for row in results:
            writer.writerow(row)
cur.close()
conn.close()


