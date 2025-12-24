import os

# Lấy HOST_IP từ biến môi trường, fallback về giá trị mặc định
HOST_IP = os.getenv("HOST_IP", "192.168.1.7")

class Settings:
    # Host IP Configuration
    HOST_IP: str = HOST_IP
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{HOST_IP}:9092")
    KAFKA_TOPIC_FACE_RECOGNITION: str = "face-recognition-tasks"
    KAFKA_TOPIC_RESULTS: str = "face-recognition-results"
    
    # Spark Configuration (Spark đã cài trên máy host, không dùng Docker)
    SPARK_MASTER: str = os.getenv("SPARK_MASTER", f"spark://{HOST_IP}:7077")
    SPARK_HOME: str = os.getenv("SPARK_HOME", "/opt/spark")  # Đường dẫn Spark trên máy host
    
    # Hadoop Configuration
    HADOOP_HOME: str = os.getenv("HADOOP_HOME", "/opt/hadoop")
    HDFS_NAMENODE: str = os.getenv("HDFS_NAMENODE", f"hdfs://{HOST_IP}:9000")
    HDFS_DATA_DIR: str = os.getenv("HDFS_DATA_DIR", "/face_recognition/data")  # Thư mục trên HDFS để lưu dữ liệu
    
    # Database Configuration
    # PostgreSQL cho môi trường phân tán
    # Nếu DATABASE_URL không được set, sẽ build từ HOST_IP
    _db_url = os.getenv("DATABASE_URL")
    if not _db_url:
        _db_user = os.getenv("POSTGRES_USER", "faceid")
        _db_pass = os.getenv("POSTGRES_PASSWORD", "faceid123")
        _db_name = os.getenv("POSTGRES_DB", "faceid")
        _db_port = os.getenv("POSTGRES_PORT", "5433")  # Port NAT từ Docker
        _db_url = f"postgresql://{_db_user}:{_db_pass}@{HOST_IP}:{_db_port}/{_db_name}"
    DATABASE_URL: str = _db_url
    
    # Storage Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    KNOWN_FACES_DIR: str = os.getenv("KNOWN_FACES_DIR", "known_faces")
    
    # Branch Configuration (cho các máy worker)
    # Mỗi máy có thể có một branch_id mặc định
    DEFAULT_BRANCH_ID: int = int(os.getenv("DEFAULT_BRANCH_ID", "0"))  # 0 = không có branch mặc định

settings = Settings()

