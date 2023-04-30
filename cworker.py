from celery import Celery
from pymongo import mongo_client
from dotenv import load_dotenv
import os
import urllib.request
import numpy as np
import cv2
from face_detector import Detector
import logging
import pickle
from celery.utils.log import get_task_logger
detector = Detector()

logger = get_task_logger(__name__)

load_dotenv()
reddis = os.getenv("REDIS")
mongodb = os.getenv("MONGODB_URI")

app = Celery('cworker',broker=reddis, backend=mongodb)
client = mongo_client.MongoClient(mongodb)
db = client['aams']
col = db['users']

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
        col.update_one(query, update)
        

    
    

