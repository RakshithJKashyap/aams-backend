import os
import cv2
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from  face_detector import Detector
from pymongo import MongoClient

detector = Detector()
# Load the MTCNN and InceptionResnet models
mtcnn = MTCNN()
resnet = InceptionResnetV1(pretrained='vggface2').eval()
client = MongoClient('mongodb://localhost:27017/')

# access the database
db = client['testx']

# access the collection
collection = db['faces']


cursor = collection.find()
# iterate over the cursor and print each document
database_vector = []
for document in cursor:
    database_vector.append(document['face'])
# Load all images in a folder
folder = 'data/3/'
cap = cv2.VideoCapture(0)
embeddings = []
# Loop through the frames of the video
while True:
    # Read the next frame
    ret, frame = cap.read()
    if cap.get(cv2.CAP_PROP_POS_FRAMES) % 30 != 0:
        continue
    # Check if the frame was successfully read
    if not ret:
        break
    detector.current_frame_faces = []
    detector.face_crop_frames = []
    detector.face_coordiantes = []
    detector.class_face_vectors = []
    detector.get_embeddings_facenet(frame)
    
    # Compare face embeddings
    for i in range(len(detector.class_face_vectors)):
        for j in range(len(database_vector)):
            distance = torch.nn.functional.pairwise_distance(detector.class_face_vectors[i], torch.tensor(database_vector[j]))
            print(float(1-distance)*100)
            if float(1-distance)*100 > 60.0:
                print(f"Distance between image {i} and image {j}: {float(1-distance)*100}")
    # Display the frame
    cv2.imshow('Frame', frame)

    # Wait for a key press and then exit if the 'q' key is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video file and close the window
cap.release()
cv2.destroyAllWindows()
    