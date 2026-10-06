"""FastAPI 인증 의존성.

Django 의 `CookieJWTAuthentication` 을 대체합니다.
- 먼저 `Authorization: Bearer ...` 헤더를 확인하고,
- 없으면 `access_token` 쿠키를 확인합니다.
"""
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import decode_token, is_blacklisted
from app.models import User


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer ") :]
    return request.cookies.get("access_token")


def get_user_from_token(token: str | None, session: Session) -> User | None:
    """토큰(쿠키/헤더/웹소켓 등)에서 User 를 복원. 실패하면 None."""
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if is_blacklisted(payload):
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def get_current_user_optional(
    request: Request, session: Session = Depends(get_session)
) -> User | None:
    """로그인했으면 User, 아니면 None (익명 허용 엔드포인트용)."""
    return get_user_from_token(_extract_token(request), session)


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    """로그인 필수 엔드포인트용. 인증 실패 시 401.

    원본 Django 코드가 반환하던 `{"detail": "please signin"}` 형식을 유지합니다.
    """
    user = get_user_from_token(_extract_token(request), session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="please signin"
        )
    return user
