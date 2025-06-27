#!/bin/bash

set -e

# Attente des services
echo "Waiting for Spark Master..."
while ! nc -z spark-master 7077; do sleep 1; done
echo "Spark Master is up"

echo "Waiting for MinIO..."
while ! nc -z minio 9000; do sleep 1; done
echo "MinIO is up"

echo "Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U trainuser; do
  sleep 1
done
echo "PostgreSQL is up"

echo "All services are up - executing Spark job"

# 👉 Corrige le problème de Ivy
export HOME=/tmp

# Exécution du job Spark
/opt/bitnami/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/bitnami/spark/transform_html_data.py
