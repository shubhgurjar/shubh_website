from fastapi import APIRouter, Response, Request, HTTPException, status, Depends
from datetime import timedelta
import json

from config import COOKIE_NAME, ACCESS_TOKEN_EXPIRE_DAYS
from database import get_setting, set_setting
from auth import verify_password, hash_password, create_access_token, require_auth, get_token_from_request, decode_token
from models import LoginRequest, ChangePasswordRequest, AuthStatusResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status(request: Request):
    auth_enabled = get_setting("auth_enabled", "true") == "true"
    site_title = get_setting("site_title", "Shubh's Software Engineering Knowledge Hub")
    
    if not auth_enabled:
        return AuthStatusResponse(authenticated=True, auth_enabled=False, site_title=site_title)
    
    token = get_token_from_request(request)
    authenticated = False
    if token:
        payload = decode_token(token)
        if payload is not None:
            authenticated = True
            
    return AuthStatusResponse(authenticated=authenticated, auth_enabled=auth_enabled, site_title=site_title)


@router.post("/login")
def login(login_data: LoginRequest, response: Response):
    stored_hash = get_setting("password_hash")
    if not stored_hash or not verify_password(login_data.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect master password",
        )
    
    access_token = create_access_token({"sub": "owner"})
    max_age = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        samesite="lax",
    )
    return {"status": "success", "token": access_token}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "logged_out"}


@router.post("/change-password")
def change_password(data: ChangePasswordRequest, user=Depends(require_auth)):
    stored_hash = get_setting("password_hash")
    if not stored_hash or not verify_password(data.current_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current master password is incorrect",
        )
    
    set_setting("password_hash", hash_password(data.new_password))
    return {"status": "password_updated"}


@router.put("/settings")
def update_settings(payload: dict, user=Depends(require_auth)):
    if "site_title" in payload:
        set_setting("site_title", str(payload["site_title"]))
    if "auth_enabled" in payload:
        set_setting("auth_enabled", "true" if payload["auth_enabled"] else "false")
    return {"status": "settings_updated"}
