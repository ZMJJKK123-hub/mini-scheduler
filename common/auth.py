from common.db import create_user_db, get_user_by_username, authenticate_user_db
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status, Request

# 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345678")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24小时
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    is_active: bool = True

def verify_password(plain_password, stored_password):
    """简单密码验证"""
    return plain_password == stored_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """验证 token 并返回用户名"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

# 用户数据库（已迁移到 SQLite 数据库）
# fake_users_db = {
#     DEFAULT_USERNAME: {
#         "username": DEFAULT_USERNAME,
#         "full_name": "Admin User",
#         "email": "admin@example.com",
#         "password": DEFAULT_PASSWORD,
#         "disabled": False,
#     }
# }

def authenticate_user(username: str, password: str):
    """认证用户"""
    user = fake_users_db.get(username)
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user


def create_user(username: str, password: str) -> tuple[bool, str]:
    """创建新用户（保存到数据库）"""
    if not username or len(username) < 3:
        return False, "用户名太短（至少3个字符）"
    if not password or len(password) < 6:
        return False, "密码太短（至少6个字符）"
    
    return create_user_db(username, password)


def authenticate_user(username: str, password: str):
    """认证用户（从数据库验证）"""
    return authenticate_user_db(username, password)

def get_current_user(token: str) -> User:
    """从 token 获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的身份验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = verify_token(token)
    if username is None:
        raise credentials_exception
    
    user_data = get_user_by_username(username)
    if user_data is None:
        raise credentials_exception
    
    return User(username=user_data["username"], is_active=not user_data.get("disabled", False))

# 依赖函数：从 HTTP Bearer token 中提取
async def get_current_user_from_bearer(request: Request):
    """从 HTTP Bearer 获取当前用户"""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header:
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError()
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证头格式",
            )
    else:
        # fallback to cookie so browser page loads can validate via fetch(..., {credentials:'include'})
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少身份验证凭证",
        )

    return get_current_user(token)
