# this is an official Python runtime, used as the parent image
FROM python:3-buster
#COPY UnBurnt.py UnBurnt.py
#COPY UnBurntAPI.py UnBurntAPI.py
#COPY run.sh run.sh

# set the working directory in the container to /app
WORKDIR /app

# add the current directory to the container as /app
ADD . /app

# execute everyone's favorite pip command, pip install -r
RUN apt-get update
RUN apt-get install -y gcc g++ python-dev gfortran python3-numpy python3-scipy python3-pip
RUN python3.7m -m pip install --upgrade pip
RUN python3.7m -m pip install --upgrade pip setuptools wheel
RUN python3.7m -m pip install --trusted-host pypi.python.org -r requirements.txt
RUN chmod a+x run.sh

# unblock port 80 for the Bottle app to run on
EXPOSE 8080

# execute the Flask app
CMD ["./run.sh"] 

