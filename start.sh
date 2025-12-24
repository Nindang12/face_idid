#!/bin/bash

echo "🚀 Starting Face Recognition System..."

# Load environment variables from .env if exists
if [ -f .env ]; then
    echo "📝 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Get HOST_IP from env or default
HOST_IP=${HOST_IP:-192.168.1.7}

# Create necessary directories
mkdir -p uploads known_faces app/templates

# Start Docker services
echo "📦 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "✅ Checking services status..."
docker-compose ps

echo ""
echo "🎉 System started!"
echo ""
echo "📱 Web Interface: http://${HOST_IP}:8000"
echo "📊 Kafka UI: http://${HOST_IP}:8080"
echo "⚡ Spark Master: http://${HOST_IP}:8080"
echo "🗄️  Hadoop NameNode: http://${HOST_IP}:9870"
echo ""
echo "💡 To start Spark Streaming, run:"
echo "   python -m app.spark_streaming"
echo "   hoặc: ./run_spark_streaming.sh"
echo ""

