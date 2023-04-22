from face_detector import Detector
import cv2
from pymongo import MongoClient
import numpy as np
# create a MongoClient object and connect to the MongoDB server
client = MongoClient('mongodb://localhost:27017/')

# access the database
db = client['testx']

# access the collection
collection = db['faces']

# create a document to insert into the collection


# insert the document into the collection


cap = cv2.VideoCapture(r"C:\\Users\\shrav\\Desktop\\Threshold\\input.mp4")
detector = Detector()
frame_num  =0 
while True:
    ret, frame = cap.read()
    print(cap.get(cv2.CAP_PROP_POS_FRAMES))
    if cap.get(cv2.CAP_PROP_POS_FRAMES) % 30 != 0:
        continue
    print(frame_num)
    
    detector.current_frame_faces = []
    detector.face_crop_frames = []
    detector.face_coordiantes = []
    detector.get_embeddings(frame)
    cursor = collection.find()
    # iterate over the cursor and print each document
    field_list = {}

    # for id ,x in enumerate(detector.current_frame_people[0]):
    #     doc = {'id': id, 'face': x.tolist(),'bbox':detector.face_coordiantes[id]}
    #         # insert the document into the collection
    #     result = collection.insert_one(doc)
    
    # for id, i in enumerate(detector.face_coordiantes):
    #     text = id
    #     org = (i['x1']-5,i['y1']-5)
    #     font = cv2.FONT_HERSHEY_SIMPLEX
    #     fontScale = 1
    #     color = (255, 0, 0)
    #     thickness = 2
    #     cv2.putText(frame, str(text), org, font, fontScale, color, thickness)
    #     cv2.rectangle(frame,(i['x1'],i['y1']),(i['x2'],i['y2']),(0,255,0),2)
    # cv2.imshow("i",frame)
    # cv2.waitKey(1)

    for document in cursor:
        field_list[document['id']] = [document['face'], document['bbox']]


    for index , x in enumerate(detector.current_frame_people[0]):
        most = -1
        person_id = -1
        for id, y in field_list.items():
            highest = detector.check_similarity_with_database(x, y[0])
            highest = (1-highest)*100
            if most < highest and highest >= 50.0:
                most = highest
                person_id = id
            print(highest)
        if person_id!= -1:
            i = field_list[person_id][1]
            text = person_id
            org = (i['x1']-5,i['y1']-5)
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            color = (255, 0, 0)
            thickness = 2
            cv2.putText(frame, str(text), org, font, fontScale, color, thickness)
            cv2.rectangle(frame,(i['x1'],i['y1']),(i['x2'],i['y2']),(0,255,0),2)
            detector.present_in_class.append(person_id)
            detector.frames.append(frame)
            del field_list[person_id]
    cv2.imshow("i",frame)
    cv2.waitKey(1)
    frame+=1
