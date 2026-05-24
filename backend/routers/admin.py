"""
Admin API — endpoints for managing admin users.
Only existing admins can add/remove other admins.
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from backend.auth import RequiredUser
from backend import metrics_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class AddAdminRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Email is required")
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v


@router.get("/check/{email}")
def check_admin_status(email: str):
    """
    Check if an email is in the admin list. Public endpoint for pre-login check.
    """
    email = email.strip().lower()
    if not email or not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    is_admin = metrics_db.is_admin(email)
    return {"email": email, "is_admin": is_admin}


@router.get("/users")
def list_admin_users(user: RequiredUser):
    """
    List all admin users. Only accessible by admins.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    admins = metrics_db.list_admins()
    return {"admins": admins}


@router.post("/users")
def add_admin_user(body: AddAdminRequest, user: RequiredUser):
    """
    Add a new admin user. Only accessible by admins.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success = metrics_db.add_admin(body.email)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add admin user")
    
    return {"ok": True, "email": body.email}


@router.delete("/users/{email}")
def remove_admin_user(email: str, user: RequiredUser):
    """
    Remove an admin user. Only accessible by admins.
    Cannot remove yourself.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if email.lower().strip() == user.email.lower().strip():
        raise HTTPException(status_code=400, detail="Cannot remove yourself as admin")
    
    success = metrics_db.remove_admin(email)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove admin user")
    
    return {"ok": True, "email": email}
