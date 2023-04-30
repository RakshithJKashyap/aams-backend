from celery import Celery
from pymongo import mongo_client
from dotenv import load_dotenv
import os
import urllib.request
import numpy as np
import cv2
import torch
from face_detector import Detector
import logging
import pickle
from vidgear.gears import CamGear
from celery.utils.log import get_task_logger
import time

detector = Detector()

logger = get_task_logger(__name__)

load_dotenv()
reddis = os.getenv("REDIS")
mongodb = os.getenv("MONGODB_URI")

app = Celery('cworker',broker=reddis, backend=mongodb)
client = mongo_client.MongoClient(mongodb)
db = client['aams']
users = db['users']
cams = db['camera']
sessions = db['sessions']
@app.task(name='health_check')
def health_check():
    return "OK, I'm alive!."

@app.task(name='first_register')
def first_register(image_url, auth0_token):
    # Download the image and convert it to a NumPy array
    resp = urllib.request.urlopen(image_url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")

    # Decode the NumPy array into OpenCV format
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    logger.info("Calling Face Detector on image")
    detector.get_embeddings_facenet(image)
    if len(detector.class_face_vectors):
        logger.info("Updating database")
        data = pickle.dumps(detector.class_face_vectors[0])
        query = {'auth0_token': auth0_token}
        update = {'$set': {'face_vector': data}}
        users.update_one(query, update)
        

    
@app.task(name='start_attendance')
def start_attendance(class_name, sem, section, branch):
    class_session = {"class_name": class_name, "sem": sem, "section": section, "branch": branch, "attendance": []}
    class_vector = []
    class_names = []
    query = {"sem": sem, "section": section, "branch": branch}
    cursor = users.find()

    camera  = {"class_name": class_name}
    source = cams.find_one(camera)['ip_address']

    for document in cursor:
        if 'face_vector' in document.keys():
            class_vector.append(torch.tensor(pickle.loads(document['face_vector'])))
            class_names.append(document['name'])
    stream = CamGear(source=source, stream_mode = True,logging=True).start()
    start_time = time.time()
    while time.time() - start_time < 10:
    # Read the next frame
        frame = stream.read()
        # Check if the frame was successfully read
        logger.info(type(frame))
        if frame is None:
            break
        detector.current_frame_faces = []
        detector.face_crop_frames = []
        detector.face_coordiantes = []
        detector.class_face_vectors = []
        detector.get_embeddings_facenet(frame)
        
        # Compare face embeddings
        for i in range(len(detector.class_face_vectors)):
            for j in range(len(class_vector)):
                distance = torch.nn.functional.pairwise_distance(detector.class_face_vectors[i], torch.tensor(class_vector[j]))
                if float(1-distance)*100 > 30.0:
                    co_ordinates = detector.face_coordiantes[i]
                    logger.info(co_ordinates)
                    frame = cv2.rectangle(frame, (co_ordinates['x1'], co_ordinates['y1']), (co_ordinates['x2'], co_ordinates['y2']), (0, 255, 0), 2)
                    frame = cv2.putText(frame, class_names[j]+str(" Confidence "+ str(float(1-distance)*100)), (int(co_ordinates['x1'])-12, int(co_ordinates['y1'])-12), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    logger.info(f"Distance between image {i} and image {class_names[j]}: {float(1-distance)*100}")
                    if class_names[j] not in class_session['attendance']:
                        class_session['attendance'].append(class_names[j])

        logger.info(class_session['attendance'])
        # # Display the frame
        # cv2.imshow('Frame', frame)

        # # Wait for a key press and then exit if the 'q' key is pressed
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

        time.sleep(5)
    sessions.insert_one(class_session)

        

