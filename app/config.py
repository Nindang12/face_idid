import os

class Settings:
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.147:9092")
    KAFKA_TOPIC_FACE_RECOGNITION: str = "face-recognition-tasks"
    KAFKA_TOPIC_RESULTS: str = "face-recognition-results"
    
    # Spark Configuration
    SPARK_MASTER: str = os.getenv("SPARK_MASTER", "spark://192.168.80.147:7077")
    
    # Database Configuration
    # PostgreSQL cho môi trường phân tán
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://faceid:faceid123@192.168.80.147:5432/faceid"
    )
    
    # Storage Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    KNOWN_FACES_DIR: str = os.getenv("KNOWN_FACES_DIR", "known_faces")
    
    # Branch Configuration (cho các máy worker)
    # Mỗi máy có thể có một branch_id mặc định
    DEFAULT_BRANCH_ID: int = int(os.getenv("DEFAULT_BRANCH_ID", "0"))  # 0 = không có branch mặc định

settings = Settings()

