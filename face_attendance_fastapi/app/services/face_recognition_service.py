import numpy as np
import cv2
import json
import logging

logger = logging.getLogger(__name__)

try:
    import face_recognition
    USE_DLIB = True
    logger.info("Using dlib face_recognition library")
except ImportError:
    USE_DLIB = False
    logger.warning("face_recognition library not available; using OpenCV fallback")

class FaceRecognitionService:
    def __init__(self):
        if not USE_DLIB:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_faces(self, image_bytes: bytes):
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return [], img
        if USE_DLIB:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            return locations, rgb
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            return faces, img

    def extract_encoding(self, image_bytes: bytes):
        faces, img = self.detect_faces(image_bytes)
        if len(faces) == 0:
            return None, 0
        if USE_DLIB:
            encodings = face_recognition.face_encodings(img, faces)
            if encodings:
                return encodings[0].tolist(), self._assess_quality(img, faces[0])
        else:
            return self._opencv_encoding(img, faces[0]), 75.0
        return None, 0

    def _opencv_encoding(self, img, face_rect):
        if len(face_rect) == 4:
            x, y, w, h = face_rect
            face_roi = img[y:y+h, x:x+w]
        else:
            face_roi = img
        face_resized = cv2.resize(face_roi, (128, 128))
        return (face_resized.flatten() / 255.0).tolist()[:128]

    def _assess_quality(self, img, face_location):
        return 85.0

    def match_face(self, encoding, known_encodings, threshold=0.6):
        if not known_encodings:
            return None, 0
        encoding_arr = np.array(encoding)
        best_match = None
        best_dist = float('inf')
        for uid, known_enc in known_encodings:
            known_arr = np.array(json.loads(known_enc) if isinstance(known_enc, str) else known_enc)
            if USE_DLIB:
                dist = np.linalg.norm(encoding_arr - known_arr)
            else:
                dist = np.linalg.norm(encoding_arr[:128] - known_arr[:128])
            if dist < best_dist:
                best_dist = dist
                best_match = uid
        confidence = max(0, (1 - best_dist) * 100) if USE_DLIB else max(0, (1 - best_dist / 50) * 100)
        if confidence >= threshold * 100:
            return best_match, round(confidence, 1)
        return None, round(confidence, 1)

face_service = FaceRecognitionService()
