# 🚀 Hướng Dẫn Nhanh

## Bước 1: Khởi động hệ thống

```bash
./start.sh
```

Hoặc thủ công:
```bash
docker-compose up -d
```

## Bước 2: Khởi động Spark Streaming (tùy chọn)

Nếu muốn sử dụng Spark để xử lý:

```bash
# Trong Docker
docker exec -it faceid-web python -m app.spark_streaming

# Hoặc local
./run_spark_streaming.sh
```

## Bước 3: Sử dụng

1. Mở trình duyệt: http://localhost:8000
2. Tạo room đầu tiên
3. Đăng ký user với ảnh khuôn mặt
4. Test nhận diện hoặc join room

## Kiểm tra services

- Web: http://localhost:8000
- Kafka UI: http://localhost:8080
- Spark Master: http://localhost:8081

## Dừng hệ thống

```bash
docker-compose down
```

