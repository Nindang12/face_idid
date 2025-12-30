"""
Spark Structured Streaming Application cho Face Recognition
Sử dụng Spark Structured Streaming với Kafka để xử lý nhận diện khuôn mặt phân tán
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf, struct, to_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, BooleanType
import json
import logging
import sys
import os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Schema cho Kafka message input
input_schema = StructType([
    StructField("task_id", StringType(), True),
    StructField("image_path", StringType(), True),
    StructField("branch_id", IntegerType(), True),
    StructField("timestamp", StringType(), True)
])

# Schema cho output result
output_schema = StructType([
    StructField("task_id", StringType(), True),
    StructField("image_path", StringType(), True),
    StructField("branch_id", IntegerType(), True),
    StructField("recognized", BooleanType(), True),
    StructField("result", StringType(), True),  # JSON string
    StructField("confidence", DoubleType(), True),
    StructField("status", StringType(), True),
    StructField("processed_by", StringType(), True),
    StructField("timestamp", StringType(), True)
])

def process_face_recognition(task_id, image_path, branch_id):
    """
    UDF để xử lý nhận diện khuôn mặt
    Lưu ý: Face recognition cần được thực hiện trên mỗi worker node
    """
    try:
        # Import face recognition service (cần có trên mỗi worker)
        # Thêm app directory vào path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.join(current_dir, "app")
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        from face_recognition_service import FaceRecognitionService
        from database import SessionLocal, Order
        from minio_service import minio_service
        
        logger.info(f"[Spark Worker] Processing task {task_id} for image {image_path}")
        
        # Khởi tạo face service
        face_service = FaceRecognitionService()
        
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
        
        
        # Xử lý download từ MinIO
        local_image_path = image_path
        is_temp_file = False
        
        # Nếu path không phải absolute path hoặc file không tồn tại, thử download từ MinIO
        if not os.path.isabs(image_path) or not os.path.exists(image_path):
            logger.info(f"[Spark Worker] File {image_path} seems to be remote, downloading from MinIO...")
            
            import tempfile
            file_ext = os.path.splitext(image_path)[1] or ".jpg"
            # Tạo temp file trong /tmp của worker node
            fd, temp_path = tempfile.mkstemp(suffix=file_ext)
            os.close(fd)
            
            local_image_path = temp_path
            is_temp_file = True
            
            # Download
            img_data = minio_service.download_file(image_path)
            if img_data:
                with open(local_image_path, "wb") as f:
                    f.write(img_data)
                logger.info(f"✅ Downloaded from MinIO to {local_image_path}")
            else:
                # Thử check xem có phải process local cũ gửi local path không?
                # Nếu không download được từ MinIO và file không tồn tại -> Lỗi
                raise Exception(f"Image not found at {image_path} and could not download from MinIO")

        try:
            # Nhận diện khuôn mặt
            if branch_customer_ids:
                result, confidence = face_service.recognize_face_in_branch(local_image_path, branch_customer_ids)
            else:
                result, confidence = face_service.recognize_face(local_image_path)
        finally:
             if is_temp_file and os.path.exists(local_image_path):
                os.remove(local_image_path)

        
        # Tạo kết quả
        recognition_result = {
            'task_id': task_id,
            'image_path': image_path,
            'branch_id': branch_id,
            'recognized': result is not None,
            'result': json.dumps(result) if result else None,
            'confidence': float(confidence) if confidence else 0.0,
            'status': 'completed',
            'processed_by': 'spark-worker',
            'timestamp': datetime.now().isoformat()
        }
        
        # Lưu kết quả lên MinIO
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            date_path = datetime.now().strftime('%Y/%m/%d')
            object_path = f"recognition_results/{date_path}/result_{task_id}_{timestamp}.json"
            
            data_bytes = json.dumps(recognition_result, ensure_ascii=False).encode('utf-8')
            if minio_service.upload_file(object_path, data_bytes, 'application/json'):
                logger.info(f"✅ Saved task {task_id} to MinIO: {object_path}")
            else:
                logger.warning(f"⚠️  Failed to save task {task_id} to MinIO")
        except Exception as e:
            logger.error(f"❌ Error saving to MinIO: {e}")
        
        return json.dumps(recognition_result)
        
    except Exception as e:
        logger.error(f"❌ Error processing task {task_id}: {e}", exc_info=True)
        error_result = {
            'task_id': task_id,
            'image_path': image_path,
            'branch_id': branch_id,
            'recognized': False,
            'result': None,
            'confidence': 0.0,
            'status': 'error',
            'error': str(e),
            'processed_by': 'spark-worker',
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(error_result)

# Register UDF
process_face_recognition_udf = udf(process_face_recognition, StringType())

def main():
    """Main function để chạy Spark Streaming"""
    
    # Lấy config từ environment variables
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.80.147:9092")
    kafka_input_topic = os.getenv("KAFKA_TOPIC_FACE_RECOGNITION", "face-recognition-tasks")
    kafka_output_topic = os.getenv("KAFKA_TOPIC_RESULTS", "face-recognition-results")
    spark_master = os.getenv("SPARK_MASTER", "spark://192.168.80.147:7077")
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Spark Structured Streaming for Face Recognition")
    logger.info(f"📊 Spark Master: {spark_master}")
    logger.info(f"📊 Kafka Bootstrap Servers: {kafka_bootstrap_servers}")
    logger.info(f"📊 Input Topic: {kafka_input_topic}")
    logger.info(f"📊 Output Topic: {kafka_output_topic}")
    logger.info("=" * 60)
    
    # Tạo Spark Session
    # Lưu ý: Disable HDFS và dùng local filesystem cho checkpoint
    spark = SparkSession.builder \
        .appName("FaceRecognitionStreaming") \
        .master(spark_master) \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
        .config("spark.sql.streaming.checkpointLocation", "file:///tmp/spark-checkpoint-face-recognition") \
        .config("spark.hadoop.fs.defaultFS", "file:///") \
        .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem") \
        .config("spark.hadoop.fs.hdfs.impl", "org.apache.hadoop.hdfs.DistributedFileSystem") \
        .config("spark.hadoop.fs.AbstractFileSystem.hdfs.impl", "org.apache.hadoop.fs.Hdfs") \
        .config("spark.hadoop.fs.hdfs.impl.disable.cache", "true") \
        .config("spark.sql.warehouse.dir", "file:///tmp/spark-warehouse") \
        .getOrCreate()
    
    # Set Hadoop configuration để tránh kết nối HDFS
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.defaultFS", "file:///")
    spark.sparkContext._jsc.hadoopConfiguration().set("fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("✅ Spark Session created")
    
    # Đọc stream từ Kafka
    logger.info(f"📥 Reading from Kafka topic: {kafka_input_topic}")
    logger.info(f"⚠️  Make sure topic '{kafka_input_topic}' exists in Kafka before starting")
    
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", kafka_input_topic) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # DEBUG: In ra console để kiểm tra dữ liệu đọc được (Tạm tắt để check output)
    # debug_query = df.selectExpr("CAST(value AS STRING)").writeStream \
    #     .format("console") \
    #     .outputMode("append") \
    #     .start()

    # Parse JSON từ Kafka value
    df_parsed = df.select(
        col("key").cast("string").alias("kafka_key"),
        col("value").cast("string").alias("json_value"),
        col("timestamp").alias("kafka_timestamp")
    ).filter(col("json_value").isNotNull())
    
    # Parse JSON thành struct
    df_structured = df_parsed.select(
        from_json(col("json_value"), input_schema).alias("data")
    ).select("data.*")
    
    # Xử lý face recognition với UDF
    df_processed = df_structured.select(
        col("task_id"),
        col("image_path"),
        col("branch_id"),
        process_face_recognition_udf(
            col("task_id"),
            col("image_path"),
            col("branch_id")
        ).alias("result_json")
    )
    
    # Parse result JSON và chuẩn bị output
    df_output = df_processed.select(
        from_json(col("result_json"), output_schema).alias("result")
    ).select("result.*")

    # DEBUG: In kết quả ĐÃ XỬ LÝ ra console
    debug_output_query = df_output.writeStream \
        .format("console") \
        .option("truncate", "false") \
        .outputMode("append") \
        .start()
    
    # Convert output thành JSON string để gửi về Kafka
    df_final = df_output.select(
        col("task_id").alias("key"),
        to_json(struct([
            col("task_id"),
            col("image_path"),
            col("branch_id"),
            col("recognized"),
            col("result"),
            col("confidence"),
            col("status"),
            col("processed_by"),
            col("timestamp")
        ])).alias("value")
    )
    
    # Ghi stream về Kafka
    logger.info(f"📤 Writing to Kafka topic: {kafka_output_topic}")
    query = df_final \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("topic", kafka_output_topic) \
        .option("checkpointLocation", "file:///tmp/spark-checkpoint-face-recognition-output") \
        .outputMode("append") \
        .start()
    
    logger.info("✅ Spark Streaming started. Waiting for messages...")
    logger.info("⏳ Press Ctrl+C to stop")
    
    # Chờ query chạy
    # PySpark StreamingQueryManager.awaitTermination() waits for any
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()

