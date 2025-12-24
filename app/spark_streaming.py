"""
Spark Streaming Application cho Face Recognition
Sử dụng Spark đã cài trên máy host và lưu dữ liệu lên Hadoop HDFS
"""
import os
import sys
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer
from app.face_recognition_service import FaceRecognitionService
from app.config import settings
from app.database import SessionLocal, Customer, Order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_to_hadoop(data, hdfs_path):
    """
    Lưu dữ liệu lên Hadoop HDFS
    Sử dụng hdfs3 hoặc pyarrow để kết nối với HDFS
    """
    try:
        # Cách 1: Sử dụng hdfs3
        try:
            from hdfs3 import HDFileSystem
            hdfs_host = settings.HDFS_NAMENODE.split('://')[1].split(':')[0]
            hdfs_port = int(settings.HDFS_NAMENODE.split(':')[-1])
            
            hdfs = HDFileSystem(host=hdfs_host, port=hdfs_port)
            
            # Tạo thư mục nếu chưa có
            dir_path = os.path.dirname(hdfs_path)
            if not hdfs.exists(dir_path):
                hdfs.mkdir(dir_path)
            
            # Lưu dữ liệu
            with hdfs.open(hdfs_path, 'wb') as f:
                if isinstance(data, dict):
                    f.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                else:
                    f.write(str(data).encode('utf-8'))
            
            logger.info(f"✅ Data saved to HDFS: {hdfs_path}")
            return True
            
        except ImportError:
            # Cách 2: Sử dụng pyarrow (nếu hdfs3 không có)
            try:
                import pyarrow.fs as pafs
                filesystem = pafs.HadoopFileSystem.from_uri(settings.HDFS_NAMENODE)
                
                # Tạo thư mục nếu chưa có
                dir_path = os.path.dirname(hdfs_path)
                try:
                    file_info = filesystem.get_file_info(dir_path)
                    if file_info.type != pafs.FileType.Directory:
                        filesystem.create_dir(dir_path, recursive=True)
                except:
                    filesystem.create_dir(dir_path, recursive=True)
                
                # Lưu dữ liệu
                with filesystem.open_output_stream(hdfs_path) as f:
                    if isinstance(data, dict):
                        f.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                    else:
                        f.write(str(data).encode('utf-8'))
                
                logger.info(f"✅ Data saved to HDFS: {hdfs_path}")
                return True
                
            except ImportError:
                # Cách 3: Sử dụng subprocess với hdfs command (nếu có Hadoop CLI)
                import subprocess
                import tempfile
                
                # Tạo file tạm
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                    json.dump(data, tmp_file, ensure_ascii=False)
                    tmp_path = tmp_file.name
                
                try:
                    # Upload lên HDFS
                    cmd = f"hdfs dfs -mkdir -p {os.path.dirname(hdfs_path)}"
                    subprocess.run(cmd, shell=True, check=True, capture_output=True)
                    
                    cmd = f"hdfs dfs -put {tmp_path} {hdfs_path}"
                    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                    
                    logger.info(f"✅ Data saved to HDFS: {hdfs_path}")
                    return True
                except subprocess.CalledProcessError as e:
                    logger.error(f"❌ Failed to save to HDFS using hdfs command: {e.stderr}")
                    return False
                finally:
                    os.unlink(tmp_path)
                    
    except Exception as e:
        logger.error(f"❌ Error saving to HDFS: {e}", exc_info=True)
        return False

def process_with_spark_workers():
    """
    Xử lý tasks từ Kafka và lưu dữ liệu lên Hadoop HDFS
    Sử dụng Kafka Consumer để nhận dữ liệu từ Kafka
    Sau khi xử lý, lưu kết quả lên HDFS
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
    logger.info(f"HDFS Namenode: {settings.HDFS_NAMENODE}")
    logger.info(f"HDFS Data Directory: {settings.HDFS_DATA_DIR}")
    
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
                    'processed_by': 'spark-worker',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Lưu kết quả lên Hadoop HDFS
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                date_path = datetime.now().strftime('%Y/%m/%d')
                hdfs_path = f"{settings.HDFS_DATA_DIR}/recognition_results/{date_path}/result_{task_id}_{timestamp}.json"
                
                logger.info(f"💾 Attempting to save to HDFS: {hdfs_path}")
                save_success = save_to_hadoop(recognition_result, hdfs_path)
                
                if save_success:
                    logger.info(f"✅ Successfully saved task {task_id} to HDFS")
                else:
                    logger.warning(f"⚠️  Failed to save task {task_id} to HDFS, but continuing...")
                
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
                    'processed_by': 'spark-worker',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Lưu error lên HDFS
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                date_path = datetime.now().strftime('%Y/%m/%d')
                hdfs_path = f"{settings.HDFS_DATA_DIR}/errors/{date_path}/error_{task_data.get('task_id', 'unknown')}_{timestamp}.json"
                save_to_hadoop(error_result, hdfs_path)
                
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
    logger.info(f"Spark Master: {settings.SPARK_MASTER}")
    logger.info(f"HDFS Namenode: {settings.HDFS_NAMENODE}")
    logger.info(f"HDFS Data Dir: {settings.HDFS_DATA_DIR}")
    logger.info("=" * 50)
    
    # Kiểm tra kết nối HDFS
    try:
        test_path = f"{settings.HDFS_DATA_DIR}/test_connection.json"
        test_data = {"test": True, "timestamp": datetime.now().isoformat()}
        if save_to_hadoop(test_data, test_path):
            logger.info("✅ HDFS connection test successful!")
        else:
            logger.warning("⚠️  HDFS connection test failed, but continuing...")
    except Exception as e:
        logger.warning(f"⚠️  Could not test HDFS connection: {e}")
    
    process_with_spark_workers()
