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
        echo "   Example: export SPARK_HOME=/home/haminhchien/Downloads/spark-4.0.0-bin-hadoop3"
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
HOST_IP=${HOST_IP:-192.168.1.34}
SPARK_MASTER=${SPARK_MASTER:-spark://${HOST_IP}:7077}
# SPARK_MASTER="local[*]"

# ... (Kafka config kept)

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
  --conf "spark.executorEnv.MINIO_ENDPOINT=$MINIO_ENDPOINT" \
  --conf "spark.executorEnv.MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY" \
  --conf "spark.executorEnv.MINIO_SECRET_KEY=$MINIO_SECRET_KEY" \
  --conf "spark.executorEnv.MINIO_BUCKET_NAME=$MINIO_BUCKET_NAME" \
  --conf "spark.executorEnv.DATABASE_URL=$DATABASE_URL" \
  --py-files "$(pwd)/app/face_recognition_service.py,$(pwd)/app/minio_service.py,$(pwd)/app/config.py,$(pwd)/app/database.py" \
  --files "$(pwd)/app/config.py,$(pwd)/app/database.py" \
  spark_kafka_stream.py \
  --conf "spark.executor.extraJavaOptions=-Djava.security.egd=file:/dev/./urandom" \
  --conf "spark.driver.extraJavaOptions=-Djava.security.egd=file:/dev/./urandom"

# Export KAFKA_BOOTSTRAP_SERVERS để Spark script có thể dùng
export KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS

echo ""
echo "✅ Spark job completed"

