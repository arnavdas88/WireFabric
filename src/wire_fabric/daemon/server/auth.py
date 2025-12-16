import os
import secrets
from typing import Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv

load_dotenv()

security = HTTPBasic()

def load_users() -> Dict[str, Dict]:
    users = {}
    raw = os.getenv("FABRIC_USERS", "")
    for entry in raw.split(","):
        if not entry.strip():
            continue
        username, password, role = entry.split(":")
        users[username] = {
            "password": password,
            "role": role
        }
    return users

USERS = load_users()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    user = USERS.get(credentials.username)
    if not user or not secrets.compare_digest(
        credentials.password, user["password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"username": credentials.username, "role": user["role"]}

def require_role(*allowed_roles):
    def checker(user=Depends(authenticate)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges"
            )
        return user
    return checker
