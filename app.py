from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schema import User
import os
import cloudinary
import cloudinary.uploader
from db import DBConnect
import time
from dotenv import load_dotenv
from celery import Celery

load_dotenv()
myapp = FastAPI()

cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")
redis = os.getenv("REDIS")
mongodb = os.getenv("MONGODB_URI")

celery = Celery(__name__, broker=redis, backend=mongodb)


cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
)

origins = ["*"]
myapp.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@myapp.get("/")
def myroot():
    return {"message": "Welcome to AAMS"}


@myapp.get("/test", tags=["status"])
def test():
    r = celery.send_task('health_check')
    return {"status": "ok", "task_id": r.id, "task_status": r.status}

@myapp.post("/first_register")
def first_register(
    auth0_token: str,
    username: str,
    email: str,
    usn: str,
    name: str,
    sem: str,
    section: str,
    role: str,
    branch: str,
    photo: UploadFile = File(...),
):
    client = DBConnect()

    existing_username = client["users"].find_one({"username": username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")

    existing_email = client["users"].find_one({"email": email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    existing_usn = client["users"].find_one({"usn": usn})
    if existing_usn:
        raise HTTPException(status_code=400, detail="USN already exists")
    try:
        upload_result = cloudinary.uploader.upload(photo.file, folder=username)
        print("Photo uploaded successfully")
    except Exception as e:
        print("Error: ", e)
        raise HTTPException(status_code=400, detail="Photo upload failed")

    photo_url = upload_result["url"]

    user_dict = {
        "_id": username,
        "auth0_token": auth0_token,
        "username": username,
        "name": name,
        "email": email,
        "sem": sem,
        "branch": branch,
        "usn": usn,
        "photo_url": photo_url,
        "section": section,
        "role": role,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }

    try:
        output = client["users"].insert_one(user_dict)
        celery.send_task('first_register', args=[photo_url, auth0_token])
    except Exception as e:
        raise HTTPException(status_code=400, detail="User registration failed")

    return {"message": "User registered successfully"}


@myapp.get("/get_user")
def get_user(auth0_token: str):
    client = DBConnect()
    if client == "error":
        raise HTTPException(status_code=400, detail="Database connection failed")

    user = client["users"].find_one({"auth0_token": auth0_token})
    if not user:
        return {"message": "User not found", "status": "failed"}

    return {"message": "User found", "status": "success", "type": user["role"]}


@myapp.post("/add_cameras")
def add_cameras(class_name: str, ip_address: str):
    client = DBConnect()
    if client == "error":
        raise HTTPException(status_code=400, detail="Database connection failed")

    # Check if camera with the same class_name or ip_address already exists
    existing_camera = client["camera"].find_one({"$or": [{"class_name": class_name}, {"ip_address": ip_address}]})
    if existing_camera:
        raise HTTPException(status_code=400, detail="Camera with the same class_name or ip_address already exists")

    # Insert the new camera
    new_camera = client["camera"].insert_one({"class_name": class_name, "ip_address": ip_address})
    if not new_camera:
        return {"message": "Camera not added", "status": "failed"}
    else:
        return {"message": "Camera added", "status": "success"}



@myapp.delete("/delete_camera/{class_name}")
def delete_camera(class_name: str):
    client = DBConnect()
    if client == "error":
        raise HTTPException(status_code=400, detail="Database connection failed")

    result = client["camera"].delete_one({"class_name": class_name})
    if result.deleted_count == 1:
        return {"message": "Camera deleted", "status": "success"}
    else:
        return {"message": "Camera not found", "status": "failed"}

    
@myapp.get("/get_cameras")
def get_cameras():
    client = DBConnect()
    if client == "error":
        raise HTTPException(status_code=400, detail="Database connection failed")

    cameras = []
    for camera in client["camera"].find():
        cameras.append({"class_name": camera["class_name"], "ip_address": camera["ip_address"]})

    return cameras


@myapp.get("/start_detection")
def start_detection(camera_id:str):
    celery.send_task('start_attendance',args=[camera_id])
