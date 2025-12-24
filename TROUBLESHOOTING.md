# 🔧 Hướng Dẫn Sửa Lỗi - Face Recognition System

Tài liệu này hướng dẫn cách xử lý các lỗi phổ biến trong hệ thống nhận diện khuôn mặt.

---

## 📋 Mục Lục

1. [Lỗi UI không cập nhật (Cache Browser)](#1-lỗi-ui-không-cập-nhật-cache-browser)
2. [Lỗi Container không chạy](#2-lỗi-container-không-chạy)
3. [Lỗi Database Connection](#3-lỗi-database-connection)
4. [Lỗi Kafka Connection](#4-lỗi-kafka-connection)
5. [Lỗi Camera không hoạt động](#5-lỗi-camera-không-hoạt-động)
6. [Lỗi Face Recognition không nhận diện](#6-lỗi-face-recognition-không-nhận-diện)
7. [Lỗi Port đã được sử dụng](#7-lỗi-port-đã-được-sử-dụng)
8. [Lỗi Module không tìm thấy](#8-lỗi-module-không-tìm-thấy)

---

## 1. Lỗi UI không cập nhật (Cache Browser)

### Triệu chứng:
- Thay đổi code nhưng giao diện web vẫn hiển thị phiên bản cũ
- Tab, form, hoặc nội dung không thay đổi sau khi sửa file HTML

### Nguyên nhân:
- Browser đang cache file HTML/CSS/JS cũ
- Container chưa được rebuild với file mới

### Cách sửa:

#### Bước 1: Rebuild Container
```bash
cd /home/haminhchien/Documents/distributed_system/project_final/face_idid
docker compose stop web
docker compose rm -f web
docker compose build --no-cache web
docker compose up -d web
```

#### Bước 2: Clear Browser Cache

**Chrome/Edge:**
1. Nhấn `Ctrl + Shift + Delete` (Windows/Linux) hoặc `Cmd + Shift + Delete` (Mac)
2. Chọn "Cached images and files"
3. Chọn "All time"
4. Nhấn "Clear data"

**Firefox:**
1. Nhấn `Ctrl + Shift + Delete` (Windows/Linux) hoặc `Cmd + Shift + Delete` (Mac)
2. Chọn "Cache"
3. Chọn "Everything"
4. Nhấn "Clear Now"

#### Bước 3: Hard Refresh
- **Windows/Linux:** `Ctrl + Shift + R` hoặc `Ctrl + F5`
- **Mac:** `Cmd + Shift + R`

#### Bước 4: Kiểm tra file trong container
```bash
docker compose exec web cat /code/app/templates/index.html | head -20
```

#### Bước 5: Truy cập với version parameter
```
http://localhost:8000/?v=12345
```

---

## 2. Lỗi Container không chạy

### Triệu chứng:
```bash
docker compose ps
# Container có status "Exited" hoặc "Restarting"
```

### Cách sửa:

#### Kiểm tra logs:
```bash
docker compose logs web
docker compose logs postgres
docker compose logs kafka
```

#### Restart tất cả services:
```bash
docker compose down
docker compose up -d
```

#### Rebuild và restart:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### Kiểm tra resource:
```bash
# Kiểm tra disk space
df -h

# Kiểm tra memory
free -h

# Kiểm tra Docker
docker system df
docker system prune -a  # Cẩn thận: Xóa tất cả images không dùng
```

---

## 3. Lỗi Database Connection

### Triệu chứng:
```
sqlalchemy.exc.OperationalError: could not connect to server
psycopg2.OperationalError: connection refused
```

### Cách sửa:

#### Bước 1: Kiểm tra PostgreSQL container
```bash
docker compose ps postgres
docker compose logs postgres
```

#### Bước 2: Kiểm tra port conflict
```bash
# Kiểm tra port 5433 (host) có bị chiếm không
sudo netstat -tulpn | grep 5433
# Hoặc
sudo lsof -i :5433
```

#### Bước 3: Kiểm tra .env file
```bash
cat .env | grep POSTGRES
# Đảm bảo có:
# POSTGRES_USER=faceid
# POSTGRES_PASSWORD=faceid123
# POSTGRES_DB=faceid
```

#### Bước 4: Restart PostgreSQL
```bash
docker compose restart postgres
# Đợi 10 giây
docker compose logs postgres | tail -20
```

#### Bước 5: Test connection
```bash
docker compose exec postgres psql -U faceid -d faceid -c "SELECT 1;"
```

#### Bước 6: Reset database (nếu cần)
```bash
docker compose down -v  # Xóa volumes
docker compose up -d postgres
# Đợi postgres khởi động xong
docker compose up -d web
```

---

## 4. Lỗi Kafka Connection

### Triệu chứng:
```
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
Connection refused to kafka:29092
```

### Cách sửa:

#### Bước 1: Kiểm tra Kafka và Zookeeper
```bash
docker compose ps kafka zookeeper
docker compose logs kafka | tail -50
docker compose logs zookeeper | tail -50
```

#### Bước 2: Kiểm tra network
```bash
docker network ls
docker network inspect face_idid_faceid-network
```

#### Bước 3: Restart Kafka
```bash
docker compose restart zookeeper
sleep 10
docker compose restart kafka
sleep 10
docker compose logs kafka | tail -30
```

#### Bước 4: Kiểm tra KAFKA_ADVERTISED_LISTENERS trong .env
```bash
cat .env | grep KAFKA
# Đảm bảo có:
# KAFKA_ADVERTISED_HOST=192.168.80.147 (hoặc IP của máy chủ)
```

#### Bước 5: Test Kafka connection từ container
```bash
docker compose exec web python -c "
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['kafka:29092'])
print('Kafka connection OK')
"
```

#### Bước 6: Recreate Kafka (nếu cần)
```bash
docker compose stop kafka zookeeper
docker compose rm -f kafka zookeeper
docker compose up -d zookeeper
sleep 15
docker compose up -d kafka
sleep 15
docker compose up -d web
```

---

## 5. Lỗi Camera không hoạt động

### Triệu chứng:
- Trang `/camera` không hiển thị video
- Lỗi: "Cannot read properties of undefined (reading 'getUserMedia')"
- Camera không được phép truy cập

### Cách sửa:

#### Bước 1: Kiểm tra Browser Support
- Chỉ hoạt động trên **HTTPS** hoặc **localhost**
- Không hoạt động trên HTTP với IP (ví dụ: `http://192.168.80.147:8000`)

#### Bước 2: Truy cập qua localhost
```
http://localhost:8000/camera
```

#### Bước 3: Cấp quyền Camera
- Browser sẽ hỏi quyền truy cập camera
- Chọn "Allow" hoặc "Cho phép"

#### Bước 4: Kiểm tra Camera đang được sử dụng
```bash
# Linux
lsof | grep video
# Hoặc
ls -la /dev/video*
```

#### Bước 5: Test với HTTPS (nếu cần)
- Cài đặt SSL certificate
- Hoặc sử dụng ngrok để tạo HTTPS tunnel:
```bash
ngrok http 8000
# Sau đó truy cập URL HTTPS từ ngrok
```

---

## 6. Lỗi Face Recognition không nhận diện

### Triệu chứng:
- Không nhận diện được khách hàng đã đăng ký
- Confidence score luôn thấp
- Lỗi khi load face encoding

### Cách sửa:

#### Bước 1: Kiểm tra face encodings
```bash
ls -la app/known_faces/
ls -la known_faces/
# Đảm bảo có file .pkl cho mỗi khách hàng
```

#### Bước 2: Kiểm tra image path trong database
```bash
docker compose exec postgres psql -U faceid -d faceid -c "
SELECT id, name, face_encoding_path FROM customers LIMIT 10;
"
```

#### Bước 3: Kiểm tra file images
```bash
ls -la app/uploads/
# Đảm bảo file ảnh tồn tại
```

#### Bước 4: Re-register customer (nếu cần)
- Xóa customer cũ
- Đăng ký lại với ảnh rõ nét, ánh sáng tốt
- Đảm bảo chỉ có 1 khuôn mặt trong ảnh

#### Bước 5: Kiểm tra logs
```bash
docker compose logs web | grep -i "face\|recognition\|encoding"
```

#### Bước 6: Test face recognition service
```bash
docker compose exec web python -c "
from app.face_recognition_service import FaceRecognitionService
service = FaceRecognitionService()
print('Service loaded:', len(service.known_encodings), 'encodings')
"
```

---

## 7. Lỗi Port đã được sử dụng

### Triệu chứng:
```
Bind for 0.0.0.0:8000 failed: port is already allocated
Bind for 0.0.0.0:5432 failed: port is already allocated
```

### Cách sửa:

#### Bước 1: Tìm process đang dùng port
```bash
# Port 8000
sudo lsof -i :8000
# Hoặc
sudo netstat -tulpn | grep 8000

# Port 5432 (PostgreSQL)
sudo lsof -i :5432
```

#### Bước 2: Kill process (nếu cần)
```bash
# Tìm PID từ bước 1
sudo kill -9 <PID>
```

#### Bước 3: Hoặc đổi port trong docker-compose.yml
```yaml
# Thay đổi từ:
ports:
  - "8000:8000"
# Thành:
ports:
  - "8001:8000"  # Sử dụng port 8001 trên host
```

#### Bước 4: Restart container
```bash
docker compose down
docker compose up -d
```

---

## 8. Lỗi Module không tìm thấy

### Triệu chứng:
```
ModuleNotFoundError: No module named 'app'
ImportError: cannot import name 'xxx' from 'app'
```

### Cách sửa:

#### Bước 1: Kiểm tra Dockerfile
```bash
cat Dockerfile
# Đảm bảo có:
# WORKDIR /code
# COPY app/ /code/app
```

#### Bước 2: Kiểm tra file trong container
```bash
docker compose exec web ls -la /code/app/
docker compose exec web python -c "import sys; print(sys.path)"
```

#### Bước 3: Rebuild container
```bash
docker compose stop web
docker compose rm -f web
docker compose build --no-cache web
docker compose up -d web
```

#### Bước 4: Kiểm tra Python path trong container
```bash
docker compose exec web python -c "
import sys
sys.path.insert(0, '/code')
from app import main
print('Import OK')
"
```

---

## 🔍 Các Lệnh Debug Hữu Ích

### Kiểm tra trạng thái hệ thống:
```bash
# Xem tất cả containers
docker compose ps

# Xem logs real-time
docker compose logs -f web

# Xem resource usage
docker stats

# Xem network
docker network inspect face_idid_faceid-network
```

### Kiểm tra database:
```bash
# Connect vào PostgreSQL
docker compose exec postgres psql -U faceid -d faceid

# Xem tables
\dt

# Xem customers
SELECT * FROM customers LIMIT 10;

# Xem orders
SELECT * FROM orders LIMIT 10;

# Xem logs
SELECT * FROM recognition_logs ORDER BY created_at DESC LIMIT 10;
```

### Kiểm tra Kafka:
```bash
# List topics
docker compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Xem messages trong topic
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic face-recognition-tasks \
  --from-beginning
```

### Clean up:
```bash
# Xóa containers và volumes
docker compose down -v

# Xóa images không dùng
docker system prune -a

# Xóa tất cả (cẩn thận!)
docker system prune -a --volumes
```

---

## 📞 Liên Hệ & Hỗ Trợ

Nếu vẫn gặp lỗi sau khi thử các cách trên:

1. Kiểm tra logs chi tiết:
   ```bash
   docker compose logs > all_logs.txt
   ```

2. Kiểm tra system requirements:
   - Docker version: `docker --version`
   - Docker Compose version: `docker compose version`
   - Disk space: `df -h`
   - Memory: `free -h`

3. Tạo issue với thông tin:
   - OS version
   - Docker version
   - Error logs
   - Steps to reproduce

---

## ✅ Checklist Khi Gặp Lỗi

- [ ] Đã kiểm tra logs của container bị lỗi
- [ ] Đã kiểm tra port conflicts
- [ ] Đã kiểm tra .env file
- [ ] Đã thử restart container
- [ ] Đã thử rebuild container
- [ ] Đã clear browser cache
- [ ] Đã kiểm tra network connectivity
- [ ] Đã kiểm tra disk space và memory

---

**Lưu ý:** Luôn backup dữ liệu trước khi chạy các lệnh có thể xóa dữ liệu (như `docker compose down -v`).

