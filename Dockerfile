FROM python:3.10-slim

ENV PYTHONUNBUFFERED 1

# set the working directory inside the container
WORKDIR /app
COPY . /app

# install wget
RUN apt-get update && apt-get install --no-install-recommends -y wget

# install loacl dependancies
RUN pip install -r requirements.txt

# here we can run tests once we have this working

# run the main application loop
CMD python3 main.py