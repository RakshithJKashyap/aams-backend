
from PIL import Image
from numpy import asarray
from mtcnn.mtcnn import MTCNN
from keras_vggface.vggface import VGGFace
from keras_vggface.utils import preprocess_input
import os
import cv2
from scipy.spatial.distance import cosine
import time
from facenet_pytorch import InceptionResnetV1
import tensorflow as tf 
import torch

class Detector:
    model = None
    current_frame_faces = []
    face_crop_frames = []
    matched_people_total = []
    current_frame_people = []
    present_in_class = []
    frames = []
    detector = None
    face_coordiantes = []
    class_face_vectors = []


    def __init__(self) -> None:
        self.model = VGGFace(model='resnet50', include_top=False, input_shape=(224, 224, 3), pooling='avg')
        self.detector = MTCNN()
        self.facenet = InceptionResnetV1(pretrained='vggface2').eval()
    
    def  check_similarity_with_database(self,known_embedding, candidate_embedding, thresh=0.5):
        score = cosine(known_embedding, candidate_embedding)
        return score
    
    def get_face_crop(self,face, frame):
        x1, y1, width, height = face
        x2, y2 = x1 + width, y1 + height
        print("Appending")
        self.face_coordiantes.append({   'x1':x1,
                                    'x2':x2,
                                    'y1':y1,
                                    'y2':y2
                                })
        face = frame[y1:y2, x1:x2]
        return face
    
    def extract_face_coordinates(self,
                            face, frame, required_size=(224, 224)
                            ):
        """
        This function converts the face in image to an array representation.
        """
        face = self.get_face_crop(face, frame)
        self.face_crop_frames.append(face)
        image = Image.fromarray(face)
        image = image.resize(required_size)
        face_array = asarray(image)
        self.current_frame_faces.append(face_array)

    def extract_face(self,frame):
        results = self.detector.detect_faces(frame)
        print("Detected faces",len(results))
        for i in range(len(results)):
            self.extract_face_coordinates(results[i]['box'], frame)
    def get_embeddings_facenet(self,frame):
        self.current_frame_faces = []
        self.extract_face(frame)
        for face in self.current_frame_faces:
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = torch.from_numpy(face).permute(2, 0, 1).float()
            embedding = self.facenet(face.unsqueeze(0))
            self.class_face_vectors.append(embedding)
    
    def get_embeddings_vggface(self, frame):
        self.current_frame_faces = []
        self.extract_face(frame) 
        for i in self.current_frame_faces:
            samples = asarray(self.current_frame_faces, 'float32')
            samples = preprocess_input(samples, version=2)
            yhat = self.model.predict(samples)
            self.class_face_vectors.append(yhat)
	