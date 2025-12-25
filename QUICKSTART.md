# 🚀 Hướng Dẫn Nhanh

## Bước 1: Khởi động hệ thống

```bash
cd /home/haminhchien/Documents/distributed_system/project_final/face_idid

# Tạo file .env từ .env.example
cp .env.example .env

# Chỉnh sửa HOST_IP trong .env nếu cần
# HOST_IP=192.168.1.7

# Khởi động Docker services
docker compose up -d
```

## Bước 2: Kiểm tra services

```bash
# Kiểm tra tất cả services đang chạy
docker compose ps

# Kiểm tra logs nếu có lỗi
docker compose logs web
```

## Bước 3: Khởi động Spark Streaming (tùy chọn)

Nếu muốn sử dụng Spark để xử lý phân tán:

```bash
# Sử dụng script có sẵn
./start_spark_streaming.sh

# Hoặc chạy trực tiếp
python -m app.spark_streaming
```

## Bước 4: Sử dụng

1. **Mở trình duyệt**: http://localhost:8000
2. **Tạo chi nhánh đầu tiên**:
   - Vào tab "Quản Lý Chi Nhánh"
   - Nhập tên, địa chỉ và mô tả
   - Click "Tạo Chi Nhánh"
3. **Sử dụng Camera để nhận diện**:
   - Vào tab "Camera" hoặc truy cập http://localhost:8000/camera
   - Chọn chi nhánh
   - Cho phép truy cập camera
   - Hệ thống sẽ tự động nhận diện hoặc tạo khách hàng mới

## Kiểm tra services

- **Web UI**: http://localhost:8000
- **Kafka UI**: http://localhost:8080
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)
- **PgAdmin**: http://localhost:5050 (admin@faceid.com/admin123)
- **Spark Master**: http://localhost:8080 (nếu Spark đang chạy)

## Dừng hệ thống

```bash
docker compose down
```

## Khởi động lại

```bash
docker compose restart
```

## Xem logs

```bash
# Tất cả services
docker compose logs -f

# Chỉ web service
docker compose logs -f web

# Chỉ MinIO
docker compose logs -f minio
```

## Troubleshooting

Nếu gặp lỗi, xem file [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) để biết cách xử lý.
