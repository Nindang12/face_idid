# 🚀 Hướng Dẫn Triển Khai Hệ Thống Phân Tán

Hệ thống nhận diện khuôn mặt cho quán cà phê với kiến trúc phân tán sử dụng Kafka và Spark.

## 📋 Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────┐
│  Máy Chủ Chính (192.168.80.147)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │    Kafka     │  │ Spark Master │  │
│  │   :5432      │  │   :9092      │  │   :7077      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Web API     │  │  Zookeeper   │                     │
│  │  :8000       │  │   :2181      │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                                 │
┌───────▼────────┐            ┌──────────▼────────┐
│  Worker1       │            │  Worker3          │
│ 192.168.80.127 │            │ 192.168.80.207    │
│                │            │                    │
│ Spark Worker   │            │ Spark Worker      │
│ Face Recog     │            │ Face Recog        │
└────────────────┘            └───────────────────┘
```

## 🖥️ Cấu Hình Máy Chủ Chính (192.168.80.147)

> Ghi chú: Ở máy chủ chính bạn chỉ cần chạy hệ thống bằng **Docker**.  
> Tất cả máy worker sẽ truy cập API / UI qua IP `192.168.80.147`.

Một số lệnh hữu ích (tham khảo, không bắt buộc chạy hết một lượt):

```bash
# Dừng và xóa container web (nếu cần rebuild sạch)
docker compose stop web
docker compose rm -f web

# Build lại image web
docker compose build --no-cache web

# Khởi động lại riêng service web
docker compose restart web

# Khởi động toàn bộ stack (web + postgres + kafka + spark, ...)
docker compose up -d --build

# Xem log của web
docker compose logs --tail=50 web
```

### Bước 1: Clone và chuẩn bị

```bash
cd /home/haminhchien/Documents/distributed_system/project_final/face_idid
```

### Bước 2: Tạo file .env

```bash
cp .env.example .env
```

Chỉnh sửa `.env` nếu cần:
```env
KAFKA_ADVERTISED_HOST=192.168.80.147
SPARK_MASTER_HOST=192.168.80.147
# Cổng PostgreSQL được NAT ra ngoài là 5433 (tránh trùng với PostgreSQL trên host)
POSTGRES_PORT=5433
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

### Bước 5: Kiểm tra services

- **Web API**: http://192.168.80.147:8000
- **Trang Camera Cho Chi Nhánh**: http://192.168.80.147:8000/camera
- **Kafka UI**: http://192.168.80.147:8080
- **Spark Master**: http://192.168.80.147:8081

## 🖥️ Cấu Hình Máy Worker (192.168.80.127 và 192.168.80.207)

> Mỗi máy worker đại diện cho **một chi nhánh**.  
> Máy worker:
> - Chạy Spark Streaming (`spark_streaming.py`) để xử lý nhận diện phân tán.
> - Dùng **trình duyệt** để mở `http://192.168.80.147:8000/camera` và chọn đúng chi nhánh.

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

#### Bước 3: Cấu hình worker

```bash
# Sử dụng script tự động
chmod +x setup_worker.sh
./setup_worker.sh worker1 1  # worker1 với branch_id=1

# Hoặc tạo thủ công file .env
cp .env.example .env
# Chỉnh sửa .env cho worker1, ví dụ:

# Kết nối tới Kafka trên máy chủ chính
KAFKA_BOOTSTRAP_SERVERS=192.168.80.147:9092

# Kết nối tới Spark Master trên máy chủ chính
SPARK_MASTER=spark://192.168.80.147:7077

# Kết nối tới PostgreSQL trong container trên máy chủ chính (NAT cổng 5433)
DATABASE_URL=postgresql://faceid:faceid123@192.168.80.147:5433/faceid

# Chi nhánh mặc định cho worker1
DEFAULT_BRANCH_ID=1

# Nếu dùng NFS (xem phần bên dưới)
UPLOAD_DIR=/mnt/faceid_uploads
KNOWN_FACES_DIR=/mnt/faceid_known_faces
```

#### Bước 4: Tạo thư mục shared storage (nếu dùng NFS hoặc mount)

```bash
# Nếu dùng NFS hoặc shared mount
# Mount thư mục từ máy chủ chính
sudo mount -t nfs 192.168.80.147:/path/to/shared/known_faces ./known_faces
sudo mount -t nfs 192.168.80.147:/path/to/shared/uploads ./uploads

# Hoặc sử dụng rsync để đồng bộ
rsync -avz 192.168.80.147:/path/to/known_faces/ ./known_faces/
```

#### Bước 5: Chạy Spark Streaming Worker

```bash
chmod +x run_worker.sh
./run_worker.sh 1  # branch_id=1

# Hoặc chạy trực tiếp
python -m app.spark_streaming
```

### Trên Worker3 (192.168.80.207, user: nindang)

Làm tương tự như Worker1, nhưng với branch_id khác:

```bash
./setup_worker.sh worker3 3  # worker3 với branch_id=3
./run_worker.sh 3

# Hoặc chỉnh .env thủ công tương tự worker1, nhưng:
# DEFAULT_BRANCH_ID=3
```

## 🔧 Cấu Hình Shared Storage

### Option 1: NFS (Khuyến nghị cho production)

**Trên máy chủ chính:**

```bash
# Cài đặt NFS server
sudo apt-get install nfs-kernel-server

# Cấu hình exports
sudo nano /etc/exports
# Thêm dòng:
/home/haminhchien/Documents/distributed_system/project_final/face_idid/known_faces 192.168.80.0/24(rw,sync,no_subtree_check)
/home/haminhchien/Documents/distributed_system/project_final/face_idid/uploads 192.168.80.0/24(rw,sync,no_subtree_check)

# Khởi động lại NFS
sudo systemctl restart nfs-kernel-server
```

**Trên các máy worker:**

```bash
# Cài đặt NFS client
sudo apt-get install nfs-common

# Mount thư mục
sudo mkdir -p /mnt/faceid_known_faces /mnt/faceid_uploads
sudo mount -t nfs 192.168.80.147:/home/haminhchien/Documents/distributed_system/project_final/face_idid/known_faces /mnt/faceid_known_faces
sudo mount -t nfs 192.168.80.147:/home/haminhchien/Documents/distributed_system/project_final/face_idid/uploads /mnt/faceid_uploads

# Cập nhật .env
KNOWN_FACES_DIR=/mnt/faceid_known_faces
UPLOAD_DIR=/mnt/faceid_uploads
```

### Option 2: Rsync (Đơn giản hơn, nhưng không real-time)

Tạo script đồng bộ định kỳ:

```bash
# sync_faces.sh
#!/bin/bash
rsync -avz --delete 192.168.80.147:/path/to/known_faces/ ./known_faces/
```

Chạy định kỳ với cron:

```bash
# Cập nhật mỗi 5 phút
*/5 * * * * /path/to/sync_faces.sh
```

### Option 3: Database chỉ lưu metadata, images lưu trên shared storage

Các worker có thể truy cập trực tiếp database để lấy metadata, nhưng cần shared storage cho images.

## 🔍 Kiểm Tra Kết Nối

### Kiểm tra từ máy worker

```bash
# Kiểm tra Kafka
nc -zv 192.168.80.147 9092

# Kiểm tra PostgreSQL
nc -zv 192.168.80.147 5432

# Kiểm tra Spark Master
nc -zv 192.168.80.147 7077
```

### Kiểm tra từ máy chủ chính

```bash
# Kiểm tra worker đã kết nối Spark
curl http://192.168.80.147:8081

# Kiểm tra Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

## 📝 Tạo Chi Nhánh và Gán Cho Worker

1. Truy cập Web UI: http://192.168.80.147:8000
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
   sudo ufw allow from 192.168.80.0/24 to any port 9092
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
   sudo ufw allow from 192.168.80.0/24 to any port 5432
   ```

### Worker không kết nối được Spark Master

1. Kiểm tra Spark Master đã listen trên đúng interface:
   ```bash
   docker exec -it spark-master netstat -tlnp | grep 7077
   ```

2. Kiểm tra SPARK_MASTER_HOST trong docker-compose.yml

### Face encodings không đồng bộ

1. Đảm bảo shared storage đã được mount đúng
2. Kiểm tra quyền truy cập thư mục
3. Sử dụng rsync để đồng bộ thủ công nếu cần

## 📊 Monitoring

### Xem logs

**Máy chủ chính:**
```bash
docker-compose logs -f web
docker-compose logs -f kafka
docker-compose logs -f spark-master
```

**Máy worker:**
```bash
# Logs của Spark Streaming worker
tail -f /path/to/logs/spark_streaming.log
```

### Kiểm tra Spark Workers

Truy cập: http://192.168.80.147:8081

### Kiểm tra Kafka

Truy cập: http://192.168.80.147:8080

## 🔒 Bảo Mật

1. **Thay đổi mật khẩu database mặc định**
2. **Sử dụng firewall để giới hạn truy cập**
3. **Sử dụng VPN hoặc SSH tunnel cho production**
4. **Mã hóa dữ liệu nhạy cảm**

## 📞 Liên Hệ

Nếu gặp vấn đề, kiểm tra:
1. Logs của các services
2. Kết nối mạng giữa các máy
3. Firewall rules
4. Cấu hình trong file .env

