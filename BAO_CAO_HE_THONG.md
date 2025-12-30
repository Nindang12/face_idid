# BÁO CÁO KỸ THUẬT: HỆ THỐNG NHẬN DIỆN KHUÔN MẶT PHÂN TÁN

**Dự án:** Face IDID - Hệ thống nhận diện khách hàng thông minh
**Phiên bản:** 2.0 (Distributed Architecture)
**Ngày lập báo cáo:** 30/12/2025

---

## 1. Giới Thiệu Chung

### 1.1. Đặt Vấn Đề
Trong các chuỗi cửa hàng bán lẻ hoặc F&B quy mô lớn, việc nhận diện khách hàng thân thiết (VIP) ngay khi họ bước vào là yếu tố then chốt để nâng cao trải nghiệm. Tuy nhiên, các giải pháp truyền thống (monolith) thường gặp khó khăn khi:
*   Số lượng khách hàng lên tới hàng trăm nghìn (dữ liệu khuôn mặt quá lớn để load vào RAM một máy đơn lẻ).
*   Lượng camera từ nhiều chi nhánh gửi về đồng thời gây nghẽn cổ chai.

### 1.2. Giải Pháp
Hệ thống **Face IDID** được xây dựng dựa trên kiến trúc phân tán (Distributed System), sử dụng **Apache Spark** để xử lý song song và **Kafka** để điều phối luồng dữ liệu. Điều này cho phép hệ thống mở rộng không giới hạn bằng cách thêm các máy trạm (Worker) mà không cần thay đổi code lõi.

---

## 2. Ngăn Xếp Công Nghệ (Technology Stack)

| Thành Phần | Công Nghệ Sử Dụng | Vai Trò |
| :--- | :--- | :--- |
| **Backend API** | Python FastAPI | Xử lý yêu cầu HTTP, Async I/O |
| **Message Broker** | Apache Kafka 7.5 | Hàng đợi thông điệp, điều phối tasks |
| **Distributed Process** | Apache Spark 3.5+ | Xử lý ảnh phân tán, tính toán vector song song |
| **Storage** | MinIO (Object Storage) | Lưu trữ ảnh và file encoding (.pkl) |
| **Database** | PostgreSQL 15 | Lưu trữ thông tin khách hàng, log, đơn hàng |
| **Face Core** | Dlib / Face Recognition | Thuật toán trích xuất đặc trưng khuôn mặt (128-d vector) |
| **Frontend** | HTML5 / JS (Fetch API) | Giao diện Camera, Polling cơ chế |
| **Container** | Docker & Docker Compose | Đóng gói và triển khai dịch vụ |

---

## 3. Kiến Trúc Hệ Thống

### 3.1. Sơ đồ Luồng Dữ Liệu (Data Flow)

```mermaid
graph TD
    User[Khách Hàng] -->|Camera| Web[Web App / Camera UI]
    Web -->|0. Upload Ảnh| MinIO[MinIO Storage]
    Web -->|1. Event: Task Nhận Diện| KafkaIn[Kafka Topic: face-recognition-tasks]
    
    KafkaIn -->|2. Phân phối Load| Cluster[Spark Cluster (Master + Workers)]
    
    subgraph "Spark Worker Nodes"
        Cluster -->|3. Fetch Ảnh| MinIO
        Cluster -->|4. Tính Vector & Matching| Logic[Face Recognition Lib]
    end
    
    Cluster -->|5. Event: Kết Quả| KafkaOut[Kafka Topic: face-recognition-results]
    
    KafkaOut -->|6. Consume| Processor[Result Processor Service]
    
    subgraph "Backend Processing"
        Processor -->|7. Logic| AutoReg[Tự Động Đăng Ký Khách Mới]
        Processor -->|8. Logic| UpdateDB[Ghi Log & Update Customer]
    end
    
    Web -->|9. Long Polling| UpdateDB
    UpdateDB -->|10. Trả Kết Quả| User
```

### 3.2. Cơ Chế Hoạt Động Cụ Thể

1.  **Ingestion Layer (Web + Kafka Producer)**:
    *   Ảnh chụp từ camera không được gửi trực tiếp vào RAM của server xử lý. Thay vào đó, nó được upload lên **MinIO** (kho lưu trữ chung).
    *   Web Server chỉ gửi một "tấm vé" (message) chứa đường dẫn ảnh vào **Kafka**. Việc này giúp Web Server trả lời người dùng ngay lập tức mà không bị "treo".

2.  **Processing Layer (Spark Streaming)**:
    *   Các **Spark Worker** (có thể nằm trên nhiều máy vật lý khác nhau) liên tục lấy "vé" từ Kafka.
    *   Worker tải ảnh từ MinIO, dùng thư viện `face_recognition` để mã hóa khuôn mặt thành vector 128 chiều.
    *   Thuật toán so sánh: Tính khoảng cách Euclidean giữa vector mới và hàng nghìn vector trong Cache.
    *   **Ưu điểm**: Nếu hệ thống chậm, chỉ cần bật thêm máy tính Worker, Spark Master sẽ tự chia việc.

3.  **Storage Layer (MinIO + Postgres)**:
    *   **MinIO**: Đóng vai trò như HDFS (Hadoop File System), giúp chia sẻ file giữa các máy.
    *   **PostgreSQL**: Lưu trữ dữ liệu có cấu trúc (quan hệ Khách hàng - Đơn hàng).

---

## 4. Giải Thích Mã Nguồn Chi Tiết

### A. Phân Hệ Backend (`app/`)

*   **`main.py`**:
    *   Khởi tạo FastAPI app.
    *   Endpoint `/api/recognize`: Nhận ảnh -> Upload MinIO -> Gửi Kafka.
    *   Endpoint `/api/recognition-status/{task_id}`: API cho Frontend polling. Nó kiểm tra DB xem task đã có kết quả chưa.

*   **`face_recognition_service.py`**:
    *   Module quan trọng nhất chứa logic AI.
    *   `load_known_faces()`: Cơ chế **Smart Cache**. Thay vì tải lại toàn bộ database mỗi lần nhận diện, nó chỉ tải những file `.pkl` mới từ MinIO (delta update).
    *   `encode_face()`: Cài đặt thuật toán chọn khuôn mặt trung tâm (Center-Face Priority) để loại bỏ nhiễu nền.

*   **`result_processor.py`**:
    *   Service chạy nền (Daemon).
    *   Chịu trách nhiệm về tính toàn vẹn dữ liệu (Data Consistency).
    *   Logic **Double-Check**: Khi Spark báo "Lạ mặt", service này không tin ngay mà tải ảnh về kiểm tra lại lần cuối với cache mới nhất. Nếu thực sự lạ, nó mới tạo ID mới (Auto-Registration).
    *   **Transaction Management**: Đảm bảo log chỉ được ghi khi mọi bước xử lý thành công.

### B. Phân Hệ Phân Tán

*   **`spark_kafka_stream.py`**:
    *   Code chạy trên môi trường Spark.
    *   Sử dụng `Spark Structured Streaming` để đọc Kafka theo lô (micro-batch).
    *   Định nghĩa UDF (User Defined Function) để nhúng code Python nhận diện khuôn mặt vào luồng xử lý của Spark.

*   **`run_spark_submit.sh`**:
    *   Script Shell tự động hóa việc deploy.
    *   Nó đóng gói toàn bộ thư mục `app/` thành file ZIP ảo để gửi tới các worker, đảm bảo mọi worker đều có code mới nhất mà không cần copy thủ công.

---

## 5. Thiết Kế Cơ Sở Dữ Liệu (Database Schema)

### Bảng `customers`
Lưu thông tin khách hàng.
*   `id`: Primary Key.
*   `face_encoding_path`: Đường dẫn tới file vector trên MinIO.
*   `name`: Tên hiển thị (Mặc định là "Guest" với khách vãng lai).

### Bảng `recognition_logs`
Lưu lịch sử nhận diện (Dùng cho Polling và thống kê).
*   `image_path`: Đường dẫn ảnh chụp lúc vào cửa.
*   `customer_id`: FK tới bảng customers.
*   `confidence`: Độ tin cậy của thuật toán (0.0 - 1.0).
*   `branch_id`: Định danh chi nhánh.

---

## 6. Khả Năng Mở Rộng & Bảo Trì

*   **Thêm Camera**: Chỉ cần trỏ API về Server, không cần cấu hình thêm.
*   **Thêm Sức Mạnh Xử Lý**: Cài đặt Spark Worker lên máy tính mới, trỏ IP về Spark Master -> Hệ thống tự tăng tốc độ gấp đôi.
*   **Backup**: Dữ liệu ảnh nằm trên MinIO, dễ dàng backup sang Cloud (AWS S3) mà không cần tắt hệ thống.

---
*Tài liệu này dùng cho mục đích báo cáo đồ án và chuyển giao kỹ thuật.*
