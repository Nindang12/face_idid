import json
import uuid
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceRecognitionProducer:
    """
    Kafka Producer dùng để gửi task nhận diện khuôn mặt.
    Được thiết kế để **không** làm app crash nếu Kafka chưa sẵn sàng.
    """

    def __init__(self):
        self.topic = settings.KAFKA_TOPIC_FACE_RECOGNITION
        self.producer = None

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            logger.info(
                f"KafkaProducer initialized with bootstrap_servers={settings.KAFKA_BOOTSTRAP_SERVERS}"
            )
        except NoBrokersAvailable as e:
            # Không làm app dừng, chỉ log lỗi. Các lệnh send sau sẽ trả về False.
            logger.error(
                f"No Kafka brokers available at {settings.KAFKA_BOOTSTRAP_SERVERS}. "
                f"Kafka features will be disabled until broker is available. Error: {e}"
            )
            self.producer = None
        except KafkaError as e:
            logger.error(f"Failed to initialize KafkaProducer: {e}")
            self.producer = None

    def send_recognition_task(
        self, task_id: str, image_path: str, branch_id: int = None
    ) -> bool:
        """Gửi task nhận diện khuôn mặt vào Kafka. Trả về True/False."""
        if not self.producer:
            logger.error(
                "KafkaProducer is not available. Cannot send recognition task. "
                f"bootstrap_servers={settings.KAFKA_BOOTSTRAP_SERVERS}"
            )
            return False

        message = {
            "task_id": task_id,
            "image_path": image_path,
            "branch_id": branch_id,
            "timestamp": str(uuid.uuid4()),
        }

        try:
            future = self.producer.send(
                self.topic,
                key=task_id,
                value=message,
            )
            future.get(timeout=10)
            logger.info(f"Sent recognition task {task_id} to Kafka topic {self.topic}")
            return True
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            return False

    def close(self):
        if self.producer:
            self.producer.close()


# Singleton instance (có xử lý an toàn khi Kafka chưa sẵn sàng)
producer = FaceRecognitionProducer()

