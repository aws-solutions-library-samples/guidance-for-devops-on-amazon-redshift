FROM ubuntu:18.04

RUN apt-get update && \
    apt-get install --no-install-recommends -y gcc && \
    apt-get install --no-install-recommends -y python3.7 python3-pip python3.7-dev && \
    apt-get install --no-install-recommends -y vim && \
    apt-get install --no-install-recommends -y curl && \
    apt-get install --no-install-recommends -y unzip && \
    apt-get install python3-setuptools -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/\* /var/tmp/*

#RUN apt-get -y install build-essential
#RUN apt-get -y install python3
#RUN apt-get -y install python3-pip

RUN pip3 install pandas
RUN pip3 install boto3
RUN pip3 install configparser
RUN pip3 install dataclasses
#RUN pip3 install time

RUN mkdir /src
RUN mkdir /src/output_data
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install


COPY src/RedshiftEphemeral.py /src/RedshiftEphemeral.py
COPY src/__init__.py /src/__init__.py
COPY src/python_client_redshift_ephemeral.py /src/python_client_redshift_ephemeral.py
COPY src/dw_config.ini /src/dw_config.ini
COPY src/query_redshift_api.ini /src/query_redshift_api.ini
COPY src/requirements.txt /src/requirements.txt

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_REGION=us-east-1

WORKDIR "/src"

