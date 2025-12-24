#!/bin/bash

# Script cấu hình cho máy worker
# Sử dụng: ./setup_worker.sh [worker_name] [branch_id] [host_ip]
# Ví dụ: ./setup_worker.sh worker1 1 192.168.1.7

WORKER_NAME=${1:-worker1}
BRANCH_ID=${2:-0}
HOST_IP=${3:-""}

echo "🔧 Cấu hình máy worker: $WORKER_NAME"
echo "📍 Branch ID: $BRANCH_ID"

# Nếu không có HOST_IP, hỏi người dùng hoặc đọc từ .env.example
if [ -z "$HOST_IP" ]; then
    if [ -f .env.example ]; then
        # Đọc HOST_IP từ .env.example
        HOST_IP=$(grep "^HOST_IP=" .env.example | cut -d'=' -f2 | tr -d ' ')
        if [ -z "$HOST_IP" ]; then
            # Nếu không tìm thấy, thử đọc từ KAFKA_BOOTSTRAP_SERVERS
            KAFKA_SERVER=$(grep "^KAFKA_BOOTSTRAP_SERVERS=" .env.example | cut -d'=' -f2 | cut -d':' -f1 | tr -d ' ')
            if [ ! -z "$KAFKA_SERVER" ]; then
                HOST_IP=$KAFKA_SERVER
            fi
        fi
    fi
    
    # Nếu vẫn không có, hỏi người dùng
    if [ -z "$HOST_IP" ]; then
        echo "❓ Nhập IP của máy chủ chính (hoặc Enter để dùng 192.168.1.7):"
        read -r HOST_IP
        HOST_IP=${HOST_IP:-192.168.1.7}
    fi
fi

echo "🌐 Host IP: $HOST_IP"

# Tạo thư mục cần thiết
echo "📁 Tạo thư mục..."
mkdir -p uploads known_faces app/templates

# Tạo file .env cho worker
echo "📝 Tạo file .env..."
cat > .env << EOF
# Host IP Configuration
HOST_IP=$HOST_IP

# Kafka Configuration
KAFKA_ADVERTISED_HOST=$HOST_IP
KAFKA_BOOTSTRAP_SERVERS=$HOST_IP:9092

# Spark Configuration
SPARK_HOME=/opt/spark
SPARK_MASTER=spark://$HOST_IP:7077
SPARK_MASTER_HOST=$HOST_IP

# Hadoop Configuration
HADOOP_HOME=/opt/hadoop
HDFS_NAMENODE=hdfs://$HOST_IP:9000
HDFS_DATA_DIR=/face_recognition/data

# Database Configuration
DATABASE_URL=postgresql://faceid:faceid123@$HOST_IP:5433/faceid
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
echo "   - Host IP: $HOST_IP"
echo "   - Kafka: $HOST_IP:9092"
echo "   - Spark Master: spark://$HOST_IP:7077"
echo "   - HDFS: hdfs://$HOST_IP:9000"
echo "   - Database: $HOST_IP:5433"
echo ""
echo "🚀 Để chạy Spark Streaming worker:"
echo "   python -m app.spark_streaming"
echo ""

