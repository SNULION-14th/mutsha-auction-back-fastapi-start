"""인증/보안 유틸 (JWT 발급·검증, 비밀번호 해시, 쿠키 세팅).

Django 의 `rest_framework_simplejwt` + `django.contrib.auth.hashers` 역할을
직접 구현합니다. 프론트엔드와의 호환을 위해 쿠키 이름/속성을 원본과 동일하게 맞췄습니다.
- access_token / refresh_token 쿠키 (httponly=False, samesite=Lax, secure=False)
"""
import uuid
from datetime import datetime, timezone

import bcrypt
import jwt
from fastapi import Response

from app.core.config import settings

# 로그아웃 시 무효화된 refresh 토큰의 jti 를 저장 (simplejwt 의 blacklist 대체).
# 데모용 인메모리 저장소입니다. 서버 재시작 시 초기화됩니다.
_blacklisted_jti: set[str] = set()


# --------------------------------------------------------------------------- #
# 비밀번호 해시
# --------------------------------------------------------------------------- #
def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()


def verify_password(raw_password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode(), hashed.encode())
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def _create_token(user_id: int, token_type: str, lifetime) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "token_type": token_type,
        "exp": now + lifetime,
        "iat": now,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(user_id, "access", settings.access_token_lifetime)


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, "refresh", settings.refresh_token_lifetime)


def decode_token(token: str) -> dict:
    """토큰을 검증하고 payload 를 반환. 실패 시 jwt 예외를 던집니다."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def blacklist_token(token: str) -> None:
    try:
        payload = decode_token(token)
        _blacklisted_jti.add(payload.get("jti", ""))
    except jwt.PyJWTError:
        pass


def is_blacklisted(payload: dict) -> bool:
    return payload.get("jti", "") in _blacklisted_jti


# --------------------------------------------------------------------------- #
# 쿠키
# --------------------------------------------------------------------------- #
def set_auth_cookies(response: Response, user_id: int) -> None:
    """access + refresh 토큰을 쿠키에 실어 보냅니다 (signup/signin 시)."""
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    response.set_cookie(
        "access_token", access, httponly=False, samesite="lax", secure=False
    )
    response.set_cookie(
        "refresh_token", refresh, httponly=False, samesite="lax", secure=False
    )


def set_access_cookie(response: Response, user_id: int) -> None:
    """access 토큰만 새로 발급 (refresh 시)."""
    access = create_access_token(user_id)
    response.set_cookie(
        "access_token", access, httponly=False, samesite="lax", secure=False
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
