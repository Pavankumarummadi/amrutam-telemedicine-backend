import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import Role, User, get_db

oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
def hash_password(password:str)->str:
    salt=os.urandom(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1)
    return "scrypt$16384$8$1$"+base64.urlsafe_b64encode(salt).decode()+"$"+base64.urlsafe_b64encode(digest).decode()
def verify_password(password:str, hashed:str)->bool:
    try:
        scheme,n,r,p,salt_b64,digest_b64=hashed.split("$")
        if scheme!="scrypt": return False
        salt=base64.urlsafe_b64decode(salt_b64); expected=base64.urlsafe_b64decode(digest_b64)
        actual=hashlib.scrypt(password.encode(),salt=salt,n=int(n),r=int(r),p=int(p))
        return hmac.compare_digest(actual,expected)
    except (ValueError, TypeError): return False
def create_token(user:User)->str:
    exp=datetime.now(timezone.utc)+timedelta(minutes=get_settings().jwt_expire_minutes)
    return jwt.encode({"sub":str(user.id),"role":user.role.value,"exp":exp}, get_settings().jwt_secret, algorithm="HS256")
def current_user(token:str=Depends(oauth2_scheme), db:Session=Depends(get_db))->User:
    exc=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials", headers={"WWW-Authenticate":"Bearer"})
    try: uid=int(jwt.decode(token,get_settings().jwt_secret,algorithms=["HS256"])["sub"])
    except (JWTError, KeyError, ValueError): raise exc
    user=db.get(User,uid)
    if not user or not user.is_active: raise exc
    return user
def require_roles(*roles:Role):
    def dep(user:User=Depends(current_user)):
        if user.role not in roles: raise HTTPException(403,"Insufficient permissions")
        return user
    return dep
