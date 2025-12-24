#!/bin/bash

echo "🚀 Starting Spark Streaming for Face Recognition..."

# Load environment variables from .env if exists
if [ -f .env ]; then
    echo "📝 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container..."
    python -m app.spark_streaming
else
    echo "Running locally..."
    # Use HOST_IP from env or default
    HOST_IP=${HOST_IP:-192.168.1.7}
    export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-${HOST_IP}:9092}
    export SPARK_MASTER=${SPARK_MASTER:-spark://${HOST_IP}:7077}
    export HDFS_NAMENODE=${HDFS_NAMENODE:-hdfs://${HOST_IP}:9000}
    
    echo "📊 Configuration:"
    echo "   - Kafka: $KAFKA_BOOTSTRAP_SERVERS"
    echo "   - Spark: $SPARK_MASTER"
    echo "   - HDFS: $HDFS_NAMENODE"
    echo ""
    
    python -m app.spark_streaming
fi

