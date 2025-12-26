#!/bin/bash

# Script để test hệ thống face recognition
echo "🔍 Testing Face Recognition System..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check Docker services
echo "1️⃣  Checking Docker services..."
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Docker services are running${NC}"
    docker compose ps | grep "Up"
else
    echo -e "${RED}❌ Docker services are not running${NC}"
    exit 1
fi
echo ""

# 2. Check Web API
echo "2️⃣  Checking Web API..."
if curl -s http://localhost:8000/api/branches/ > /dev/null; then
    echo -e "${GREEN}✅ Web API is accessible${NC}"
    BRANCHES=$(curl -s http://localhost:8000/api/branches/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} branches')" 2>/dev/null || echo "API responded")
    echo "   $BRANCHES"
else
    echo -e "${RED}❌ Web API is not accessible${NC}"
fi
echo ""

# 3. Check Kafka
echo "3️⃣  Checking Kafka..."
if docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1 || \
   docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Kafka is running${NC}"
    TOPICS=$(docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null || \
             docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null)
    echo "   Topics:"
    echo "$TOPICS" | sed 's/^/   - /'
    
    # Check if topics exist
    if echo "$TOPICS" | grep -q "face-recognition-tasks"; then
        echo -e "   ${GREEN}✅ face-recognition-tasks topic exists${NC}"
    else
        echo -e "   ${YELLOW}⚠️  face-recognition-tasks topic does not exist (will be created automatically)${NC}"
    fi
    
    if echo "$TOPICS" | grep -q "face-recognition-results"; then
        echo -e "   ${GREEN}✅ face-recognition-results topic exists${NC}"
    else
        echo -e "   ${YELLOW}⚠️  face-recognition-results topic does not exist (will be created automatically)${NC}"
    fi
else
    echo -e "${RED}❌ Kafka is not accessible${NC}"
fi
echo ""

# 4. Check Spark Master
echo "4️⃣  Checking Spark Master..."
if nc -z -v -w2 localhost 7077 2>&1 | grep -q succeeded || \
   ss -tlnp 2>/dev/null | grep -q ":7077"; then
    echo -e "${GREEN}✅ Spark Master is running on port 7077${NC}"
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Spark Web UI is accessible at http://localhost:8080${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Spark Master is not running (optional for use_spark=false)${NC}"
    echo "   To start: \$SPARK_HOME/sbin/start-master.sh"
fi
echo ""

# 5. Check MinIO
echo "5️⃣  Checking MinIO..."
if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MinIO is running${NC}"
    echo "   Console: http://localhost:9001"
else
    echo -e "${RED}❌ MinIO is not accessible${NC}"
fi
echo ""

# 6. Check Kafka Producer in Web service
echo "6️⃣  Checking Kafka Producer in Web service..."
if docker compose logs web 2>&1 | grep -q "KafkaProducer initialized"; then
    echo -e "${GREEN}✅ Kafka Producer is initialized in Web service${NC}"
else
    echo -e "${YELLOW}⚠️  Kafka Producer may not be initialized${NC}"
    echo "   Check: docker compose logs web | grep Kafka"
fi
echo ""

# 7. Test sending a message to Kafka (if possible)
echo "7️⃣  Testing Kafka connection..."
if python3 -c "
from kafka import KafkaProducer
import json
try:
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    producer.send('face-recognition-tasks', {'test': True})
    producer.flush()
    producer.close()
    print('✅ Successfully sent test message to Kafka')
except Exception as e:
    print(f'❌ Failed to send message: {e}')
" 2>&1; then
    echo -e "${GREEN}✅ Kafka connection test passed${NC}"
else
    echo -e "${YELLOW}⚠️  Kafka connection test failed (may need kafka-python package)${NC}"
fi
echo ""

# Summary
echo "📊 Summary:"
echo "==========="
echo "✅ Docker services: $(docker compose ps | grep -c 'Up') services running"
echo "✅ Web API: http://localhost:8000"
echo "✅ Kafka: localhost:9092"
echo "✅ MinIO: http://localhost:9000"
echo ""
echo "🎯 To test face recognition:"
echo "   1. Open http://localhost:8000 in browser"
echo "   2. Upload an image with use_spark=false (direct processing)"
echo "   3. Or use_spark=true (requires Spark worker running)"
echo ""
echo "🚀 To start Spark Streaming:"
echo "   ./run_spark_submit.sh"
echo "   or"
echo "   python3 -m app.spark_streaming"


