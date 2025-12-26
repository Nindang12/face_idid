# Hướng Dẫn Setup và Chạy Spark Structured Streaming

## 🎯 Mục Đích

Sử dụng **Spark Structured Streaming** thật sự với `spark-submit` để xử lý face recognition phân tán qua Kafka.

## 📋 Yêu Cầu

### 1. Cài Đặt Spark 4.0.0

```bash
# Download Spark 4.0.0 (nếu chưa có)
wget https://archive.apache.org/dist/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz
tar -xzf spark-4.0.0-bin-hadoop3.tgz
sudo mv spark-4.0.0-bin-hadoop3 /opt/spark

# Set environment variables
export SPARK_HOME=/opt/spark
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
```

### 2. Khởi Động Spark Master

```bash
# Trên máy chủ chính
$SPARK_HOME/sbin/start-master.sh

# Kiểm tra Spark Master đang chạy
# Web UI: http://localhost:8080
# Hoặc: http://YOUR_IP:8080
```

### 3. Khởi Động Spark Workers (trên các máy worker)

```bash
# Trên mỗi máy worker
$SPARK_HOME/sbin/start-worker.sh spark://MASTER_IP:7077

# Ví dụ:
$SPARK_HOME/sbin/start-worker.sh spark://192.168.1.9:7077
```

### 4. Cài Đặt Dependencies trên Workers

**Quan trọng:** Mỗi Spark worker cần có:
- Python 3.10+
- `face-recognition` và các dependencies
- Code của app (app/ directory)

```bash
# Trên mỗi worker
cd /path/to/face_idid
pip install face-recognition opencv-python-headless numpy Pillow sqlalchemy psycopg2-binary minio kafka-python
```

## 🚀 Chạy Spark Streaming

### Cách 1: Dùng Script (Khuyến nghị)

```bash
./run_spark_submit.sh
```

### Cách 2: Chạy Trực Tiếp

```bash
export SPARK_HOME=/opt/spark
export SPARK_MASTER=spark://192.168.1.9:7077
export KAFKA_BOOTSTRAP_SERVERS=192.168.1.9:9092

$SPARK_HOME/bin/spark-submit \
  --master $SPARK_MASTER \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --conf "spark.sql.streaming.checkpointLocation=/tmp/spark-checkpoint-face-recognition" \
  --conf "spark.executor.memory=2g" \
  --conf "spark.driver.memory=1g" \
  spark_kafka_stream.py
```

## 📊 Kiểm Tra

### 1. Spark Master Web UI
- URL: `http://YOUR_IP:8080`
- Xem các workers đã kết nối
- Xem các applications đang chạy

### 2. Spark Application Logs
- Xem logs trong terminal chạy `spark-submit`
- Hoặc xem trong Spark Master Web UI → Applications → Logs

### 3. Kafka Topics
```bash
# Kiểm tra messages trong input topic
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-tasks \
  --from-beginning

# Kiểm tra results trong output topic
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-results \
  --from-beginning
```

### 4. MinIO Results
```bash
# Kiểm tra kết quả đã lưu
docker compose exec web python -c "
from app.minio_service import minio_service
files = minio_service.list_files('recognition_results/')
for f in list(files)[:5]:
    print(f)
"
```

## ⚙️ Cấu Hình

### Environment Variables

Tạo file `.env` hoặc export:

```bash
export SPARK_HOME=/opt/spark
export SPARK_MASTER=spark://192.168.1.9:7077
export KAFKA_BOOTSTRAP_SERVERS=192.168.1.9:9092
export KAFKA_TOPIC_FACE_RECOGNITION=face-recognition-tasks
export KAFKA_TOPIC_RESULTS=face-recognition-results
export HOST_IP=192.168.1.9
```

### Spark Configuration

Có thể thêm các config trong `run_spark_submit.sh`:

```bash
--conf "spark.executor.memory=4g" \
--conf "spark.executor.cores=4" \
--conf "spark.driver.memory=2g" \
--conf "spark.sql.shuffle.partitions=200" \
```

## 🔧 Troubleshooting

### 1. Workers không kết nối được Master

```bash
# Kiểm tra firewall
sudo ufw allow from 192.168.0.0/16 to any port 7077
sudo ufw allow from 192.168.0.0/16 to any port 8080

# Kiểm tra Spark Master đang listen
netstat -tlnp | grep 7077
```

### 2. Dependencies không tìm thấy trên Workers

**Giải pháp:** Copy code và cài dependencies trên mỗi worker:

```bash
# Trên mỗi worker
cd /path/to/face_idid
pip install -r requirements.txt
```

### 3. Kafka connection errors

```bash
# Kiểm tra Kafka đang chạy
docker compose ps kafka

# Kiểm tra Kafka có thể truy cập từ workers
telnet KAFKA_IP 9092
```

### 4. Face recognition không hoạt động trên Workers

Đảm bảo mỗi worker có:
- `face-recognition` package đã cài
- `dlib` dependencies
- Code `app/face_recognition_service.py` và `app/minio_service.py`

## 📈 Performance Tuning

### Tăng số lượng workers
- Thêm nhiều Spark workers để tăng throughput
- Mỗi worker sẽ xử lý một phần tasks

### Tăng resources
```bash
--conf "spark.executor.memory=4g" \
--conf "spark.executor.cores=4" \
--conf "spark.executor.instances=4"
```

### Kafka partitions
- Tăng số partitions của Kafka topic để parallel processing tốt hơn
- Mỗi partition có thể được xử lý bởi một executor

## ✅ So Sánh: Spark Structured Streaming vs Simple Kafka Consumer

| Tiêu Chí | Simple Consumer | Spark Structured Streaming |
|----------|----------------|---------------------------|
| **Phân tán** | ❌ Chạy trên 1 máy | ✅ Phân tán trên nhiều workers |
| **Scalability** | ❌ Hạn chế | ✅ Tự động scale |
| **Fault Tolerance** | ❌ Thấp | ✅ Cao (checkpointing) |
| **Throughput** | ❌ Thấp | ✅ Rất cao |
| **Complexity** | ✅ Đơn giản | ❌ Phức tạp hơn |
| **Setup** | ✅ Dễ | ❌ Cần Spark cluster |

