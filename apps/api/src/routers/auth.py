import sys, hashlib, os, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

load_dotenv()
router = APIRouter(prefix="/api/auth", tags=["auth"])

def _col(name):
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured. Set MONGODB_URI in environment.",
        )
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db_name = os.environ.get("MONGODB_DB", "career_recommender")
        return client[db_name][name]
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Database is unavailable")

def _hash(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

class SignupRequest(BaseModel):
    username: str   # used as user_id
    email: str
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    user_id: str
    token: str
    full_name: str
    email: str

@router.post("/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    try:
        users = _col("auth_users")
        if users.find_one({"username": req.username}):
            raise HTTPException(400, "Username already taken")
        if users.find_one({"email": req.email}):
            raise HTTPException(400, "Email already registered")
        salt = uuid.uuid4().hex
        token = uuid.uuid4().hex
        users.insert_one({
            "username": req.username,
            "email": req.email,
            "full_name": req.full_name,
            "salt": salt,
            "password_hash": _hash(req.password, salt),
            "token": token,
        })
        # Also create a minimal user profile in user_profiles collection
        profiles = _col("user_profiles")
        profiles.update_one(
            {"user_id": req.username},
            {"$setOnInsert": {"user_id": req.username, "manual_skills": [], "interest_tags": [], "full_name": req.full_name}},
            upsert=True
        )
        return AuthResponse(user_id=req.username, token=token, full_name=req.full_name, email=req.email)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Database is unavailable")

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    try:
        users = _col("auth_users")
        user = users.find_one({"username": req.username})
        if not user or user["password_hash"] != _hash(req.password, user["salt"]):
            raise HTTPException(401, "Invalid username or password")
        # Rotate token on login
        token = uuid.uuid4().hex
        users.update_one({"username": req.username}, {"$set": {"token": token}})
        return AuthResponse(
            user_id=req.username,
            token=token,
            full_name=user.get("full_name", ""),
            email=user.get("email", ""),
        )
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Database is unavailable")

@router.get("/me")
def me_from_token(token: str):
    try:
        users = _col("auth_users")
        user = users.find_one({"token": token})
        if not user:
            raise HTTPException(401, "Invalid or expired token")
        return {"user_id": user["username"], "full_name": user.get("full_name",""), "email": user.get("email","")}
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Database is unavailable")

@router.post("/logout")
def logout(token: str):
    try:
        users = _col("auth_users")
        users.update_one({"token": token}, {"$set": {"token": ""}})
        return {"status": "ok"}
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Database is unavailable")
