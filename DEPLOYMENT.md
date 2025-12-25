# 🚀 Hướng Dẫn Triển Khai Hệ Thống Phân Tán

Hệ thống nhận diện khuôn mặt cho quán cà phê với kiến trúc phân tán sử dụng Kafka, Spark (cài trên máy host) và MinIO Object Storage để lưu trữ dữ liệu.

## 📋 Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────┐
│  Máy Chủ Chính (HOST_IP từ .env, mặc định: 192.168.1.7) │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │    Kafka     │  │ Spark Master │  │
│  │   :5433      │  │   :9092      │  │   :7077      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web API     │  │  Zookeeper   │  │    MinIO     │  │
│  │  :8000       │  │   :2181      │  │   :9000      │  │
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

## 🖥️ Cấu Hình Máy Chủ Chính

> Ghi chú: 
> - **Docker**: Chạy PostgreSQL, Kafka, Zookeeper, Web API, MinIO
> - **Spark**: Cài đặt trên máy host (không dùng Docker)
> - **MinIO**: Chạy trong Docker để lưu trữ dữ liệu (images, encodings, logs)
> - Tất cả máy worker sẽ truy cập API / UI qua IP từ biến môi trường `HOST_IP` (mặc định: `192.168.1.7`)

### Bước 1: Clone và chuẩn bị

```bash
cd /home/haminhchien/Documents/distributed_system/project_final/face_idid
```

### Bước 2: Tạo file .env

```bash
cp .env.example .env
```

Chỉnh sửa `.env` nếu cần (quan trọng: set `HOST_IP`):
```env
# IP của máy chủ chính (thay đổi theo IP thực tế của máy bạn)
HOST_IP=192.168.1.7

# Kafka Configuration
KAFKA_ADVERTISED_HOST=192.168.1.7
KAFKA_BOOTSTRAP_SERVERS=192.168.1.7:9092

# Spark Configuration (cài trên máy host)
SPARK_HOME=/opt/spark
SPARK_MASTER=spark://192.168.1.7:7077

# MinIO Configuration (chạy trong Docker)
MINIO_ENDPOINT=192.168.1.7:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=face-recognition-data
MINIO_USE_SSL=false

# Database Configuration
POSTGRES_PORT=5433  # Cổng PostgreSQL được NAT ra ngoài là 5433
```

### Bước 3: Khởi động services

```bash
# Tạo thư mục cần thiết
mkdir -p uploads known_faces app/templates

# Khởi động Docker services
docker compose up -d

# Kiểm tra services
docker compose ps
```

### Bước 4: Khởi tạo database

Database sẽ tự động được tạo khi web service khởi động. Nếu cần khởi tạo thủ công:

```bash
docker exec -it faceid-web python -c "from app.database import init_db; init_db()"
```

### Bước 5: Cài đặt Spark trên máy host

> **Lưu ý**: Spark không chạy trong Docker, cần cài đặt trực tiếp trên máy host.

```bash
# Tải Spark (ví dụ Spark 3.5.0)
cd /opt
sudo wget https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz
sudo tar -xzf spark-3.5.0-bin-hadoop3.tgz
sudo mv spark-3.5.0-bin-hadoop3 spark
sudo chown -R $USER:$USER /opt/spark

# Thêm vào ~/.bashrc hoặc ~/.zshrc
export SPARK_HOME=/opt/spark
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin

# Cấu hình Spark Master
cd $SPARK_HOME/conf
cp spark-env.sh.template spark-env.sh
echo "export SPARK_MASTER_HOST=${HOST_IP:-192.168.1.7}" >> spark-env.sh
echo "export SPARK_MASTER_PORT=7077" >> spark-env.sh

# Khởi động Spark Master
$SPARK_HOME/sbin/start-master.sh

# Kiểm tra Spark Master Web UI
# http://${HOST_IP:-192.168.1.7}:8080
```

### Bước 6: Kiểm tra MinIO

MinIO đã được cài đặt và chạy trong Docker. Kiểm tra:

```bash
# Kiểm tra MinIO đang chạy
docker compose ps minio

# Truy cập MinIO Console
# http://localhost:9001
# Username: minioadmin
# Password: minioadmin123

# Kiểm tra bucket đã được tạo tự động
docker compose exec web python -c "
from app.minio_service import MinioService
service = MinioService()
print('MinIO connected:', service.client is not None)
"
```

### Bước 7: Kiểm tra services

Thay `${HOST_IP}` bằng IP thực tế từ file `.env` (mặc định: `192.168.1.7`):

- **Web API**: http://${HOST_IP}:8000
- **Trang Camera Cho Chi Nhánh**: http://${HOST_IP}:8000/camera
- **Kafka UI**: http://${HOST_IP}:8080
- **Spark Master Web UI**: http://${HOST_IP}:8080 (Spark)
- **MinIO Console**: http://${HOST_IP}:9001
- **PgAdmin**: http://${HOST_IP}:5050

## 🖥️ Cấu Hình Máy Worker

> Mỗi máy worker đại diện cho **một chi nhánh**.  
> Máy worker:
> - Chạy Spark Streaming (`spark_streaming.py`) để xử lý nhận diện phân tán (tùy chọn).
> - Nhận dữ liệu từ Kafka, xử lý nhận diện khuôn mặt, và **lưu kết quả lên MinIO**.
> - **Mở camera để nhận diện khách hàng** qua trình duyệt web.

### 📹 Mở Camera Trên Máy Worker

Để sử dụng camera nhận diện trên máy worker:

1. **Mở trình duyệt web** (Chrome, Firefox, Edge) trên máy worker
2. **Truy cập URL**: `http://${HOST_IP}:8000/camera`
   - Thay `${HOST_IP}` bằng IP của máy chủ chính (ví dụ: `192.168.1.7`)
   - Ví dụ: `http://192.168.1.7:8000/camera`
3. **Cho phép truy cập camera** khi trình duyệt yêu cầu
4. **Chọn chi nhánh** từ dropdown menu (phải chọn đúng chi nhánh của máy worker này)
5. **Click "Bắt Đầu"** để bắt đầu streaming và nhận diện

**Lưu ý quan trọng:**
- Camera chỉ hoạt động trên **HTTPS** hoặc **localhost**
- Nếu truy cập qua IP (ví dụ: `http://192.168.1.7:8000`), một số trình duyệt có thể chặn camera
- **Giải pháp**: 
  - Sử dụng `localhost` nếu máy worker và máy chủ là cùng một máy
  - Hoặc cấu hình HTTPS/SSL cho web server
  - Hoặc sử dụng ngrok để tạo HTTPS tunnel: `ngrok http 8000`

### Trên Worker1 (192.168.80.127, user: nindang)

#### Bước 1: Clone code

```bash
cd ~/Documents/distributed_system/project_final/face_idid
# Hoặc clone từ git repository
```

#### Bước 2: Cài đặt dependencies

```bash
# Tạo virtual environment (khuyến nghị)
python3 -m venv venv
source venv/bin/activate

# Cài đặt packages
pip install -r requirements.txt
```

#### Bước 3: Cài đặt Spark trên Worker

```bash
# Cài đặt Spark (tương tự như trên máy chủ chính)
# Xem hướng dẫn ở Bước 5 của máy chủ chính

# Cài đặt Python libraries cho MinIO
pip install minio
```

#### Bước 4: Cấu hình worker

```bash
# Sử dụng script tự động (script sẽ đọc IP từ .env.example hoặc prompt user)
chmod +x setup_worker.sh
./setup_worker.sh worker1 1 192.168.1.7  # worker1 với branch_id=1 và host_ip

# Hoặc tạo thủ công file .env
   cp .env.example .env
# Chỉnh sửa .env cho worker1, ví dụ:

# Host IP của máy chủ chính
HOST_IP=192.168.1.7

# Kafka Configuration
KAFKA_ADVERTISED_HOST=192.168.1.7
KAFKA_BOOTSTRAP_SERVERS=192.168.1.7:9092

# Spark Configuration
SPARK_HOME=/opt/spark
SPARK_MASTER=spark://192.168.1.7:7077

# MinIO Configuration
MINIO_ENDPOINT=192.168.1.7:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=face-recognition-data
MINIO_USE_SSL=false

# Database Configuration
DATABASE_URL=postgresql://faceid:faceid123@192.168.1.7:5433/faceid

# Chi nhánh mặc định cho worker1
DEFAULT_BRANCH_ID=1
```

#### Bước 5: Chạy Spark Streaming Worker (Tùy chọn)

> **Lưu ý**: Spark Streaming sẽ:
> - Nhận dữ liệu từ Kafka
> - Xử lý nhận diện khuôn mặt
> - **Lưu kết quả lên MinIO** (`face-recognition-data/recognition_results/`)
> - Gửi kết quả về Kafka topic results
> 
> **Nếu không dùng Spark Streaming**, bạn có thể bỏ qua bước này và chỉ sử dụng camera trực tiếp.

```bash
chmod +x start_spark_streaming.sh
./start_spark_streaming.sh

# Hoặc chạy trực tiếp
python -m app.spark_streaming
```

#### Bước 6: Mở Camera Để Nhận Diện

1. **Mở trình duyệt web** trên máy worker
2. **Truy cập**: `http://${HOST_IP}:8000/camera`
   - Ví dụ: `http://192.168.1.7:8000/camera`
3. **Cho phép truy cập camera** khi trình duyệt hỏi
4. **Chọn chi nhánh** từ dropdown (phải khớp với `DEFAULT_BRANCH_ID` trong `.env`)
5. **Click "Bắt Đầu"** để bắt đầu nhận diện

**Lưu ý về Camera:**
- Camera chỉ hoạt động trên HTTPS hoặc localhost
- Nếu truy cập qua IP, có thể cần cấu hình HTTPS hoặc dùng ngrok
- Xem thêm trong [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) phần "Lỗi Camera không hoạt động"

### Trên Worker3 (192.168.80.207, user: nindang)

Làm tương tự như Worker1, nhưng với branch_id khác:

```bash
./setup_worker.sh worker3 3 192.168.1.7  # worker3 với branch_id=3 và host_ip
./start_spark_streaming.sh

# Hoặc chỉnh .env thủ công tương tự worker1, nhưng:
# DEFAULT_BRANCH_ID=3
```

### 📹 Mở Camera Trên Máy Worker

Sau khi cấu hình xong, để sử dụng camera:

1. **Mở trình duyệt** trên máy worker
2. **Truy cập**: `http://${HOST_IP}:8000/camera`
3. **Chọn chi nhánh** từ dropdown
4. **Click "Bắt Đầu"** và cho phép truy cập camera
5. Camera sẽ tự động nhận diện khách hàng

**Xem hướng dẫn chi tiết trong file [WORKER_CAMERA_GUIDE.md](./WORKER_CAMERA_GUIDE.md)**

## 🔍 Kiểm Tra Kết Nối

### Kiểm tra từ máy worker

Thay `${HOST_IP}` bằng IP thực tế từ file `.env`:

```bash
# Kiểm tra Kafka
nc -zv ${HOST_IP} 9092

# Kiểm tra PostgreSQL
nc -zv ${HOST_IP} 5433

# Kiểm tra Spark Master
nc -zv ${HOST_IP} 7077

# Kiểm tra MinIO
nc -zv ${HOST_IP} 9000
```

### Kiểm tra từ máy chủ chính

```bash
# Kiểm tra worker đã kết nối Spark
curl http://${HOST_IP}:8080

# Kiểm tra Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Kiểm tra MinIO bucket
docker compose exec web python -c "
from app.minio_service import MinioService
service = MinioService()
files = service.list_files('recognition_results/')
print('Files in MinIO:', len(list(files)))
"
```

## 📝 Tạo Chi Nhánh và Gán Cho Worker

1. Truy cập Web UI: http://${HOST_IP}:8000
2. Tạo chi nhánh mới (ví dụ: "Chi nhánh 1", "Chi nhánh 3")
3. Lưu lại Branch ID
4. Cấu hình worker với branch_id tương ứng trong `.env`:
   ```env
   DEFAULT_BRANCH_ID=1  # Cho Worker1
   DEFAULT_BRANCH_ID=3  # Cho Worker3
   ```

## 🐛 Troubleshooting

### Worker không kết nối được Kafka

1. Kiểm tra firewall:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 9092
   ```

2. Kiểm tra Kafka đã listen trên 0.0.0.0:
   ```bash
   docker exec -it kafka netstat -tlnp | grep 9092
   ```

3. Kiểm tra KAFKA_ADVERTISED_LISTENERS trong docker-compose.yml

### Worker không kết nối được Database

1. Kiểm tra PostgreSQL đã cho phép remote connection:
   ```bash
   # Trên máy chủ chính
   sudo nano /etc/postgresql/15/main/pg_hba.conf
   # Thêm: host all all 192.168.80.0/24 md5
   
   sudo nano /etc/postgresql/15/main/postgresql.conf
   # Đảm bảo: listen_addresses = '*'
   
   sudo systemctl restart postgresql
   ```

2. Kiểm tra firewall:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 5433
   ```

### Worker không kết nối được Spark Master

1. Kiểm tra Spark Master đã chạy trên máy host:
   ```bash
   # Trên máy chủ chính
   $SPARK_HOME/sbin/start-master.sh
   netstat -tlnp | grep 7077
   ```

2. Kiểm tra Spark Master Web UI: http://${HOST_IP}:8080

3. Kiểm tra firewall:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 7077
   sudo ufw allow from 192.168.0.0/16 to any port 8080
   ```

### Worker không lưu được dữ liệu lên MinIO

1. Kiểm tra MinIO đã chạy:
   ```bash
   # Trên máy chủ chính
   docker compose ps minio
   docker compose logs minio
   ```

2. Kiểm tra kết nối từ worker:
   ```bash
   # Trên worker
   python -c "
   from minio import Minio
   client = Minio('192.168.1.7:9000', 
                  access_key='minioadmin', 
                  secret_key='minioadmin123',
                  secure=False)
   buckets = client.list_buckets()
   print('MinIO buckets:', [b.name for b in buckets])
   "
   ```

3. Kiểm tra firewall:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 9000
   sudo ufw allow from 192.168.0.0/16 to any port 9001
   ```

4. Kiểm tra Python libraries:
   ```bash
   pip install minio
   ```

5. Kiểm tra dữ liệu đã lưu:
   ```bash
   # Trên máy chủ chính
   docker compose exec web python -c "
   from app.minio_service import MinioService
   service = MinioService()
   files = list(service.list_files('recognition_results/'))
   print('Files in MinIO:', len(files))
   for f in files[:5]:
       print('  -', f)
   "
   ```

## 📊 Monitoring

### Xem logs

**Máy chủ chính:**
```bash
docker compose logs -f web
docker compose logs -f kafka
docker compose logs -f minio

# Spark Master logs
tail -f $SPARK_HOME/logs/spark-*-master-*.out
```

**Máy worker:**
```bash
# Logs của Spark Streaming worker
tail -f /path/to/logs/spark_streaming.log

# Spark Worker logs
tail -f $SPARK_HOME/logs/spark-*-worker-*.out
```

### Kiểm tra Spark Workers

Truy cập: http://${HOST_IP}:8080 (Spark Master Web UI)

### Kiểm tra Kafka

Truy cập: http://${HOST_IP}:8080 (Kafka UI)

### Kiểm tra MinIO

Truy cập: http://${HOST_IP}:9001 (MinIO Console)

Xem dữ liệu đã lưu:
```bash
# Sử dụng MinIO client (mc) hoặc Python
docker compose exec web python -c "
from app.minio_service import MinioService
service = MinioService()
files = list(service.list_files('recognition_results/'))
print('Total files:', len(files))
for f in files[:10]:
    print('  -', f)
"
```

## 🔒 Bảo Mật

1. **Thay đổi mật khẩu database mặc định**
2. **Thay đổi mật khẩu MinIO mặc định**
3. **Sử dụng firewall để giới hạn truy cập**
4. **Sử dụng VPN hoặc SSH tunnel cho production**
5. **Mã hóa dữ liệu nhạy cảm**
6. **Cấu hình MinIO với SSL/TLS cho production**

## 📞 Liên Hệ

Nếu gặp vấn đề, kiểm tra:
1. Logs của các services
2. Kết nối mạng giữa các máy
3. Firewall rules
4. Cấu hình trong file .env
5. Xem file [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) để biết thêm chi tiết
