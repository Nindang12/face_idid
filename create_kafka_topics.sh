#!/bin/bash

# Script để tạo Kafka topics cần thiết
# Sử dụng: ./create_kafka_topics.sh

echo "📦 Creating Kafka topics..."

# Get Kafka container name
KAFKA_CONTAINER=$(docker compose ps -q kafka)

if [ -z "$KAFKA_CONTAINER" ]; then
    echo "❌ Kafka container not found. Is it running?"
    exit 1
fi

echo "✅ Kafka container found: $KAFKA_CONTAINER"

# Try kafka-topics (newer) first, fallback to kafka-topics.sh (older)
KAFKA_TOPICS_CMD="kafka-topics"
if ! docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
    KAFKA_TOPICS_CMD="kafka-topics.sh"
fi

echo "📋 Using command: $KAFKA_TOPICS_CMD"

# Check if topics already exist
EXISTING_TOPICS=$(docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD --bootstrap-server localhost:9092 --list 2>/dev/null || echo "")

# Create face-recognition-tasks topic
if echo "$EXISTING_TOPICS" | grep -q "face-recognition-tasks"; then
    echo "✅ Topic 'face-recognition-tasks' already exists"
else
    echo "🔨 Creating topic 'face-recognition-tasks'..."
    docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD \
        --create \
        --bootstrap-server localhost:9092 \
        --topic face-recognition-tasks \
        --partitions 3 \
        --replication-factor 1
    
    if [ $? -eq 0 ]; then
        echo "✅ Topic 'face-recognition-tasks' created successfully"
    else
        echo "❌ Failed to create topic 'face-recognition-tasks'"
    fi
fi

# Create face-recognition-results topic
if echo "$EXISTING_TOPICS" | grep -q "face-recognition-results"; then
    echo "✅ Topic 'face-recognition-results' already exists"
else
    echo "🔨 Creating topic 'face-recognition-results'..."
    docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD \
        --create \
        --bootstrap-server localhost:9092 \
        --topic face-recognition-results \
        --partitions 3 \
        --replication-factor 1
    
    if [ $? -eq 0 ]; then
        echo "✅ Topic 'face-recognition-results' created successfully"
    else
        echo "❌ Failed to create topic 'face-recognition-results'"
    fi
fi

echo ""
echo "📊 List of topics:"
docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD --bootstrap-server localhost:9092 --list 2>/dev/null | sed 's/^/   - /'

echo ""
echo "✅ Done!"


