# ✅ Spark Streaming Đã Chạy Thành Công!

## 📊 Trạng Thái

Spark Structured Streaming đã khởi động và đang chờ messages từ Kafka.

## ⚠️ Giải Thích Warnings

Các warnings bạn thấy là **bình thường**:

1. **Offset warnings**: 
   - Spark checkpoint có offset cũ (1) nhưng topic hiện tại chỉ có offset 0
   - Điều này xảy ra khi topic được tạo lại hoặc checkpoint cũ không khớp
   - **Không ảnh hưởng** - Spark sẽ tiếp tục chạy và chỉ xử lý messages mới

2. **"Some data may have been missed"**:
   - Do offset mismatch ở trên
   - Với `failOnDataLoss=false`, Spark sẽ tiếp tục thay vì dừng
   - **Đúng như mong muốn** - không muốn Spark crash vì offset cũ

3. **"spark.sql.adaptive.enabled is not supported in streaming"**:
   - Adaptive execution không hỗ trợ streaming
   - Spark tự động disable và tiếp tục
   - **Không ảnh hưởng**

## 🧪 Test Hệ Thống

### Cách 1: Qua Web UI (Khuyến nghị)

1. **Mở trình duyệt**: http://localhost:8000
2. **Vào tab "Nhận Diện Khuôn Mặt"**
3. **Upload ảnh**
4. **CHECK "Use Spark"**
5. **Click "Nhận Diện"**
6. **Xem logs trong terminal Spark** để thấy:
   - `[Spark Worker] Processing task ...`
   - `✅ Successfully saved task ... to MinIO`
   - `✅ Sent result for task ... to Kafka results topic`

### Cách 2: Qua API

```bash
curl -X POST "http://localhost:8000/api/recognize/" \
  -F "image=@/path/to/image.jpg" \
  -F "use_spark=true"
```

### Cách 3: Gửi Test Message Trực Tiếp

```bash
python3 << 'EOF'
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

test_msg = {
    "task_id": "test-123",
    "image_path": "/tmp/test.jpg",
    "branch_id": 1,
    "timestamp": "2025-12-26T10:52:00"
}

producer.send('face-recognition-tasks', value=test_msg, key='test-123')
producer.flush()
print("✅ Message sent!")
producer.close()
EOF
```

## 📈 Monitor

### Xem Logs Spark
- Logs sẽ hiển thị trong terminal đang chạy Spark
- Tìm: `[Spark Worker] Processing task ...`

### Kiểm Tra Kafka Topics

```bash
# Xem messages trong input topic
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-tasks \
  --from-beginning

# Xem results trong output topic
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-results \
  --from-beginning
```

### Kiểm Tra MinIO

```bash
docker compose exec web python -c "
from app.minio_service import minio_service
files = minio_service.list_files('recognition_results/')
print('Results in MinIO:')
for f in list(files)[:10]:
    print(f'  - {f}')
"
```

### Spark Web UI

- **URL**: http://localhost:8080
- Xem applications đang chạy
- Xem streaming queries

## 🎯 Kết Luận

**Hệ thống đã sẵn sàng!**

- ✅ Spark Streaming đang chạy
- ✅ Đang chờ messages từ Kafka
- ✅ Sẵn sàng xử lý face recognition tasks

**Bước tiếp theo:** Gửi task từ web với `use_spark=true` và xem Spark xử lý!


