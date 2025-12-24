#!/bin/bash

echo "🚀 Starting Spark Streaming for Face Recognition..."

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container..."
    python -m app.spark_streaming
else
    echo "Running locally..."
    # Make sure Kafka is accessible
    export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}
    python -m app.spark_streaming
fi

