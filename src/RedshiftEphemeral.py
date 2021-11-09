import boto3
import pandas as pd
import numpy as np
pd.set_option('display.max_colwidth',100)
pd.set_option('display.max_rows', 100)
import json
from datetime import datetime
import time
import configparser
import logging

config = configparser.ConfigParser(interpolation=None)

obj = boto3.client('redshift')
obj_data = boto3.client('redshift-data')
iam = boto3.client('iam')

# notes --> audit for logs
# cross VPC redshift


class RedshiftEphemeral:
    def __init__(self, file_name, cluster_group):  # constructor
        config.read_file(open(file_name))
        self.name = config.get(cluster_group, "DWH_CLUSTER_IDENTIFIER")
        self.clusterType = config.get(cluster_group, "DWH_CLUSTER_TYPE")
        self.nodeType = config.get(cluster_group, "DWH_NODE_TYPE")
        self.masterUser = config.get(cluster_group, "DWH_DB_USER")
        self.masterPassword = config.get(cluster_group, "DWH_DB_PASSWORD")
        self.numOfNodes = int(config.get(cluster_group, "DWH_NUM_NODES"))
        self.iamrole = config.get(cluster_group, "DWH_IAM_ROLE_NAME")

    def create_cluster(self):
        print('================================================================')
        print("cluster creation initiated at:", datetime.now())
        try:
            roleArn = iam.get_role(RoleName=self.iamrole)['Role']['Arn']
            response = obj.create_cluster(
                ClusterIdentifier=self.name,
                NodeType=self.nodeType,
                ClusterType=self.clusterType,
                MasterUsername=self.masterUser,
                MasterUserPassword=self.masterPassword,
                NumberOfNodes=self.numOfNodes,
                IamRoles=[roleArn]
            )
        except Exception as e:
            print(e)
        # poll cluster availability
        waiter = obj.get_waiter('cluster_available')
        waiter.wait(
            ClusterIdentifier=self.name,
            MaxRecords=99,
            WaiterConfig={
                'Delay': 10,
                'MaxAttempts': 99
            }
        )
        print('==================================================================')
        print('cluster: ', self.name, ' is available at', datetime.now())
        return response

    def delete_cluster(self):
        # check cluster state
        print('===================================================')
        print('cluster: ', self.name, ' deletion request received', datetime.now())
        try:
            waiter = obj.get_waiter('cluster_available')
            waiter.wait(
                ClusterIdentifier=self.name,
                MaxRecords=99,
                WaiterConfig={
                    'Delay': 6,
                    'MaxAttempts': 99  # check for 1 hour to check cluster state
                }
            )
            response = obj.delete_cluster(
                ClusterIdentifier=self.name,
                SkipFinalClusterSnapshot=True
                # FinalClusterSnapshotIdentifier='finalsnapshot',
                # FinalClusterSnapshotRetentionPeriod=1
            )
        except Exception as e:
            print(e)
        waiter = obj.get_waiter('cluster_deleted')
        waiter.wait(
            ClusterIdentifier=self.name,
            MaxRecords=99,
            WaiterConfig={
                'Delay': 6,
                'MaxAttempts': 99
            }
        )
        print('===================================================')
        print('cluster: ', self.name, ' has been deleted', datetime.now())
        return response

    def pause_cluster(self):
        # check cluster state
        print('===================================================')
        print('cluster: ', self.name, ' pause request received:', datetime.now())
        try:
            response = obj.create_cluster_snapshot(
                SnapshotIdentifier = self.name + 'snapshot'+datetime.now(),
                ClusterIdentifier = self.name,
                ManualSnapshotRetentionPeriod =123
            )
        except Exception as e:
            waiter = obj.get_waiter('snapshot_available')
            waiter.wait(
                ClusterIdentifier=self.name,
                MaxRecords=99,
                WaiterConfig={
                    'Delay': 6,
                    'MaxAttempts': 99
                }
            )
            response = obj.pause_cluster(
                ClusterIdentifier=self.name
            )
        print('===================================================')
        print('cluster: ', self.name, ' has been paused at ', datetime.now())
        return response

    def resume_cluster(self):
        print('================================================================')
        print("cluster resume initiated at:", datetime.now())
        try:
            response = obj.resume_cluster(
                ClusterIdentifier=self.name
              )
        except Exception as e:
            print(e)
        # poll cluster availability
        waiter = obj.get_waiter('cluster_available')
        waiter.wait(
            ClusterIdentifier=self.name,
            MaxRecords=99,
            WaiterConfig={
                'Delay': 10,
                'MaxAttempts': 99
            }
        )
        print('==================================================================')
        print('cluster: ', self.name, ' was available at', datetime.now())
        return response


    def extract_cluster_properties(self):
        clusterProperties = obj.describe_clusters(ClusterIdentifier=self.name)['Clusters'][0]
        keysToShow = ["ClusterIdentifier", "NodeType", "ClusterStatus","'ClusterAvailabilityStatus'" \
                      "MasterUsername", "DBName", "Endpoint", "NumberOfNodes", 'VpcId']

        x = [(k, v) for k, v in clusterProperties.items() if k in keysToShow]
        return pd.DataFrame(data=x, columns=["Key", "Value"])

    def poll_status(self, Id):
        try:
            result = obj_data.describe_statement(Id=Id)
            if result['Status'] == 'FINISHED':
                return result['Status']
            if result['Status'] == 'FAILED':
                return result['Status']
            else:
                return result['Status']
        except Exception as e:
            print(e)

    def execute_sql(self, sql, statementname):
        try:
            waiter = obj.get_waiter('cluster_available')
            waiter.wait(
                ClusterIdentifier=self.name,
                MaxRecords=99,
                WaiterConfig={
                    'Delay': 6,
                    'MaxAttempts': 99
                }
            )
            check_status = True
            # df = RedshiftEphemeral.extract_cluster_properties(self.name)
            # print(df)
            #time.sleep(30)
            start_time = time.time()
            response = obj_data.execute_statement(
                ClusterIdentifier=self.name,
                Database='dev',
                DbUser=self.masterUser,
                Sql=sql,
                StatementName=statementname
            )
            x = response['Id']
            print('Id of request is:', x)
            # print(obj_data.describe_statement(Id=x))
            print('+++++++++++++++++++++++++++++++++++++++++++++++++++++')
            result = obj_data.describe_statement(Id=response['Id'])
            #print(result)
            print(self.poll_status(response['Id']))
            print('+++++++++++++++++++++++++++++++++++++++++++++++++++++')
            while check_status == True:
                print('request status is:', self.poll_status(Id=x))
                if self.poll_status(response['Id']) == 'FINISHED':
                    check_status = False
                    result_output = self.return_results(response['Id'])
                    return result_output
                if self.poll_status(response['Id']) == 'FAILED':
                    check_status = False
                    return 'execution failed'
                    # return results
        except Exception as e:
            print('Error in execution', e)
        end_time = time.time()
        print('Total execution time is:', end_time-start_time)
        return

    def return_results(self, Id):
        try:
            results = obj_data.get_statement_result(Id=Id)
            if results == None:
                results = -1 #set result value as -1
            return results
        except Exception as e:
            #print('inside function return_results',e)
            results = obj_data.describe_statement(Id=Id)
            #print(results)
        return results


    def convert_results_to_df(self,result):
        try:
            if result != -1:
                if 'TotalNumRows' in result and 'ColumnMetadata' in result and 'Records' in result:
                    nrows = result["TotalNumRows"]
                    ncols = len(result["ColumnMetadata"])
                    resultrows = result["Records"]
                else:
                    df1 = pd.DataFrame() #generate an empty dataframe
                    return df1
                col_labels = []
                for i in range(ncols): col_labels.append(result["ColumnMetadata"][i]['label'])
                records = []
                for i in range(nrows):
                    records.append(resultrows[i])
                df = pd.DataFrame(np.array(resultrows), columns=col_labels)  # convert list into dataframe

                row = []
                for i in range(nrows):
                    col = []
                    for j in range(ncols):
                        for k, v in df.iloc[i, j].items():
                            col.append(v)
                    row.append(col)
                df1 = pd.DataFrame(np.array(row), columns=col_labels)
                return df1
            else:
                return 'no result generated by query execution'
        except Exception as e:
            print('There was an exception:', e)


def main():
    pass


if __name__ == "__main__":
    main()
#testing

