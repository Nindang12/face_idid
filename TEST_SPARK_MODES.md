# Hướng Dẫn Test Cả 2 Chế Độ: use_spark=true và use_spark=false

## 🎯 Mục Đích

Đảm bảo hệ thống hoạt động đúng với cả 2 chế độ:
- **use_spark=false**: Xử lý trực tiếp trong FastAPI (low latency)
- **use_spark=true**: Gửi task vào Kafka để Spark xử lý phân tán (high throughput)

## 📋 Yêu Cầu

1. **Docker services đang chạy:**
   ```bash
   docker compose ps
   # Phải thấy: postgres, kafka, zookeeper, web, minio đang chạy
   ```

2. **Kafka đang hoạt động:**
   ```bash
   docker compose logs kafka | tail -20
   # Phải thấy Kafka đã start thành công
   ```

3. **Spark Streaming Worker (tùy chọn - chỉ cần khi test use_spark=true):**
   ```bash
   # Chạy Spark Streaming worker để xử lý tasks từ Kafka
   python -m app.spark_streaming
   ```

## 🧪 Test use_spark=false

### Bước 1: Test qua Web UI

1. Mở trình duyệt: `http://localhost:8000/`
2. Vào tab "Nhận Diện Khuôn Mặt"
3. Upload ảnh
4. **KHÔNG** check "Use Spark"
5. Click "Nhận Diện"
6. **Kết quả mong đợi:**
   - Nhận diện ngay lập tức (không có delay)
   - Trả về kết quả với status: "recognized" hoặc "auto_registered"
   - Không có message về Kafka/Spark

### Bước 2: Test qua API

```bash
# Test với use_spark=false
curl -X POST "http://localhost:8000/api/recognize/" \
  -F "image=@/path/to/image.jpg" \
  -F "use_spark=false"

# Kết quả mong đợi:
# {
#   "task_id": "...",
#   "status": "recognized" hoặc "auto_registered",
#   "recognized": true,
#   "customer": {...},
#   ...
# }
```

## 🧪 Test use_spark=true

### Bước 1: Khởi động Spark Streaming Worker

```bash
# Trong terminal mới
cd /home/haminhchien/Documents/distributed_system/project_final/face_idid
python -m app.spark_streaming
```

**Kết quả mong đợi:**
```
✅ Spark Streaming Consumer started. Listening to topic: face-recognition-tasks
✅ Kafka Producer for results initialized
✅ MinIO connection test successful!
```

### Bước 2: Test qua Web UI

1. Mở trình duyệt: `http://localhost:8000/`
2. Vào tab "Nhận Diện Khuôn Mặt"
3. Upload ảnh
4. **CHECK** "Use Spark"
5. Click "Nhận Diện"
6. **Kết quả mong đợi:**
   - Trả về ngay với status: "processing"
   - Message: "Task sent to Spark for processing via Kafka"
   - Spark worker sẽ xử lý và lưu kết quả lên MinIO

### Bước 3: Test qua API

```bash
# Test với use_spark=true
curl -X POST "http://localhost:8000/api/recognize/" \
  -F "image=@/path/to/image.jpg" \
  -F "use_spark=true"

# Kết quả mong đợi:
# {
#   "task_id": "...",
#   "status": "processing",
#   "message": "Task sent to Spark for processing via Kafka"
# }
```

### Bước 4: Kiểm tra Kafka Topics

```bash
# Kiểm tra messages trong Kafka topic
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-tasks \
  --from-beginning

# Kiểm tra results
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-results \
  --from-beginning
```

### Bước 5: Kiểm tra MinIO

```bash
# Kiểm tra kết quả đã được lưu lên MinIO
docker compose exec web python -c "
from app.minio_service import minio_service
files = minio_service.list_files('recognition_results/')
print('Files in MinIO:', list(files)[:5])
"
```

## 🔍 Kiểm Tra Logs

### Web Service Logs

```bash
docker compose logs web --tail 50
# Tìm:
# - "✅ KafkaProducer initialized" (khi Kafka available)
# - "❌ No Kafka brokers available" (khi Kafka không available)
# - "Kafka unavailable, processing task ... directly" (fallback)
```

### Spark Worker Logs

```bash
# Trong terminal chạy spark_streaming
# Tìm:
# - "[Spark Worker] Processing task ..."
# - "✅ Successfully saved task ... to MinIO"
# - "✅ Sent result for task ... to Kafka results topic"
```

## ⚠️ Xử Lý Lỗi

### Nếu Kafka không available

**Triệu chứng:**
- Log: "❌ No Kafka brokers available"
- `use_spark=true` sẽ fallback về xử lý trực tiếp

**Giải pháp:**
```bash
# Kiểm tra Kafka đang chạy
docker compose ps kafka

# Restart Kafka nếu cần
docker compose restart kafka

# Kiểm tra logs
docker compose logs kafka
```

### Nếu Spark Worker không nhận được messages

**Triệu chứng:**
- Spark worker không log "Processing task"
- Messages tích tụ trong Kafka topic

**Giải pháp:**
1. Kiểm tra Kafka connection:
   ```bash
   docker compose logs kafka | grep -i error
   ```

2. Kiểm tra consumer group:
   ```bash
   docker exec -it kafka kafka-consumer-groups \
     --bootstrap-server localhost:9092 \
     --list
   ```

3. Restart Spark worker

## ✅ Checklist

- [ ] `use_spark=false` hoạt động bình thường
- [ ] `use_spark=true` gửi task vào Kafka thành công
- [ ] Spark worker nhận và xử lý tasks
- [ ] Kết quả được lưu lên MinIO
- [ ] Kết quả được gửi về Kafka results topic
- [ ] Fallback hoạt động khi Kafka không available

