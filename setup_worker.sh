#!/bin/bash

# Script cấu hình cho máy worker
# Sử dụng: ./setup_worker.sh [worker_name] [branch_id]
# Ví dụ: ./setup_worker.sh worker1 1

WORKER_NAME=${1:-worker1}
BRANCH_ID=${2:-0}

echo "🔧 Cấu hình máy worker: $WORKER_NAME"
echo "📍 Branch ID: $BRANCH_ID"

# Tạo thư mục cần thiết
echo "📁 Tạo thư mục..."
mkdir -p uploads known_faces app/templates

# Tạo file .env cho worker
echo "📝 Tạo file .env..."
cat > .env << EOF
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=192.168.80.147:9092

# Spark Configuration
SPARK_MASTER=spark://192.168.80.147:7077
SPARK_MASTER_HOST=192.168.80.147

# Database Configuration
DATABASE_URL=postgresql://faceid:faceid123@192.168.80.147:5432/faceid
POSTGRES_USER=faceid
POSTGRES_PASSWORD=faceid123
POSTGRES_DB=faceid

# Storage Configuration
UPLOAD_DIR=uploads
KNOWN_FACES_DIR=known_faces

# Branch Configuration
DEFAULT_BRANCH_ID=$BRANCH_ID
EOF

echo "✅ Cấu hình hoàn tất!"
echo ""
echo "📋 Thông tin cấu hình:"
echo "   - Worker: $WORKER_NAME"
echo "   - Branch ID: $BRANCH_ID"
echo "   - Kafka: 192.168.80.147:9092"
echo "   - Spark Master: spark://192.168.80.147:7077"
echo "   - Database: 192.168.80.147:5432"
echo ""
echo "🚀 Để chạy Spark Streaming worker:"
echo "   python -m app.spark_streaming"
echo ""

