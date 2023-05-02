import datetime
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
from scipy.spatial.distance import cosine
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
    detector.get_embeddings_vggface(image)
    if len(detector.class_face_vectors):
        logger.info("Updating database")
        data = detector.class_face_vectors[0].tolist()
        query = {'auth0_token': auth0_token}
        update = {'$set': {'face_vector': data}}
        users.update_one(query, update)
        

    
@app.task(name='start_attendance')
def start_attendance(class_name, sem, section, branch, teacher_id):
    current_datetime = datetime.datetime.now()

    # Convert the datetime object to epoch time
    epoch_time = current_datetime.strftime("%d/%m/%Y")
    class_session = {"class_name": class_name, "teacher_name":teacher_id,"sem": sem,
                      "section": section, "branch": branch, "attendance": [], 
                      'date':epoch_time,
                      }
    class_vector = []
    class_names = []
    query = {"sem": sem, "section": section, "branch": branch}
    cursor = users.find()

    camera  = {"class_name": class_name}
    source = cams.find_one(camera)['ip_address']
    cams.update_one(camera, {'$set': {'status': 'true'}})
    try:
        for document in cursor:
            if 'face_vector' in document.keys():
                class_vector.append(np.array(document['face_vector'][0]))
                class_names.append(document['name'])
        
        start_time = time.time()
        while time.time() - start_time < 120:
            stream = CamGear(source=source, stream_mode = True,logging=True).start()
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
            detector.get_embeddings_vggface(frame)
            
            # Compare face embeddings
            for i in range(len(detector.class_face_vectors)):
                logger.info(detector.class_face_vectors[i].shape)
                for j in range(len(class_vector)):
                    distance = cosine(detector.class_face_vectors[i][0], class_vector[j])
                    logger.info(f"Distance between image {i} and image {class_names[j]}: {float(1-distance)*100}")
                    if float(1-distance)*100 > 80.0:
                        co_ordinates = detector.face_coordiantes[i]
                        logger.info(co_ordinates)
                        frame = cv2.rectangle(frame, (co_ordinates['x1'], co_ordinates['y1']), (co_ordinates['x2'], co_ordinates['y2']), (0, 255, 0), 2)
                        frame = cv2.putText(frame, class_names[j]+str(" Confidence "+ str(float(1-distance)*100)), (int(co_ordinates['x1'])-12, int(co_ordinates['y1'])-12), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)     
                        if class_names[j] not in class_session['attendance']:
                            class_session['attendance'].append(class_names[j])
                        continue

            logger.info(class_session['attendance'])
            # Display the frame
            # cv2.imshow('Frame', frame)

            # # Wait for a key press and then exit if the 'q' key is pressed
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

            time.sleep(5)
        cams.update_one(camera, {'$set': {'status': 'false'}})
        stream.stop()
    except Exception as e: 
        logger.info(e)
        cams.update_one(camera, {'$set': {'status': 'false'}})
    sessions.insert_one(class_session)
    
        

