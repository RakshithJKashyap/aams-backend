from pydantic import BaseModel


class User(BaseModel):
    name: str
    username: str
    email: str
    usn: str
    sem: str
    branch: str
    section: str
    role: str = None
    created_at: int = None
    updated_at: int = None

    class Config:
        orm_mode = True
