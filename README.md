# Hệ Thống Nhận Diện Khách Hàng - Cửa Hàng Cà Phê

Hệ thống nhận diện khuôn mặt phân tán cho cửa hàng cà phê sử dụng Kafka Streaming, Apache Spark (cài trên máy host) và MinIO Object Storage. Hệ thống cho phép nhận diện khách hàng và tự động lấy thông tin đơn hàng gần nhất của họ để chuẩn bị sẵn.

## 🚀 Tính năng

- ✅ Nhận diện khuôn mặt khách hàng real-time qua camera
- ✅ Quản lý chi nhánh (tạo, xóa, xem danh sách)
- ✅ Quản lý khách hàng (danh sách, chỉnh sửa, xóa)
- ✅ Tự động đăng ký khách hàng mới khi không nhận diện được
- ✅ Quản lý đơn hàng của khách hàng
- ✅ Tự động lấy đơn hàng gần nhất khi nhận diện được khách
- ✅ Hiển thị combo món thường mua cho khách hàng
- ✅ Menu thanh toán tích hợp
- ✅ Kafka Streaming cho xử lý bất đồng bộ
- ✅ Apache Spark (trên máy host) cho xử lý phân tán trên nhiều máy
- ✅ MinIO Object Storage để lưu trữ dữ liệu (images, encodings, logs)
- ✅ Giao diện web đẹp và dễ sử dụng
- ✅ API hỗ trợ mobile app cho các chi nhánh
- ✅ Logs và tracking chi tiết

## 📋 Yêu cầu

### Máy Chủ Chính:
- Docker và Docker Compose
- Python 3.11+ (nếu chạy Spark Streaming local)
- Apache Spark (cài trên máy host, không dùng Docker)
- 8GB RAM trở lên (khuyến nghị)

### Máy Worker:
- Python 3.11+
- Apache Spark Worker
- Kết nối mạng đến máy chủ chính

## 🛠️ Cài đặt và Chạy

### 1. Clone và vào thư mục dự án

```bash
cd /home/haminhchien/Documents/distributed_system/project_final/face_idid
```

### 2. Tạo file .env

```bash
cp .env.example .env
```

Chỉnh sửa `.env` với IP của máy chủ:
```env
HOST_IP=192.168.1.34
MINIO_ENDPOINT=192.168.1.34:9000
KAFKA_BOOTSTRAP_SERVERS=192.168.1.34:9092
SPARK_MASTER=spark://192.168.1.34:7077
```

### 3. Chạy hệ thống với Docker Compose

```bash
docker compose up -d
```

Hệ thống sẽ khởi động các services:
- **Zookeeper**: Port 2181
- **Kafka**: Port 9092 (external), 9093 (internal)
- **Kafka UI**: Port 8081 (http://192.168.1.34:8081)
- **MinIO**: Port 9000 (API), 9001 (Console - http://192.168.1.34:9001)
- **PostgreSQL**: Port 5433 (mapped từ 5432)
- **PgAdmin**: Port 5050 (http://192.168.1.34:5050)
- **Web Application**: Port 8000 (http://192.168.1.34:8000)

### 4. Khởi động Spark Streaming (quan trọng)

Trên máy chủ chính hoặc worker, sử dụng script sau để submit job lên Spark Master:

```bash
# Script này sẽ tự động tải các dependencies và chạy job
./run_spark_submit.sh
```

## 📖 Hướng dẫn sử dụng

### Truy cập giao diện web

Mở trình duyệt và truy cập: **http://localhost:8000**

### Quy trình sử dụng:

1. **Tạo Chi Nhánh**
   - Vào tab "Quản Lý Chi Nhánh"
   - Nhập tên, địa chỉ và mô tả chi nhánh
   - Click "Tạo Chi Nhánh"

2. **Quản Lý Khách Hàng**
   - Vào tab "Danh Sách Khách Hàng"
   - Xem danh sách tất cả khách hàng
   - Click vào khách hàng để xem chi tiết
   - Click "Sửa" để chỉnh sửa thông tin
   - Click "Xóa" để xóa khách hàng

3. **Nhận Diện Khách Hàng (Camera)**
   - Vào tab "Camera" hoặc truy cập `/camera`
   - Chọn chi nhánh
   - Cho phép truy cập camera
   - Hệ thống sẽ tự động nhận diện
   - **Nếu nhận diện được**: Hiển thị menu thanh toán với combo món thường mua
   - **Nếu không nhận diện được**: Tự động tạo khách hàng mới và hiển thị menu thanh toán

4. **Xem Logs**
   - Vào tab "Logs"
   - Xem lịch sử nhận diện
   - Có thể lọc theo chi nhánh

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│  Máy Chủ Chính (HOST_IP từ .env, mặc định: 192.168.1.7) │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │    Kafka     │  │ Spark Master │  │
│  │   :5433      │  │   :9092      │  │   :7077      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web API     │  │  Zookeeper   │  │    MinIO      │  │
│  │  :8000       │  │   :2181      │  │   :9000       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                                 │
┌───────▼────────┐            ┌──────────▼────────┐
│  Worker1       │            │  Worker3          │
│                │            │                    │
│ Spark Worker   │            │ Spark Worker      │
│ Kafka→MinIO    │            │ Kafka→MinIO       │
│ Face Recog     │            │ Face Recog       │
└────────────────┘            └───────────────────┘
```

**Luồng dữ liệu:**
1. Camera gửi ảnh → Kafka Topic (`face-recognition-tasks`)
2. Spark Streaming Worker xử lý nhận diện khuôn mặt
3. Kết quả được lưu lên **MinIO** (`face-recognition-data/`)
4. Kết quả được gửi về Kafka Topic (`face-recognition-results`)

### Components:

1. **Web Backend (FastAPI)**
   - RESTful API
   - Quản lý chi nhánh, khách hàng và đơn hàng
   - Xử lý upload ảnh và lưu vào MinIO
   - Nhận diện khuôn mặt và trả về đơn hàng gần nhất
   - Gửi tasks vào Kafka

2. **Kafka**
   - Topic: `face-recognition-tasks` (input)
   - Topic: `face-recognition-results` (output)
   - Streaming data giữa các services

3. **Spark Streaming** (trên máy host)
   - Nhận tasks từ Kafka
   - Xử lý phân tán trên nhiều workers
   - Lưu kết quả vào MinIO
   - Gửi kết quả về Kafka

4. **MinIO Object Storage**
   - Lưu trữ images khách hàng
   - Lưu trữ face encodings (.pkl files)
   - Lưu trữ logs và streaming data
   - Thay thế Hadoop HDFS

5. **Face Recognition Service**
   - Sử dụng thư viện `face_recognition`
   - Tải và so sánh face encodings từ MinIO
   - Hỗ trợ nhận diện theo chi nhánh

6. **Database (PostgreSQL)**
   - Lưu trữ thông tin chi nhánh (Branch)
   - Lưu trữ thông tin khách hàng (Customer)
   - Lưu trữ đơn hàng (Order)
   - Lưu logs nhận diện (RecognitionLog)

## 🔧 Cấu hình

Các biến môi trường có thể cấu hình trong `.env`:

```env
# IP của máy chủ chính
HOST_IP=192.168.1.7

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=192.168.1.7:9092

# Spark Configuration (cài trên máy host)
SPARK_HOME=/opt/spark
SPARK_MASTER=spark://192.168.1.7:7077

# MinIO Configuration
MINIO_ENDPOINT=192.168.1.7:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=face-recognition-data
MINIO_USE_SSL=false

# Database Configuration
POSTGRES_PORT=5433
DATABASE_URL=postgresql://faceid:faceid123@192.168.1.7:5433/faceid
```

## 📁 Cấu trúc thư mục

```
face_idid/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database models
│   ├── face_recognition_service.py  # Face recognition logic
│   ├── kafka_producer.py    # Kafka producer
│   ├── result_processor.py  # Service xử lý kết quả & auto-registration
│   ├── spark_streaming.py   # Spark streaming logic
│   ├── minio_service.py     # MinIO client service
│   └── templates/
│       ├── index.html       # Main web UI
│       └── camera.html      # Camera recognition page
├── uploads/                 # Temp files (local)
├── known_faces/             # Temp encodings (local)
├── docker-compose.yml       # Docker services
├── Dockerfile              # Web app Docker image
├── requirements.txt        # Python dependencies
├── run_spark_submit.sh     # Script chạy Spark Streaming (Summit mode)
├── spark_kafka_stream.py   # Entry point cho Spark Job
└── README.md
```

## 📝 API Endpoints

### Chi Nhánh (Branches)
- `GET /` - Web interface
- `POST /api/branches/` - Tạo chi nhánh
- `GET /api/branches/` - Lấy danh sách chi nhánh
- `GET /api/branches/{branch_id}` - Lấy thông tin chi nhánh
- `DELETE /api/branches/{branch_id}` - Xóa chi nhánh

### Khách Hàng (Customers)
- `POST /api/customers/` - Đăng ký khách hàng mới
- `GET /api/customers/` - Lấy danh sách khách hàng
- `GET /api/customers/{customer_id}` - Lấy thông tin khách hàng
- `GET /api/customers/{customer_id}/details` - Lấy chi tiết khách hàng (stats, orders, branches)
- `PUT /api/customers/{customer_id}` - Cập nhật khách hàng
- `DELETE /api/customers/{customer_id}` - Xóa khách hàng

### Đơn Hàng (Orders)
- `POST /api/orders/` - Tạo đơn hàng mới
- `GET /api/customers/{customer_id}/orders` - Lấy danh sách đơn hàng của khách
- `GET /api/customers/{customer_id}/orders/latest` - Lấy đơn hàng gần nhất

### Nhận Diện (Recognition)
- `POST /api/recognize/` - Nhận diện khuôn mặt (trả về đơn hàng nếu nhận diện được)
- `POST /api/branches/{branch_id}/recognize` - API cho mobile app tại chi nhánh

### Logs
- `GET /api/logs/` - Lấy logs nhận diện (có thể lọc theo branch_id)

## 📱 Sử dụng với Mobile App

Mobile app tại các chi nhánh có thể sử dụng endpoint:

```
POST /api/branches/{branch_id}/recognize
```

**Request:**
- `image`: File ảnh (multipart/form-data)
- `use_spark`: boolean (tùy chọn)

**Response khi nhận diện được:**
```json
{
  "status": "recognized",
  "recognized": true,
  "customer": {
    "id": 1,
    "name": "Nguyễn Văn A",
    "phone": "0123456789",
    "email": "a@example.com"
  },
  "latest_order": {
    "id": 1,
    "branch_id": 1,
    "items": [{"name": "Cà phê đen", "quantity": 1, "price": 25000}],
    "total_amount": 25000,
    "status": "completed",
    "created_at": "2024-01-01T10:00:00"
  },
  "confidence": 0.95,
  "message": "Khách hàng Nguyễn Văn A đã được nhận diện..."
}
```

**Response khi không nhận diện được (tự động tạo khách mới):**
```json
{
  "status": "processing_new_customer",
  "recognized": true,
  "auto_registered": true,
  "customer": {
    "id": 3,
    "name": "Guest",
    "phone": null,
    "email": null
  },
  "message": "Khách hàng mới đã được tạo tự động..."
}
```

## 🐛 Troubleshooting

### Một số lỗi thường gặp:

- **Kafka không kết nối được**: Kiểm tra IP trong `.env` và đảm bảo Kafka đang chạy
- **MinIO không kết nối được**: Kiểm tra `MINIO_ENDPOINT` và đảm bảo MinIO đang chạy
- **Spark không xử lý tasks**: Kiểm tra Spark Master đang chạy và workers đã kết nối
- **Face recognition không hoạt động**: Đảm bảo ảnh có khuôn mặt rõ ràng và khách hàng đã được đăng ký

## 🔒 Lưu ý bảo mật

- Hệ thống này chỉ dùng cho mục đích demo/development
- Không sử dụng trong production mà không có bảo mật bổ sung
- Cân nhắc thêm authentication và authorization
- Mã hóa dữ liệu nhạy cảm
- Bảo vệ API endpoints với API keys hoặc JWT tokens
- Thay đổi mật khẩu mặc định của MinIO và PostgreSQL

## 📄 License

MIT License

## 👨‍💻 Tác giả

Hệ thống nhận diện khách hàng cho cửa hàng cà phê với Kafka Streaming, Spark và MinIO
