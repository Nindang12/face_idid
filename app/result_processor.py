
import os
import sys
import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from kafka import KafkaConsumer
from app.config import settings
from app.database import SessionLocal, Customer, RecognitionLog
from app.face_recognition_service import FaceRecognitionService
from app.minio_service import minio_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResultProcessor")


# Initialize FaceRecognitionService ONCE at startup to maintain cache
face_service = FaceRecognitionService()

def auto_register_customer(db, image_path_local, file_extension):
    """
    Register a new customer from a local image file.
    """
    try:
        # Create customer
        customer = Customer(
            name="Guest",
            face_encoding_path="",
            phone=None,
            email=None,
        )
        db.add(customer)
        db.flush() # Use flush instead of commit to get ID but keep transaction open
        db.refresh(customer)
        logger.info(f"Created new customer record with ID: {customer.id}")

        # Read image data
        with open(image_path_local, "rb") as f:
            image_data = f.read()

        # Upload to MinIO (permanent location)
        minio_object_path = f"images/customer_{customer.id}{file_extension}"
        content_type = f"image/{file_extension[1:]}" if file_extension else "image/jpeg"
        
        if minio_service.upload_file(minio_object_path, image_data, content_type):
            logger.info(f"Uploaded customer image to: {minio_object_path}")
        else:
            logger.error(f"Failed to upload customer image to {minio_object_path}")
            db.rollback() # Rollback customer creation
            return None

        # Generate and save face encoding using the GLOBAL face_service instance
        saved = face_service.save_face_encoding(str(customer.id), customer.name, image_path_local)
        
        if saved:
            logger.info(f"Saved face encoding for customer {customer.id}")
            # Update customer with MinIO path and COMMIT everything
            customer.face_encoding_path = minio_object_path
            db.commit() 
            db.refresh(customer)
            return customer
        else:
            logger.warning(f"Could not save face encoding for customer {customer.id} - Rolling back registration")
            # If we can't encode the face, we shouldn't create a 'Guest' user
            # Since we only used flush(), this rollback will remove the customer record
            db.rollback()
            return None

    except Exception as e:
        logger.error(f"Error in auto_register_customer: {e}", exc_info=True)
        return None

def process_results():
    logger.info("🚀 Starting Result Processor Service")
    logger.info(f"Listen on topic: {settings.KAFKA_TOPIC_RESULTS}")

    consumer = KafkaConsumer(
        settings.KAFKA_TOPIC_RESULTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='result-processor-group'
    )

    for message in consumer:
        try:
            data = message.value
            task_id = data.get('task_id')
            status = data.get('status')
            
            if status != 'completed':
                logger.info(f"Skipping task {task_id} with status {status}")
                continue

            logger.info(f"Processing result for task {task_id}")
            
            recognized = data.get('recognized')
            minio_temp_path = data.get('image_path') # e.g., temp/uuid.jpg
            branch_id = data.get('branch_id')
            
            db = SessionLocal()
            local_temp_file = None

            try:

                # Log recognition result to DB for UI Polling / History
                log_entry = RecognitionLog(
                    branch_id=branch_id,
                    image_path=minio_temp_path,
                    recognized=recognized,
                    confidence=str(data.get('confidence', 0.0)),
                    created_at=datetime.utcnow()
                )
                
                if recognized:
                    logger.info(f"✅ Face recognized for task {task_id}")
                    # Parse result JSON to get customer_id
                    try:
                        raw_result = data.get('result')
                        if raw_result:
                            result_json = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                            log_entry.customer_id = int(result_json.get('customer_id'))
                    except Exception as e:
                        logger.warning(f"Could not parse customer_id from result: {e}")
                else:
                    logger.info(f"👤 Face NOT recognized for task {task_id}. Checking again with updated cache...")
                    # ... (double check logic)
                    
                db.add(log_entry)
                db.commit() # Commit log entry first

                if not recognized:
                    # Proceed with double check and registration logic...

                    
                    # 1. Download image from MinIO temp path
                    if minio_temp_path:
                        file_ext = os.path.splitext(minio_temp_path)[1] or ".jpg"
                        fd, local_temp_file = tempfile.mkstemp(suffix=file_ext)
                        os.close(fd)
                        
                        logger.info(f"Downloading {minio_temp_path} to {local_temp_file}...")
                        img_data = minio_service.download_file(minio_temp_path)
                        
                        if img_data:
                            with open(local_temp_file, "wb") as f:
                                f.write(img_data)
                            
                            # === DOUBLE CHECKING LOGIC ===
                            # Check if the face is NOW recognized (maybe registered by a previous task in this batch)
                            double_check_result, _ = face_service.recognize_face(local_temp_file)
                            
                            if double_check_result:
                                matched_name = double_check_result.get('name')
                                matched_id = double_check_result.get('customer_id')
                                logger.info(f"✋ Wait! We actually know this person now: {matched_name} (ID: {matched_id}). Skipping registration.")
                                
                                # Update log entry so UI sees the result
                                log_entry.customer_id = int(matched_id)
                                log_entry.recognized = True
                                db.commit()
                            else:
                                # 2. Register new customer
                                # ONLY register if we can successfully encode the face (to prevent duplicates)
                                # Check encoding first before creating DB record?
                                # Or rely on auto_register_customer to return None if encoding fails?

                                # Let's modify auto_register_customer to be stricter
                                new_customer = auto_register_customer(db, local_temp_file, file_ext)
                                
                                if new_customer:
                                    logger.info(f"🎉 Successfully registered new customer: {new_customer.name} (ID: {new_customer.id})")
                                    
                                    # Update log entry so UI sees the new guest
                                    log_entry.customer_id = new_customer.id
                                    db.commit()
                                else:
                                    logger.warning(f"⏩ Skipped registration for task {task_id} because no face could be encoded.")
                        else:
                            logger.error(f"Could not download {minio_temp_path} from MinIO")
                    else:
                        logger.error("No image_path provided in result")

                # 3. Cleanup: Delete temp file from MinIO
                if minio_temp_path and minio_temp_path.startswith("temp/"):
                    logger.info(f"🧹 Deleting temp file from MinIO: {minio_temp_path}")
                    minio_service.client.remove_object(settings.MINIO_BUCKET_NAME, minio_temp_path)

            except Exception as e:
                logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            finally:
                db.close()
                if local_temp_file and os.path.exists(local_temp_file):
                    os.remove(local_temp_file)

        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    sys.path.append(os.getcwd())
    process_results()
