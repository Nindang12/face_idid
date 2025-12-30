# HƯỚNG DẪN CHẠY HỆ THỐNG NHẬN DIỆN KHUÔN MẶT PHÂN TÁN

Tài liệu này hướng dẫn chi tiết các bước để cài đặt và vận hành hệ thống.

## 1. Yêu cầu hệ thống

*   **Hệ điều hành**: Linux (Ubuntu 20.04+ khuyến nghị).
*   **Phần mềm**:
    *   Docker & Docker Compose (để chạy Kafka, MinIO, DB, Web).
    *   Apache Spark 3.x/4.x (để chạy module xử lý luồng phân tán).
    *   Python 3.11+ (cài trên máy chạy Spark worker).
*   **Mạng**: Cần biết địa chỉ IP LAN của máy chủ (ví dụ: `192.168.1.34`).

## 2. Cấu hình hệ thống

### Bước 1: Clone mã nguồn
Vào thư mục dự án:
```bash
cd /đường/dẫn/tới/face_idid
```

### Bước 2: Cấu hình biến môi trường
Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```

Mở file `.env` và chỉnh sửa các dòng sau cho đúng với IP máy bạn:
```ini
# Thay 192.168.1.34 bằng IP LAN máy bạn
HOST_IP=192.168.1.34

# Kafka & MinIO (Giữ nguyên port, chỉ thay IP)
KAFKA_ADVERTISED_HOST=192.168.1.34
KAFKA_BOOTSTRAP_SERVERS=192.168.1.34:9092
MINIO_ENDPOINT=192.168.1.34:9000
SPARK_MASTER=spark://192.168.1.34:7077
```

## 3. Khởi động hệ thống

### Bước 1: Chạy các dịch vụ nền (Docker)
Lệnh này sẽ bật Kafka, Zookeeper, MinIO, Postgres, Web App:
```bash
docker compose up -d
```
*Chờ khoảng 30s để các service khởi động hoàn toàn.*

### Bước 2: Chạy Spark Streaming Job
Mở một terminal mới tại thư mục dự án và chạy:
```bash
./run_spark_submit.sh
```
*Script này sẽ submit job lên Spark Master và bắt đầu lắng nghe Kafka.*

## 4. Kiểm tra và Sử dụng

### Truy cập Web App
*   Mở trình duyệt: `http://192.168.1.34:8000`
*   **Camera nhận diện**: `http://192.168.1.34:8000/camera`
    *   *Lưu ý*: Nếu dùng Chrome trên máy khác, bạn cần bật flag `#unsafely-treat-insecure-origin-as-secure` cho IP này để mở được Camera.
    *   Chọn "Chi nhánh" và bấm "Bắt đầu Camera".

### Quản trị
*   **Kafka UI**: `http://192.168.1.34:8081` (Xem message qua lại).
*   **MinIO Console**: `http://192.168.1.34:9001` (User/Pass: `minioadmin` / `minioadmin123`).
*   **PgAdmin**: `http://192.168.1.34:5050` (Email: `admin@faceid.com` / Pass: `admin123`).

## 5. Tắt hệ thống

Để tắt toàn bộ:
1.  Dừng script Spark (Ctrl+C).
2.  Tắt Docker:
    ```bash
    docker compose down
    ```

## 6. Gỡ lỗi (Troubleshooting)

*   **Lỗi Kafka không kết nối**: Kiểm tra lại `HOST_IP` trong `.env` và `docker-compose.yml` có khớp nhau không. Sau đó chạy `docker compose up -d` lại.
*   **Lỗi Spark không tìm thấy thư viện**: Script `./run_spark_submit.sh` đã tự động đóng gói code trong thư mục `app/`. Đảm bảo bạn không đổi cấu trúc thư mục.
*   **Web Camera không lên hình**: Kiểm tra quyền truy cập Camera trên trình duyệt và cấu hình HTTPS/Insecure Flag.

## 7. Chạy với nhiều máy (Distributed Mode)

Nếu bạn muốn dùng một máy khác để làm Worker xử lý nhận diện (giảm tải cho máy chính):

### Tại máy Worker (Máy phụ):
1.  **Cài đặt**: Python 3.11+ và Java (để chạy Spark).
2.  **Mã nguồn**: Copy thư mục `face_idid` từ máy chính sang máy phụ.
3.  **Cấu hình**:
    *   Mở file `.env` trên máy phụ.
    *   Sửa `HOST_IP` thành **IP CỦA MÁY CHÍNH** (Ví dụ: `192.168.1.34`).
    *   *Lý do*: Để Worker biết Kafka và MinIO nằm ở đâu.
4.  **Chạy**:
    ```bash
    ./run_spark_submit.sh
    ```
    Script này sẽ tự động kết nối tới Spark Master ở máy chính và nhận task xử lý.
