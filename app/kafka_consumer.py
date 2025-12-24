import json
import logging
from kafka import KafkaConsumer
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceRecognitionConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            settings.KAFKA_TOPIC_RESULTS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='face-recognition-results-group'
        )
        logger.info(f"Consumer initialized for topic: {settings.KAFKA_TOPIC_RESULTS}")
    
    def consume_results(self):
        """Consume kết quả nhận diện từ Kafka"""
        for message in self.consumer:
            try:
                result = message.value
                logger.info(f"Received result: {result}")
                yield result
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    def close(self):
        self.consumer.close()

