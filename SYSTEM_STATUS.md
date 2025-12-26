# 📊 Trạng Thái Hệ Thống

## ✅ Các Thành Phần Đang Hoạt Động

### 1. Docker Services (7/7) ✅
- ✅ **PostgreSQL**: Port 5433 - Database chính
- ✅ **MinIO**: Port 9000 (API), 9001 (Console) - Object Storage
- ✅ **Kafka**: Port 9092 - Message Queue
- ✅ **Zookeeper**: Port 2181 - Kafka coordination
- ✅ **Kafka UI**: Port 8081 - Kafka management UI
- ✅ **pgAdmin**: Port 5050 - Database management
- ✅ **Web API**: Port 8000 - FastAPI application

### 2. Web API ✅
- **URL**: http://localhost:8000
- **Status**: ✅ Running
- **Branches**: 1 branch found
- **API Endpoints**: Accessible

### 3. Spark Master ✅
- **Port**: 7077
- **Web UI**: http://localhost:8080
- **Status**: ✅ Running

### 4. MinIO ✅
- **API**: http://localhost:9000
- **Console**: http://localhost:9001
- **Status**: ✅ Running and healthy

### 5. Kafka ✅
- **Port**: 9092
- **Connection Test**: ✅ Passed
- **Producer**: ✅ Initialized in Web service
- **Note**: Topics will be auto-created when first message is sent

## ⚠️ Lưu Ý

### Kafka Connection
- Web service có thể gặp timeout khi kết nối Kafka từ Docker network
- Kafka connection test từ host machine: ✅ Passed
- Nếu gặp lỗi, có thể cần restart web service:
  ```bash
  docker compose restart web
  ```

### Spark Workers
- Spark Master đang chạy nhưng cần workers để xử lý tasks
- Để chạy Spark Streaming:
  ```bash
  ./run_spark_submit.sh
  ```

## 🧪 Test Hệ Thống

### Test 1: Direct Processing (use_spark=false)
```bash
# Qua Web UI
1. Mở http://localhost:8000
2. Vào tab "Nhận Diện Khuôn Mặt"
3. Upload ảnh
4. KHÔNG check "Use Spark"
5. Click "Nhận Diện"
→ Kết quả trả về ngay lập tức
```

### Test 2: Spark Processing (use_spark=true)
```bash
# Bước 1: Khởi động Spark Streaming
./run_spark_submit.sh

# Bước 2: Gửi task qua Web UI
1. Mở http://localhost:8000
2. Upload ảnh
3. CHECK "Use Spark"
4. Click "Nhận Diện"
→ Task được gửi vào Kafka, Spark worker xử lý
```

### Test 3: API Test
```bash
# Test API trực tiếp
curl -X POST "http://localhost:8000/api/recognize/" \
  -F "image=@/path/to/image.jpg" \
  -F "use_spark=false"

# Hoặc với use_spark=true
curl -X POST "http://localhost:8000/api/recognize/" \
  -F "image=@/path/to/image.jpg" \
  -F "use_spark=true"
```

## 📈 Monitoring

### Xem Logs
```bash
# Web service logs
docker compose logs web --tail 50

# Kafka logs
docker compose logs kafka --tail 50

# All services
docker compose logs --tail 50
```

### Kiểm Tra Kafka Topics
```bash
# List topics (sau khi có messages)
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-tasks \
  --from-beginning \
  --max-messages 5
```

### Kiểm Tra MinIO
```bash
# List files in MinIO
docker compose exec web python -c "
from app.minio_service import minio_service
files = minio_service.list_files('recognition_results/')
print('Results:', len(list(files)))
"
```

## 🎯 Kết Luận

**Hệ thống đã sẵn sàng hoạt động!**

- ✅ Tất cả Docker services đang chạy
- ✅ Web API hoạt động bình thường
- ✅ Kafka có thể kết nối
- ✅ Spark Master đang chạy
- ✅ MinIO hoạt động

**Có thể bắt đầu test ngay:**
1. Mở http://localhost:8000
2. Upload ảnh để test face recognition
3. Chọn use_spark=false để test trực tiếp
4. Hoặc use_spark=true để test với Spark (cần chạy Spark worker trước)


