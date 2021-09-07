### Redshift Cluster Data Analyzer

The script run by this Docker container will produce CSV data about the desired cluster, used to evaluate the cluster's
health.

It requires that you have docker installed on the system you're going to run it from.

It works by executing a python script inside the container, which connects to a Redshift cluster. It runs some 
analysis queries, which are saved as CSV files.  These files are made accessible outside of the container by mounting
a volume to the container when run (see details below).

#### Building the Docker container

This step will build a self-contained environment to run the script.

It starts with a base Python 2 image, copies over the files, and installs required dependencies.

Run the command in the same directory the script exists in.

    docker build . -t redshift_analyzer

#### Running the Docker container

The following command will execute the script inside the container.

It requires the following environment variables to be set, via the `-e` flag.

    PROD_REDSHIFT_HOST: The hostname of the cluster to connect to for analysis.
    PROD_REDSHIFT_DB: the name of the database to connect to.
    PROD_REDSHIFT_USERNAME: The username to connect as.
    PGPASSWORD: The password of the supplied username.

First, create an empty directory on your local filesystem where you'd like the output results to be stored, and change
into that directory.

    docker run -it -e PROD_REDSHIFT_HOST="<hostname>" -e PROD_REDSHIFT_DB="<db_name>" \ 
                   -e PROD_REDSHIFT_USERNAME="<username>" -e PGPASSWORD="<username_password>" \ 
                   -v </path/to/your/new_data_directory>:/result_data redshift_analyzer 
