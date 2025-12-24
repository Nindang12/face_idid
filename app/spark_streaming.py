"""
Spark Streaming Application cho Face Recognition
Chạy độc lập hoặc trong Docker container
"""
import os
import sys
import json
import logging
from kafka import KafkaConsumer
from app.face_recognition_service import FaceRecognitionService
from app.config import settings
from app.database import SessionLocal, Customer, Order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_with_spark_workers():
    """
    Xử lý tasks từ Kafka sử dụng Spark workers
    Đây là phiên bản đơn giản hóa sử dụng Kafka Consumer trực tiếp
    Để sử dụng Spark thực sự, cần cấu hình Spark Streaming với Kafka
    """
    face_service = FaceRecognitionService()
    
    consumer = KafkaConsumer(
        settings.KAFKA_TOPIC_FACE_RECOGNITION,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='face-recognition-spark-group'
    )
    
    logger.info(f"Spark Streaming Consumer started. Listening to topic: {settings.KAFKA_TOPIC_FACE_RECOGNITION}")
    
    from kafka import KafkaProducer
    
    producer = KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    try:
        for message in consumer:
            try:
                task_data = message.value
                task_id = task_data.get('task_id')
                image_path = task_data.get('image_path')
                branch_id = task_data.get('branch_id')
                
                logger.info(f"[Spark Worker] Processing task {task_id} for image {image_path}")
                
                # Lấy danh sách customers đã từng đặt hàng tại branch này nếu có
                branch_customer_ids = None
                if branch_id:
                    db = SessionLocal()
                    try:
                        branch_orders = db.query(Order).filter(Order.branch_id == branch_id).all()
                        branch_customer_ids = list(set([o.customer_id for o in branch_orders]))
                        branch_customer_ids = [str(cid) for cid in branch_customer_ids]
                    finally:
                        db.close()
                
                # Nhận diện khuôn mặt
                if branch_customer_ids:
                    result, confidence = face_service.recognize_face_in_branch(image_path, branch_customer_ids)
                else:
                    result, confidence = face_service.recognize_face(image_path)
                
                # Tạo kết quả
                recognition_result = {
                    'task_id': task_id,
                    'image_path': image_path,
                    'branch_id': branch_id,
                    'recognized': result is not None,
                    'result': result,
                    'confidence': confidence,
                    'status': 'completed',
                    'processed_by': 'spark-worker'
                }
                
                # Gửi kết quả về Kafka
                producer.send(settings.KAFKA_TOPIC_RESULTS, value=recognition_result)
                producer.flush()
                
                logger.info(f"[Spark Worker] Task {task_id} completed: {result}")
                
            except Exception as e:
                logger.error(f"Error processing task: {e}", exc_info=True)
                # Gửi error result
                error_result = {
                    'task_id': task_data.get('task_id', 'unknown'),
                    'status': 'error',
                    'error': str(e),
                    'processed_by': 'spark-worker'
                }
                producer.send(settings.KAFKA_TOPIC_RESULTS, value=error_result)
                producer.flush()
    
    except KeyboardInterrupt:
        logger.info("Shutting down Spark Streaming Consumer...")
    finally:
        consumer.close()
        producer.close()

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting Spark Streaming for Face Recognition")
    logger.info(f"Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"Topic: {settings.KAFKA_TOPIC_FACE_RECOGNITION}")
    logger.info("=" * 50)
    
    process_with_spark_workers()
