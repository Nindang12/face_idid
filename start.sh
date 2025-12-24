#!/bin/bash

echo "🚀 Starting Face Recognition System..."

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
echo "📱 Web Interface: http://localhost:8000"
echo "📊 Kafka UI: http://localhost:8080"
echo "⚡ Spark Master: http://localhost:8081"
echo ""
echo "💡 To start Spark Streaming, run:"
echo "   docker exec -it faceid-web python -m app.spark_streaming"
echo ""

