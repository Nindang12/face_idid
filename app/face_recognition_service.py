import face_recognition
import numpy as np
import os
import pickle
from pathlib import Path
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceRecognitionService:
    def __init__(self):
        self.known_faces_dir = Path(settings.KNOWN_FACES_DIR)
        self.known_faces_dir.mkdir(exist_ok=True)
        self.known_encodings = {}
        self.known_names = {}
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load tất cả khuôn mặt đã biết từ thư mục"""
        for file_path in self.known_faces_dir.glob("*.pkl"):
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                    user_id = file_path.stem
                    self.known_encodings[user_id] = data['encoding']
                    self.known_names[user_id] = data['name']
                logger.info(f"Loaded face encoding for user: {user_id}")
            except Exception as e:
                logger.error(f"Error loading face encoding from {file_path}: {e}")
    
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
        """Lưu encoding của khuôn mặt"""
        encoding = self.encode_face(image_path)
        if encoding is not None:
            file_path = self.known_faces_dir / f"{user_id}.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump({
                    'encoding': encoding,
                    'name': name
                }, f)
            
            self.known_encodings[user_id] = encoding
            self.known_names[user_id] = name
            logger.info(f"Saved face encoding for user: {user_id}")
            return True
        return False
    
    def recognize_face(self, image_path: str, tolerance: float = 0.6):
        """Nhận diện khuôn mặt trong ảnh"""
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
    
    def recognize_face_in_room(self, image_path: str, room_user_ids: list = None, tolerance: float = 0.6):
        """Nhận diện khuôn mặt trong một room cụ thể (deprecated - dùng recognize_face_in_branch)"""
        return self.recognize_face_in_branch(image_path, room_user_ids, tolerance)
    
    def recognize_face_in_branch(self, image_path: str, branch_customer_ids: list = None, tolerance: float = 0.6):
        """Nhận diện khuôn mặt trong một branch cụ thể"""
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

