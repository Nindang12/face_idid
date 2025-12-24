#!/bin/bash

# Script chạy Spark Streaming worker trên máy worker
# Sử dụng: ./run_worker.sh [branch_id]

BRANCH_ID=${1:-0}

echo "🚀 Khởi động Spark Streaming Worker..."
echo "📍 Branch ID: $BRANCH_ID"

# Kiểm tra file .env
if [ ! -f .env ]; then
    echo "⚠️  File .env không tồn tại. Đang tạo từ .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        # Cập nhật DEFAULT_BRANCH_ID
        sed -i "s/DEFAULT_BRANCH_ID=0/DEFAULT_BRANCH_ID=$BRANCH_ID/" .env
    else
        echo "❌ Không tìm thấy .env.example. Vui lòng tạo file .env thủ công."
        exit 1
    fi
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo "📊 Cấu hình:"
echo "   - Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo "   - Spark Master: $SPARK_MASTER"
echo "   - Database: $DATABASE_URL"
echo "   - Branch ID: $DEFAULT_BRANCH_ID"
echo ""

# Kiểm tra kết nối Kafka
echo "🔍 Kiểm tra kết nối Kafka..."
if command -v nc &> /dev/null; then
    KAFKA_HOST=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f1)
    KAFKA_PORT=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f2)
    if nc -z -v -w5 $KAFKA_HOST $KAFKA_PORT 2>&1 | grep -q succeeded; then
        echo "✅ Kafka đã sẵn sàng tại $KAFKA_BOOTSTRAP_SERVERS"
    else
        echo "❌ Không thể kết nối đến Kafka tại $KAFKA_BOOTSTRAP_SERVERS"
        echo "   Vui lòng kiểm tra Kafka đã chạy trên máy chủ chính chưa"
        exit 1
    fi
fi

# Kiểm tra kết nối Database
echo "🔍 Kiểm tra kết nối Database..."
if command -v psql &> /dev/null; then
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    if nc -z -v -w5 $DB_HOST $DB_PORT 2>&1 | grep -q succeeded; then
        echo "✅ Database đã sẵn sàng tại $DB_HOST:$DB_PORT"
    else
        echo "❌ Không thể kết nối đến Database tại $DB_HOST:$DB_PORT"
        echo "   Vui lòng kiểm tra PostgreSQL đã chạy trên máy chủ chính chưa"
        exit 1
    fi
fi

echo ""
echo "🎯 Khởi động Spark Streaming Worker..."
echo ""

# Chạy Spark Streaming
python -m app.spark_streaming

