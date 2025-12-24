#!/bin/bash

# Script để khởi động Spark Streaming Worker

echo "🚀 Starting Spark Streaming Worker..."
echo ""

# Load environment variables from .env if exists
if [ -f .env ]; then
    echo "📝 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if running in virtual environment
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Display configuration
HOST_IP=${HOST_IP:-192.168.1.7}
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-${HOST_IP}:9092}
SPARK_MASTER=${SPARK_MASTER:-spark://${HOST_IP}:7077}
HDFS_NAMENODE=${HDFS_NAMENODE:-hdfs://${HOST_IP}:9000}

echo "📊 Configuration:"
echo "   - Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo "   - Spark Master: $SPARK_MASTER"
echo "   - HDFS Namenode: $HDFS_NAMENODE"
echo "   - HDFS Data Dir: ${HDFS_DATA_DIR:-/face_recognition/data}"
echo ""

# Check Kafka connection
echo "🔍 Checking Kafka connection..."
if command -v nc &> /dev/null; then
    KAFKA_HOST=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f1)
    KAFKA_PORT=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f2)
    if nc -z -v -w5 $KAFKA_HOST $KAFKA_PORT 2>&1 | grep -q succeeded; then
        echo "✅ Kafka is ready at $KAFKA_BOOTSTRAP_SERVERS"
    else
        echo "❌ Cannot connect to Kafka at $KAFKA_BOOTSTRAP_SERVERS"
        echo "   Please check if Kafka is running on the main server"
        exit 1
    fi
fi

# Check if required Python packages are installed
echo "🔍 Checking Python packages..."
python3 -c "import kafka" 2>/dev/null || { echo "❌ kafka-python not installed. Run: pip install kafka-python"; exit 1; }
python3 -c "import hdfs3" 2>/dev/null || python3 -c "import pyarrow.fs" 2>/dev/null || echo "⚠️  Warning: hdfs3 or pyarrow not installed. HDFS saving may not work. Run: pip install hdfs3 pyarrow"

echo ""
echo "🎯 Starting Spark Streaming Worker..."
echo "   Press Ctrl+C to stop"
echo ""

# Run Spark Streaming
python3 -m app.spark_streaming

