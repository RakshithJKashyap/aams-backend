from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schema import User
import os
import cloudinary
import cloudinary.uploader
from db import DBConnect
import time
from dotenv import load_dotenv

load_dotenv()
myapp = FastAPI()

cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

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
