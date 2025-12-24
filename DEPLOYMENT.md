# 🚀 Hướng Dẫn Triển Khai Hệ Thống Phân Tán

Hệ thống nhận diện khuôn mặt cho quán cà phê với kiến trúc phân tán sử dụng Kafka, Spark (cài trên máy host) và Hadoop HDFS để lưu trữ dữ liệu.

## 📋 Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────┐
│  Máy Chủ Chính (HOST_IP từ .env, mặc định: 192.168.1.7) │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │    Kafka     │  │ Spark Master │  │
│  │   :5433      │  │   :9092      │  │   :7077      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web API     │  │  Zookeeper   │  │ Hadoop HDFS  │  │
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
│ Kafka→HDFS     │            │ Kafka→HDFS       │
│ Face Recog     │            │ Face Recog       │
└────────────────┘            └───────────────────┘
```

**Luồng dữ liệu:**
1. Camera gửi ảnh → Kafka Topic (`face-recognition-tasks`)
2. Spark Streaming Worker xử lý nhận diện khuôn mặt
3. Kết quả được lưu lên **Hadoop HDFS** (`/face_recognition/data/`)
4. Kết quả được gửi về Kafka Topic (`face-recognition-results`)

## 🖥️ Cấu Hình Máy Chủ Chính

> Ghi chú: 
> - **Docker**: Chạy PostgreSQL, Kafka, Zookeeper, Web API
> - **Spark**: Cài đặt trên máy host (không dùng Docker)
> - **Hadoop**: Cài đặt trên máy host để lưu dữ liệu từ Kafka streaming
> - Tất cả máy worker sẽ truy cập API / UI qua IP từ biến môi trường `HOST_IP` (mặc định: `192.168.1.7`)

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

# Hadoop Configuration (cài trên máy host)
HADOOP_HOME=/opt/hadoop
HDFS_NAMENODE=hdfs://192.168.1.7:9000
HDFS_DATA_DIR=/face_recognition/data

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

### Bước 6: Cài đặt Hadoop trên máy host

> **Lưu ý**: Hadoop cần cài đặt để lưu dữ liệu từ Kafka streaming lên HDFS.

```bash
# Tải Hadoop (ví dụ Hadoop 3.3.6)
cd /opt
sudo wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
sudo tar -xzf hadoop-3.3.6.tar.gz
sudo mv hadoop-3.3.6 hadoop
sudo chown -R $USER:$USER /opt/hadoop

# Thêm vào ~/.bashrc hoặc ~/.zshrc
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin

# Cấu hình Hadoop (đơn giản cho single-node)
cd $HADOOP_HOME/etc/hadoop

# Lấy HOST_IP từ .env hoặc dùng mặc định
HOST_IP=${HOST_IP:-192.168.1.7}

# core-site.xml
cat > core-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://${HOST_IP}:9000</value>
    </property>
</configuration>
EOF

# hdfs-site.xml
cat > hdfs-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/opt/hadoop/data/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/opt/hadoop/data/datanode</value>
    </property>
</configuration>
EOF

# Format HDFS (chỉ chạy lần đầu)
mkdir -p /opt/hadoop/data/namenode /opt/hadoop/data/datanode
$HADOOP_HOME/bin/hdfs namenode -format

# Khởi động Hadoop
$HADOOP_HOME/sbin/start-dfs.sh

# Tạo thư mục trên HDFS cho dữ liệu face recognition
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /face_recognition/data/recognition_results
$HADOOP_HOME/bin/hdfs dfs -mkdir -p /face_recognition/data/errors

# Kiểm tra HDFS
$HADOOP_HOME/bin/hdfs dfs -ls /
```

### Bước 7: Kiểm tra services

Thay `${HOST_IP}` bằng IP thực tế từ file `.env` (mặc định: `192.168.1.7`):

- **Web API**: http://${HOST_IP}:8000
- **Trang Camera Cho Chi Nhánh**: http://${HOST_IP}:8000/camera
- **Kafka UI**: http://${HOST_IP}:8080
- **Spark Master Web UI**: http://${HOST_IP}:8080 (Spark)
- **Hadoop NameNode Web UI**: http://${HOST_IP}:9870

## 🖥️ Cấu Hình Máy Worker

> Mỗi máy worker đại diện cho **một chi nhánh**.  
> Máy worker:
> - Chạy Spark Streaming (`spark_streaming.py`) để xử lý nhận diện phân tán.
> - Nhận dữ liệu từ Kafka, xử lý nhận diện khuôn mặt, và **lưu kết quả lên Hadoop HDFS**.
> - Dùng **trình duyệt** để mở `http://${HOST_IP}:8000/camera` và chọn đúng chi nhánh.

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

#### Bước 3: Cài đặt Spark và Hadoop trên Worker

```bash
# Cài đặt Spark (tương tự như trên máy chủ chính)
# Xem hướng dẫn ở Bước 5 của máy chủ chính

# Cài đặt Hadoop (nếu cần, hoặc chỉ cần kết nối tới HDFS trên máy chủ chính)
# Xem hướng dẫn ở Bước 6 của máy chủ chính

# Cài đặt Python libraries cho Hadoop
pip install hdfs3 pyarrow
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

# Hadoop Configuration
HADOOP_HOME=/opt/hadoop  # Đường dẫn Hadoop trên worker (nếu có)
HDFS_NAMENODE=hdfs://192.168.1.7:9000
HDFS_DATA_DIR=/face_recognition/data

# Database Configuration
DATABASE_URL=postgresql://faceid:faceid123@192.168.1.7:5433/faceid

# Chi nhánh mặc định cho worker1
DEFAULT_BRANCH_ID=1

# Nếu dùng NFS (xem phần bên dưới)
UPLOAD_DIR=/mnt/faceid_uploads
KNOWN_FACES_DIR=/mnt/faceid_known_faces
```

#### Bước 5: Tạo thư mục shared storage (nếu dùng NFS hoặc mount)

```bash
# Nếu dùng NFS hoặc shared mount
# Mount thư mục từ máy chủ chính
sudo mount -t nfs 192.168.80.147:/path/to/shared/known_faces ./known_faces
sudo mount -t nfs 192.168.80.147:/path/to/shared/uploads ./uploads

# Hoặc sử dụng rsync để đồng bộ
rsync -avz 192.168.80.147:/path/to/known_faces/ ./known_faces/
```

#### Bước 6: Chạy Spark Streaming Worker

> **Lưu ý**: Spark Streaming sẽ:
> - Nhận dữ liệu từ Kafka
> - Xử lý nhận diện khuôn mặt
> - **Lưu kết quả lên Hadoop HDFS** (`/face_recognition/data/recognition_results/`)
> - Gửi kết quả về Kafka topic results

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

Thay `${HOST_IP}` bằng IP thực tế từ file `.env`:

```bash
# Kiểm tra Kafka
nc -zv ${HOST_IP} 9092

# Kiểm tra PostgreSQL
nc -zv ${HOST_IP} 5433

# Kiểm tra Spark Master
nc -zv ${HOST_IP} 7077

# Kiểm tra Hadoop HDFS
nc -zv ${HOST_IP} 9000
```

### Kiểm tra từ máy chủ chính

```bash
# Kiểm tra worker đã kết nối Spark
curl http://${HOST_IP}:8080

# Kiểm tra Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Kiểm tra Hadoop HDFS
$HADOOP_HOME/bin/hdfs dfsadmin -report

# Xem dữ liệu đã lưu trên HDFS
$HADOOP_HOME/bin/hdfs dfs -ls /face_recognition/data/recognition_results/
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

### Worker không lưu được dữ liệu lên Hadoop HDFS

1. Kiểm tra Hadoop HDFS đã chạy:
   ```bash
   # Trên máy chủ chính
   $HADOOP_HOME/sbin/start-dfs.sh
   $HADOOP_HOME/bin/hdfs dfsadmin -report
   ```

2. Kiểm tra kết nối từ worker:
   ```bash
   # Trên worker
   $HADOOP_HOME/bin/hdfs dfs -ls hdfs://${HOST_IP}:9000/
   ```

3. Kiểm tra firewall:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 9000
   sudo ufw allow from 192.168.0.0/16 to any port 9870
   ```

4. Kiểm tra Python libraries:
   ```bash
   pip install hdfs3 pyarrow
   ```

5. Kiểm tra dữ liệu đã lưu:
   ```bash
   # Trên máy chủ chính
   $HADOOP_HOME/bin/hdfs dfs -ls /face_recognition/data/recognition_results/
   $HADOOP_HOME/bin/hdfs dfs -cat /face_recognition/data/recognition_results/2024/12/18/result_*.json
   ```

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

# Spark Master logs
tail -f $SPARK_HOME/logs/spark-*-master-*.out

# Hadoop logs
tail -f $HADOOP_HOME/logs/hadoop-*-namenode-*.log
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

### Kiểm tra Hadoop HDFS

Truy cập: http://${HOST_IP}:9870 (Hadoop NameNode Web UI)

Xem dữ liệu đã lưu:
```bash
$HADOOP_HOME/bin/hdfs dfs -ls /face_recognition/data/recognition_results/
$HADOOP_HOME/bin/hdfs dfs -cat /face_recognition/data/recognition_results/2024/12/18/result_*.json
```

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

