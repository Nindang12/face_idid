"""
Spark Streaming Application cho Face Recognition
Sử dụng Kafka Consumer để nhận tasks và xử lý nhận diện khuôn mặt
Lưu kết quả lên MinIO Object Storage
"""
import os
import sys
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from app.face_recognition_service import FaceRecognitionService
from app.config import settings
from app.database import SessionLocal, Customer, Order
from app.minio_service import minio_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_to_minio(data, object_path):
    """
    Lưu dữ liệu lên MinIO Object Storage
    """
    try:
        if isinstance(data, dict):
            data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        
        from io import BytesIO
        data_stream = BytesIO(data_bytes)
        data_length = len(data_bytes)
        
        # Upload lên MinIO
        if minio_service.upload_file(object_path, data_bytes, 'application/json'):
            logger.info(f"✅ Data saved to MinIO: {object_path}")
            return True
        else:
            logger.error(f"❌ Failed to save to MinIO: {object_path}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error saving to MinIO: {e}", exc_info=True)
        return False

def process_with_spark_workers():
    """
    Xử lý tasks từ Kafka và lưu dữ liệu lên MinIO Object Storage
    Sử dụng Kafka Consumer để nhận dữ liệu từ Kafka
    Sau khi xử lý, lưu kết quả lên MinIO và gửi về Kafka results topic
    """
    face_service = FaceRecognitionService()
    
    try:
        consumer = KafkaConsumer(
            settings.KAFKA_TOPIC_FACE_RECOGNITION,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='face-recognition-spark-group',
            # Không set consumer_timeout_ms để consumer chạy liên tục
            # consumer_timeout_ms=None sẽ làm consumer chờ vô hạn
        )
        logger.info(f"✅ Spark Streaming Consumer started. Listening to topic: {settings.KAFKA_TOPIC_FACE_RECOGNITION}")
        logger.info(f"⏳ Waiting for messages... (Press Ctrl+C to stop)")
    except Exception as e:
        logger.error(f"❌ Failed to create Kafka Consumer: {e}")
        return
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logger.info(f"✅ Kafka Producer for results initialized")
    except Exception as e:
        logger.error(f"❌ Failed to create Kafka Producer: {e}")
        consumer.close()
        return
    
    logger.info(f"📊 MinIO Endpoint: {settings.MINIO_ENDPOINT}")
    logger.info(f"📊 MinIO Bucket: {settings.MINIO_BUCKET_NAME}")
    
    try:
        # Consumer sẽ chạy liên tục, chờ messages từ Kafka
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
                    'processed_by': 'spark-worker',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Lưu kết quả lên MinIO
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                date_path = datetime.now().strftime('%Y/%m/%d')
                object_path = f"recognition_results/{date_path}/result_{task_id}_{timestamp}.json"
                
                logger.info(f"💾 Attempting to save to MinIO: {object_path}")
                save_success = save_to_minio(recognition_result, object_path)
                
                if save_success:
                    logger.info(f"✅ Successfully saved task {task_id} to MinIO")
                else:
                    logger.warning(f"⚠️  Failed to save task {task_id} to MinIO, but continuing...")
                
                # Gửi kết quả về Kafka
                try:
                    producer.send(settings.KAFKA_TOPIC_RESULTS, value=recognition_result)
                    producer.flush()
                    logger.info(f"✅ Sent result for task {task_id} to Kafka results topic")
                except Exception as e:
                    logger.error(f"❌ Failed to send result to Kafka: {e}")
                
                logger.info(f"[Spark Worker] Task {task_id} completed: {result}")
                
            except Exception as e:
                logger.error(f"❌ Error processing task: {e}", exc_info=True)
                # Gửi error result
                error_result = {
                    'task_id': task_data.get('task_id', 'unknown') if 'task_data' in locals() else 'unknown',
                    'status': 'error',
                    'error': str(e),
                    'processed_by': 'spark-worker',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Lưu error lên MinIO
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    date_path = datetime.now().strftime('%Y/%m/%d')
                    object_path = f"errors/{date_path}/error_{error_result['task_id']}_{timestamp}.json"
                    save_to_minio(error_result, object_path)
                except:
                    pass
                
                # Gửi error về Kafka
                try:
                    producer.send(settings.KAFKA_TOPIC_RESULTS, value=error_result)
                    producer.flush()
                except:
                    pass
    
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Spark Streaming Consumer...")
    except Exception as e:
        logger.error(f"❌ Fatal error in Spark Streaming: {e}", exc_info=True)
    finally:
        consumer.close()
        producer.close()
        logger.info("✅ Spark Streaming Consumer closed")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 Starting Spark Streaming for Face Recognition")
    logger.info(f"📊 Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"📊 Topic: {settings.KAFKA_TOPIC_FACE_RECOGNITION}")
    logger.info(f"📊 Spark Master: {settings.SPARK_MASTER}")
    logger.info(f"📊 MinIO Endpoint: {settings.MINIO_ENDPOINT}")
    logger.info(f"📊 MinIO Bucket: {settings.MINIO_BUCKET_NAME}")
    logger.info("=" * 50)
    
    # Kiểm tra kết nối MinIO
    try:
        test_object_path = "test_connection.json"
        test_data = {"test": True, "timestamp": datetime.now().isoformat()}
        if save_to_minio(test_data, test_object_path):
            logger.info("✅ MinIO connection test successful!")
        else:
            logger.warning("⚠️  MinIO connection test failed, but continuing...")
    except Exception as e:
        logger.warning(f"⚠️  Could not test MinIO connection: {e}")
    
    process_with_spark_workers()

