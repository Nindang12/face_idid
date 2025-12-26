#!/bin/bash

# Script để chạy Spark Streaming Worker
# Sử dụng: ./run_spark_streaming.sh

echo "🚀 Starting Spark Streaming Worker..."

# Load environment variables from .env if exists
if [ -f .env ]; then
    echo "📝 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Activate virtual environment nếu có
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Display configuration
HOST_IP=${HOST_IP:-192.168.1.9}
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-${HOST_IP}:9092}
SPARK_MASTER=${SPARK_MASTER:-spark://${HOST_IP}:7077}
MINIO_ENDPOINT=${MINIO_ENDPOINT:-${HOST_IP}:9000}
MINIO_BUCKET_NAME=${MINIO_BUCKET_NAME:-face-recognition-data}

echo "📊 Configuration:"
echo "   - Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo "   - Spark Master: $SPARK_MASTER"
echo "   - MinIO Endpoint: $MINIO_ENDPOINT"
echo "   - MinIO Bucket: $MINIO_BUCKET_NAME"
echo ""

# Check Kafka connection
echo "🔍 Checking Kafka connection..."
if command -v nc &> /dev/null; then
    KAFKA_HOST=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f1)
    KAFKA_PORT=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f2)
    if nc -z -v -w5 $KAFKA_HOST $KAFKA_PORT 2>&1 | grep -q succeeded; then
        echo "✅ Kafka is ready at $KAFKA_BOOTSTRAP_SERVERS"
    else
        echo "⚠️  Cannot connect to Kafka at $KAFKA_BOOTSTRAP_SERVERS"
        echo "   Continuing anyway..."
    fi
fi

# Check if required Python packages are installed
echo "🔍 Checking Python packages..."
python3 -c "import face_recognition" 2>/dev/null || { 
    echo "❌ face_recognition not installed. Installing..."
    pip install face-recognition
}
python3 -c "from kafka import KafkaConsumer" 2>/dev/null || { 
    echo "❌ kafka-python not installed. Installing..."
    pip install kafka-python
}
python3 -c "from minio import Minio" 2>/dev/null || { 
    echo "❌ minio not installed. Installing..."
    pip install minio
}

echo ""
echo "🎯 Starting Spark Streaming Worker..."
echo "   Press Ctrl+C to stop"
echo ""

# Run Spark Streaming
python3 -m app.spark_streaming

