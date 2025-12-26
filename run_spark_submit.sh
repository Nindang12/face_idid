#!/bin/bash

# Script để chạy Spark Streaming với spark-submit
# Sử dụng: ./run_spark_submit.sh

echo "🚀 Starting Spark Structured Streaming with spark-submit..."

# Load environment variables from .env if exists
if [ -f .env ]; then
    echo "📝 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Kiểm tra SPARK_HOME
if [ -z "$SPARK_HOME" ]; then
    echo "⚠️  SPARK_HOME not set. Trying to find Spark..."
    if [ -d "/opt/spark" ]; then
        export SPARK_HOME=/opt/spark
        echo "✅ Found Spark at /opt/spark"
    elif [ -d "$HOME/spark" ]; then
        export SPARK_HOME=$HOME/spark
        echo "✅ Found Spark at $HOME/spark"
    else
        echo "❌ SPARK_HOME not found. Please set SPARK_HOME environment variable."
        echo "   Example: export SPARK_HOME=/opt/spark"
        exit 1
    fi
fi

# Kiểm tra spark-submit
if [ ! -f "$SPARK_HOME/bin/spark-submit" ]; then
    echo "❌ spark-submit not found at $SPARK_HOME/bin/spark-submit"
    exit 1
fi

echo "✅ Using Spark at: $SPARK_HOME"

# Lấy config từ environment hoặc defaults
HOST_IP=${HOST_IP:-192.168.1.9}
SPARK_MASTER=${SPARK_MASTER:-spark://${HOST_IP}:7077}
# Kafka bootstrap servers - thử localhost trước, fallback về HOST_IP
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}
if ! nc -z -v -w2 $(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f1) $(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f2) 2>/dev/null; then
    KAFKA_BOOTSTRAP_SERVERS=${HOST_IP}:9092
    echo "⚠️  Using Kafka at ${KAFKA_BOOTSTRAP_SERVERS} instead"
fi
KAFKA_TOPIC_FACE_RECOGNITION=${KAFKA_TOPIC_FACE_RECOGNITION:-face-recognition-tasks}
KAFKA_TOPIC_RESULTS=${KAFKA_TOPIC_RESULTS:-face-recognition-results}

echo "📊 Configuration:"
echo "   - Spark Master: $SPARK_MASTER"
echo "   - Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo "   - Input Topic: $KAFKA_TOPIC_FACE_RECOGNITION"
echo "   - Output Topic: $KAFKA_TOPIC_RESULTS"
echo ""

# Kiểm tra kết nối Spark Master
echo "🔍 Checking Spark Master connection..."
if command -v nc &> /dev/null; then
    SPARK_HOST=$(echo $SPARK_MASTER | sed 's|spark://||' | cut -d: -f1)
    SPARK_PORT=$(echo $SPARK_MASTER | sed 's|spark://||' | cut -d: -f2)
    if nc -z -v -w5 $SPARK_HOST $SPARK_PORT 2>&1 | grep -q succeeded; then
        echo "✅ Spark Master is ready at $SPARK_MASTER"
    else
        echo "⚠️  Cannot connect to Spark Master at $SPARK_MASTER"
        echo "   Make sure Spark Master is running:"
        echo "   $SPARK_HOME/sbin/start-master.sh"
        echo "   Continuing anyway..."
    fi
fi

# Kiểm tra kết nối Kafka
echo "🔍 Checking Kafka connection..."
if command -v nc &> /dev/null; then
    KAFKA_HOST=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f1)
    KAFKA_PORT=$(echo $KAFKA_BOOTSTRAP_SERVERS | cut -d: -f2)
    if nc -z -v -w5 $KAFKA_HOST $KAFKA_PORT 2>&1 | grep -q succeeded; then
        echo "✅ Kafka is ready at $KAFKA_BOOTSTRAP_SERVERS"
    else
        echo "⚠️  Cannot connect to Kafka at $KAFKA_BOOTSTRAP_SERVERS"
        echo "   Make sure Kafka is running"
        echo "   Continuing anyway..."
    fi
fi

# Đảm bảo PYTHONPATH có app directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Export KAFKA_BOOTSTRAP_SERVERS để Spark script có thể dùng
export KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS

echo ""
echo "🎯 Submitting Spark job..."
echo "   Press Ctrl+C to stop"
echo ""
echo "📊 Using Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo ""

# Chạy spark-submit
# Lưu ý: Nếu spark-sql-kafka-0-10_2.13:4.0.0 không tồn tại, thử dùng version gần nhất (3.5.0 hoặc 3.6.0)
# Spark 4.0.0 có thể tương thích với package của version trước
# Set environment variables để tránh HDFS
# Sử dụng Hadoop config tối thiểu (local filesystem only)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/hadoop_conf" ]; then
    export HADOOP_CONF_DIR="$SCRIPT_DIR/hadoop_conf"
else
    export HADOOP_CONF_DIR=/dev/null
fi
export SPARK_LOCAL_IP=127.0.0.1

$SPARK_HOME/bin/spark-submit \
  --master "$SPARK_MASTER" \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0,org.apache.kafka:kafka-clients:3.6.0 \
  --conf "spark.sql.streaming.checkpointLocation=file:///tmp/spark-checkpoint-face-recognition" \
  --conf "spark.hadoop.fs.defaultFS=file:///" \
  --conf "spark.hadoop.fs.file.impl=org.apache.hadoop.fs.LocalFileSystem" \
  --conf "spark.hadoop.fs.hdfs.impl.disable.cache=true" \
  --conf "spark.sql.warehouse.dir=file:///tmp/spark-warehouse" \
  --conf "spark.executor.memory=2g" \
  --conf "spark.driver.memory=1g" \
  --conf "spark.executor.cores=2" \
  --conf "spark.sql.adaptive.enabled=true" \
  --conf "spark.sql.adaptive.coalescePartitions.enabled=true" \
  --conf "spark.hadoop.fs.AbstractFileSystem.hdfs.impl=org.apache.hadoop.fs.Hdfs" \
  --py-files "$(pwd)/app/face_recognition_service.py,$(pwd)/app/minio_service.py,$(pwd)/app/config.py,$(pwd)/app/database.py" \
  --files "$(pwd)/app/config.py,$(pwd)/app/database.py" \
  spark_kafka_stream.py \
  --conf "spark.executor.extraJavaOptions=-Djava.security.egd=file:/dev/./urandom" \
  --conf "spark.driver.extraJavaOptions=-Djava.security.egd=file:/dev/./urandom"

# Export KAFKA_BOOTSTRAP_SERVERS để Spark script có thể dùng
export KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS

echo ""
echo "✅ Spark job completed"

