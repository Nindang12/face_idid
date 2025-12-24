#!/bin/bash

# Script kiểm tra và xem dữ liệu trên Hadoop HDFS

echo "🔍 Kiểm tra Hadoop HDFS..."
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

HOST_IP=${HOST_IP:-192.168.1.7}
HADOOP_HOME=${HADOOP_HOME:-/opt/hadoop}
HDFS_NAMENODE=${HDFS_NAMENODE:-hdfs://${HOST_IP}:9000}
HDFS_DATA_DIR=${HDFS_DATA_DIR:-/face_recognition/data}

echo "📊 Cấu hình:"
echo "   - HDFS Namenode: $HDFS_NAMENODE"
echo "   - HDFS Data Dir: $HDFS_DATA_DIR"
echo ""

# Kiểm tra Hadoop đã cài chưa
if [ ! -d "$HADOOP_HOME" ]; then
    echo "❌ Không tìm thấy Hadoop tại $HADOOP_HOME"
    echo "   Vui lòng cài đặt Hadoop hoặc set HADOOP_HOME trong .env"
    exit 1
fi

# Kiểm tra HDFS đã chạy chưa
echo "🔍 Kiểm tra HDFS đã chạy..."
if ! $HADOOP_HOME/bin/hdfs dfsadmin -report &>/dev/null; then
    echo "⚠️  HDFS có vẻ chưa chạy. Đang thử khởi động..."
    $HADOOP_HOME/sbin/start-dfs.sh
    sleep 5
fi

# Kiểm tra kết nối
echo "🔍 Kiểm tra kết nối HDFS..."
if $HADOOP_HOME/bin/hdfs dfs -ls / &>/dev/null; then
    echo "✅ Kết nối HDFS thành công!"
else
    echo "❌ Không thể kết nối HDFS"
    echo "   Vui lòng kiểm tra:"
    echo "   1. Hadoop đã được khởi động: $HADOOP_HOME/sbin/start-dfs.sh"
    echo "   2. HDFS_NAMENODE trong .env đúng: $HDFS_NAMENODE"
    exit 1
fi

echo ""
echo "📁 Danh sách thư mục trên HDFS:"
$HADOOP_HOME/bin/hdfs dfs -ls /

echo ""
echo "📊 Kiểm tra dữ liệu face recognition:"
if $HADOOP_HOME/bin/hdfs dfs -test -d "$HDFS_DATA_DIR" 2>/dev/null; then
    echo "✅ Thư mục $HDFS_DATA_DIR tồn tại"
    echo ""
    echo "📁 Recognition Results:"
    $HADOOP_HOME/bin/hdfs dfs -ls -R "$HDFS_DATA_DIR/recognition_results" 2>/dev/null || echo "   (chưa có dữ liệu)"
    echo ""
    echo "📁 Errors:"
    $HADOOP_HOME/bin/hdfs dfs -ls -R "$HDFS_DATA_DIR/errors" 2>/dev/null || echo "   (chưa có dữ liệu)"
else
    echo "⚠️  Thư mục $HDFS_DATA_DIR chưa tồn tại"
    echo "   Đang tạo thư mục..."
    $HADOOP_HOME/bin/hdfs dfs -mkdir -p "$HDFS_DATA_DIR/recognition_results"
    $HADOOP_HOME/bin/hdfs dfs -mkdir -p "$HDFS_DATA_DIR/errors"
    echo "✅ Đã tạo thư mục"
fi

echo ""
echo "💡 Để xem chi tiết một file:"
echo "   $HADOOP_HOME/bin/hdfs dfs -cat $HDFS_DATA_DIR/recognition_results/2024/12/18/result_*.json"
echo ""
echo "💡 Để xem tất cả dữ liệu:"
echo "   $HADOOP_HOME/bin/hdfs dfs -ls -R $HDFS_DATA_DIR"

