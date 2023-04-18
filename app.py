from fastapi import FastAPI

myapp = FastAPI()

@myapp.get("/")
def myroot():
    return {"message" : "Welcome to AAMS"}