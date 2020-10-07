# this is an official Python runtime, used as the parent image
FROM python:3.7.7-slim
#COPY UnBurnt.py UnBurnt.py
#COPY UnBurntAPI.py UnBurntAPI.py
#COPY run.sh run.sh

# set the working directory in the container to /app
WORKDIR /app

# add the current directory to the container as /app
ADD . /app

# execute everyone's favorite pip command, pip install -r
RUN pip install --trusted-host pypi.python.org -r requirements.txt
RUN chmod a+x run.sh

# unblock port 80 for the Bottle app to run on
EXPOSE 8080

# execute the Flask app
CMD ["./run.sh"] 

