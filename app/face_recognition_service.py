import face_recognition
import numpy as np
import os
import pickle
import time
from pathlib import Path
from app.config import settings
from app.minio_service import minio_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceRecognitionService:
    def __init__(self):
        self.known_encodings = {}
        self.known_names = {}
        self.last_updated = 0
        self.CACHE_TTL = 10  # Check for updates every 10 seconds (aggressive for demo)
        self.load_known_faces()
    
    def refresh_cache_if_needed(self):
        """Kiểm tra và cập nhật cache nếu hết hạn"""
        if time.time() - self.last_updated > self.CACHE_TTL:
            self.load_known_faces()

    def load_known_faces(self):
        """Load các khuôn mặt mới từ MinIO (Smart Update)"""
        try:
            current_time = time.time()
            # Liệt kê tất cả encodings từ MinIO
            encoding_files = minio_service.list_files(prefix="encodings/")
            
            # Chỉ download những file chưa có trong local cache
            # (Giả định đơn giản: file name = user_id.pkl, không thay đổi content)
            
            new_files_count = 0
            for object_path in encoding_files:
                if object_path.endswith('.pkl'):
                    user_id = Path(object_path).stem
                    
                    # Nếu user_id chưa có trong cache -> Download
                    if user_id not in self.known_encodings:
                        try:
                            # Download encoding từ MinIO
                            encoding_data = minio_service.download_file(object_path)
                            if encoding_data:
                                data = pickle.loads(encoding_data)
                                self.known_encodings[user_id] = data['encoding']
                                self.known_names[user_id] = data['name']
                                new_files_count += 1
                        except Exception as e:
                            logger.error(f"Error loading face encoding from MinIO {object_path}: {e}")
                            
            if new_files_count > 0:
                logger.info(f"Updated face cache: Loaded {new_files_count} new faces. Total: {len(self.known_encodings)}")
            
            self.last_updated = current_time
            
        except Exception as e:
            logger.error(f"Error loading known faces from MinIO: {e}")
    
    def encode_face(self, image_path: str):
        """Encode khuôn mặt từ ảnh"""
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            
            if len(encodings) > 0:
                return encodings[0]
            else:
                logger.warning(f"No face found in image: {image_path}")
                return None
        except Exception as e:
            logger.error(f"Error encoding face from {image_path}: {e}")
            return None
    
    def save_face_encoding(self, user_id: str, name: str, image_path: str):
        """Lưu encoding của khuôn mặt lên MinIO"""
        encoding = self.encode_face(image_path)
        if encoding is not None:
            # Serialize encoding data
            encoding_data = pickle.dumps({
                'encoding': encoding,
                'name': name
            })
            
            # Upload lên MinIO
            object_path = f"encodings/{user_id}.pkl"
            if minio_service.upload_file(object_path, encoding_data, "application/octet-stream"):
                # Cập nhật cache
                self.known_encodings[user_id] = encoding
                self.known_names[user_id] = name
                logger.info(f"Saved face encoding for user: {user_id} to MinIO")
                return True
            else:
                logger.error(f"Failed to save face encoding for user: {user_id} to MinIO")
                return False
        return False
    
    def recognize_face(self, image_path: str, tolerance: float = 0.50):
        """Nhận diện khuôn mặt trong ảnh"""
        self.refresh_cache_if_needed() # Auto-refresh cache
        
        try:
            unknown_encoding = self.encode_face(image_path)
            if unknown_encoding is None:
                return None, 0.0
            
            # So sánh với tất cả khuôn mặt đã biết
            best_match = None
            best_distance = float('inf')
            
            for user_id, known_encoding in self.known_encodings.items():
                distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
                if distance < best_distance:
                    best_distance = distance
                    best_match = user_id
            
            # Kiểm tra xem có match không
            if best_match and best_distance <= tolerance:
                confidence = 1 - best_distance
                return {
                    'customer_id': best_match,
                    'name': self.known_names.get(best_match, 'Unknown'),
                    'confidence': round(confidence, 4),
                    'distance': round(best_distance, 4)
                }, confidence
            else:
                return None, 0.0
                
        except Exception as e:
            logger.error(f"Error recognizing face from {image_path}: {e}")
            return None, 0.0
    
    def recognize_face_in_room(self, image_path: str, room_user_ids: list = None, tolerance: float = 0.50):
        """Nhận diện khuôn mặt trong một room cụ thể (deprecated - dùng recognize_face_in_branch)"""
        return self.recognize_face_in_branch(image_path, room_user_ids, tolerance)
    
    def recognize_face_in_branch(self, image_path: str, branch_customer_ids: list = None, tolerance: float = 0.50):
        """Nhận diện khuôn mặt trong một branch cụ thể"""
        self.refresh_cache_if_needed() # Auto-refresh cache
        
        if branch_customer_ids is None:
            return self.recognize_face(image_path, tolerance)
        
        try:
            unknown_encoding = self.encode_face(image_path)
            if unknown_encoding is None:
                return None, 0.0
            
            # Chỉ so sánh với customers trong branch
            best_match = None
            best_distance = float('inf')
            
            for customer_id in branch_customer_ids:
                customer_id_str = str(customer_id)
                if customer_id_str in self.known_encodings:
                    known_encoding = self.known_encodings[customer_id_str]
                    distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
                    if distance < best_distance:
                        best_distance = distance
                        best_match = customer_id_str
            
            if best_match and best_distance <= tolerance:
                confidence = 1 - best_distance
                return {
                    'customer_id': best_match,
                    'name': self.known_names.get(best_match, 'Unknown'),
                    'confidence': round(confidence, 4),
                    'distance': round(best_distance, 4)
                }, confidence
            else:
                return None, 0.0
                
        except Exception as e:
            logger.error(f"Error recognizing face in branch from {image_path}: {e}")
            return None, 0.0

# Singleton instance
face_service = FaceRecognitionService()

