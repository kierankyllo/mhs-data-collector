#!/bin/bash



export DEVPROXY=True

./cloud_sql_proxy -instances=mhs-reddit:northamerica-northeast2:mhs-db=tcp:0.0.0.0:5432

# psql -h localhost -d mhs-test -U django -p 5432