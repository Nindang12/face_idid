# Hệ Thống Nhận Diện Khách Hàng - Cửa Hàng Cà Phê

Hệ thống nhận diện khuôn mặt phân tán cho cửa hàng cà phê sử dụng Kafka Streaming và Apache Spark. Hệ thống cho phép nhận diện khách hàng và tự động lấy thông tin đơn hàng gần nhất của họ để chuẩn bị sẵn.

## 🚀 Tính năng

- ✅ Nhận diện khuôn mặt khách hàng real-time
- ✅ Quản lý chi nhánh (tạo, xóa, xem danh sách)
- ✅ Đăng ký khách hàng mới với ảnh khuôn mặt
- ✅ Quản lý đơn hàng của khách hàng
- ✅ Tự động lấy đơn hàng gần nhất khi nhận diện được khách
- ✅ Gửi thông báo đến chi nhánh khi không nhận diện được
- ✅ Kafka Streaming cho xử lý bất đồng bộ
- ✅ Apache Spark cho xử lý phân tán trên nhiều máy
- ✅ Giao diện web đẹp và dễ sử dụng
- ✅ API hỗ trợ mobile app cho các chi nhánh
- ✅ Logs và tracking

## 📋 Yêu cầu

- Docker và Docker Compose
- Python 3.11+ (nếu chạy local)
- 8GB RAM trở lên (khuyến nghị)

## 🛠️ Cài đặt và Chạy

### 1. Clone và vào thư mục dự án

```bash
cd /home/nindang/Documents/distribute_system/faceid
```

### 2. Tạo các thư mục cần thiết

```bash
mkdir -p uploads known_faces app/templates
```

### 3. Chạy hệ thống với Docker Compose

```bash
docker-compose up -d
```

Hệ thống sẽ khởi động các services:
- **Zookeeper**: Port 2181
- **Kafka**: Port 9092
- **Kafka UI**: Port 8080 (http://localhost:8080)
- **Spark Master**: Port 8081 (http://localhost:8081)
- **Spark Worker**: Xử lý phân tán
- **Web Application**: Port 8000 (http://localhost:8000)

### 4. Khởi động Spark Streaming (nếu muốn dùng Spark)

Trong một terminal mới:

```bash
# Nếu chạy trong Docker
docker exec -it faceid-web python -m app.spark_streaming

# Hoặc nếu chạy local
python -m app.spark_streaming
```

## 📖 Hướng dẫn sử dụng

### Truy cập giao diện web

Mở trình duyệt và truy cập: **http://localhost:8000**

### Quy trình sử dụng:

1. **Tạo Chi Nhánh**
   - Vào tab "Quản Lý Chi Nhánh"
   - Nhập tên, địa chỉ và mô tả chi nhánh
   - Click "Tạo Chi Nhánh"

2. **Đăng Ký Khách Hàng**
   - Vào tab "Đăng Ký Khách Hàng"
   - Nhập tên, số điện thoại, email (tùy chọn)
   - Upload ảnh khuôn mặt rõ ràng
   - Click "Đăng Ký Khách Hàng"

3. **Tạo Đơn Hàng**
   - Vào tab "Quản Lý Đơn Hàng"
   - Chọn khách hàng và chi nhánh
   - Nhập danh sách món (JSON format)
   - Nhập tổng tiền
   - Click "Tạo Đơn Hàng"

4. **Nhận Diện Khách Hàng**
   - Vào tab "Nhận Diện Khách Hàng"
   - Chọn chi nhánh (tùy chọn)
   - Upload ảnh cần nhận diện
   - Tích "Sử dụng Spark Streaming" nếu muốn dùng Kafka + Spark
   - Click "Nhận Diện"
   - **Nếu nhận diện được**: Hệ thống sẽ hiển thị thông tin khách và đơn hàng gần nhất
   - **Nếu không nhận diện được**: Hệ thống sẽ thông báo và yêu cầu đăng ký khách mới

5. **Xem Logs**
   - Vào tab "Logs"
   - Xem lịch sử nhận diện
   - Có thể lọc theo chi nhánh

## 🏗️ Kiến trúc hệ thống

```
┌─────────────┐
│  Mobile App │  (Tại các chi nhánh)
│   (Client)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Web UI    │
│  (FastAPI)  │
└──────┬──────┘
       │
       ├───► Direct Processing (Face Recognition Service)
       │     ├─► Nếu nhận diện được: Trả về thông tin khách + đơn hàng gần nhất
       │     └─► Nếu không: Thông báo và yêu cầu đăng ký
       │
       └───► Kafka Producer ──► Kafka Topic ──► Spark Streaming
                                             │
                                             └───► Kafka Results Topic
```

### Components:

1. **Web Backend (FastAPI)**
   - RESTful API
   - Quản lý chi nhánh, khách hàng và đơn hàng
   - Xử lý upload ảnh
   - Nhận diện khuôn mặt và trả về đơn hàng gần nhất
   - Gửi tasks vào Kafka

2. **Kafka**
   - Topic: `face-recognition-tasks` (input)
   - Topic: `face-recognition-results` (output)
   - Streaming data giữa các services

3. **Spark Streaming**
   - Nhận tasks từ Kafka
   - Xử lý phân tán trên nhiều workers
   - Gửi kết quả về Kafka

4. **Face Recognition Service**
   - Sử dụng thư viện `face_recognition`
   - Lưu và so sánh face encodings
   - Hỗ trợ nhận diện theo chi nhánh

5. **Database**
   - Lưu trữ thông tin chi nhánh (Branch)
   - Lưu trữ thông tin khách hàng (Customer)
   - Lưu trữ đơn hàng (Order)
   - Lưu logs nhận diện (RecognitionLog)

## 🔧 Cấu hình

Các biến môi trường có thể cấu hình trong `.env`:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SPARK_MASTER=spark://localhost:7077
DATABASE_URL=sqlite:///./faceid.db
```

## 📁 Cấu trúc thư mục

```
faceid/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database models (Branch, Customer, Order)
│   ├── face_recognition_service.py  # Face recognition logic
│   ├── kafka_producer.py    # Kafka producer
│   ├── kafka_consumer.py    # Kafka consumer
│   ├── spark_streaming.py   # Spark streaming job
│   └── templates/
│       └── index.html       # Web UI
├── uploads/               # Uploaded images
├── known_faces/             # Face encodings
├── docker-compose.yml       # Docker services
├── Dockerfile              # Web app Docker image
├── requirements.txt        # Python dependencies
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

**Response khi không nhận diện được:**
```json
{
  "status": "not_recognized",
  "recognized": false,
  "confidence": 0.0,
  "message": "Không nhận diện được khách hàng. Vui lòng đăng ký khách hàng mới.",
  "branch_id": 1,
  "branch_name": "Chi nhánh 1"
}
```

## 🐛 Troubleshooting

### Kafka không kết nối được
- Kiểm tra Kafka đã chạy: `docker ps | grep kafka`
- Kiểm tra port 9092 có bị chiếm không
- Xem logs: `docker logs kafka`

### Spark không xử lý tasks
- Kiểm tra Spark Master: http://localhost:8081
- Kiểm tra Spark Worker đã kết nối
- Xem logs của spark-streaming

### Face recognition không hoạt động
- Đảm bảo ảnh có khuôn mặt rõ ràng
- Kiểm tra khách hàng đã được đăng ký chưa
- Xem logs trong terminal

### Database không tạo được tables
- Xóa file `faceid.db` cũ nếu có
- Khởi động lại ứng dụng để tạo database mới

## 🔒 Lưu ý bảo mật

- Hệ thống này chỉ dùng cho mục đích demo/development
- Không sử dụng trong production mà không có bảo mật bổ sung
- Cân nhắc thêm authentication và authorization
- Mã hóa dữ liệu nhạy cảm
- Bảo vệ API endpoints với API keys hoặc JWT tokens

## 📄 License

MIT License

## 👨‍💻 Tác giả

Hệ thống nhận diện khách hàng cho cửa hàng cà phê với Kafka Streaming và Spark
