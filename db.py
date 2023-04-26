from pymongo import mongo_client
from dotenv import load_dotenv
import os

load_dotenv()


def DBConnect():
    client = mongo_client.MongoClient(os.getenv("MONGODB_URI"))

    try:
        client.server_info()
        print("Connected to MongoDB")
    except Exception as e:
        print("Error: ", e)
        return "error"

    return client["aams"]
