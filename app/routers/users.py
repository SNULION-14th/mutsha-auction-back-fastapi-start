"""사용자/인증 라우터 (Django `UserProfile/views.py` + `urls.py`).

쿠키 기반 JWT 인증을 원본과 동일한 쿠키 이름/형식으로 재현하여,
프론트엔드(axios withCredentials + 401 refresh 인터셉터)가 그대로 동작합니다.
"""
import jwt
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.security import (
    blacklist_token,
    clear_auth_cookies,
    decode_token,
    hash_password,
    set_access_cookie,
    set_auth_cookies,
    verify_password,
)
from app.models import User, UserProfile
from app.schemas import (
    CheckUsernameRequest,
    PointDeductRequest,
    SignInRequest,
    SignUpRequest,
    UserProfileUpdateRequest,
)
from app.serializers import serialize_userprofile, serialize_userprofile_for_update

router = APIRouter(prefix="/api/user", tags=["user"])


def _auth_response(session: Session, user: User, status_code: int) -> JSONResponse:
    """set_token_on_response_cookie 대응: 프로필 본문 + access/refresh 쿠키."""
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user.id)
    ).first()
    res = JSONResponse(serialize_userprofile(session, profile), status_code=status_code)
    set_auth_cookies(res, user.id)
    return res


@router.post("/signup/")
def signup(body: SignUpRequest, session: Session = Depends(get_session)):
    exists = session.exec(select(User).where(User.username == body.username)).first()
    if exists:
        return JSONResponse(
            {"username": ["A user with that username already exists."]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    user = User(username=body.username, password=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)

    session.add(UserProfile(user_id=user.id))
    session.commit()

    return _auth_response(session, user, status.HTTP_201_CREATED)


@router.post("/signin/")
def signin(body: SignInRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == body.username)).first()
    if user is None:
        return JSONResponse(
            {"message": "User not found"}, status_code=status.HTTP_404_NOT_FOUND
        )
    if not verify_password(body.password, user.password):
        return JSONResponse(
            {"message": "Invalid password"}, status_code=status.HTTP_401_UNAUTHORIZED
        )
    return _auth_response(session, user, status.HTTP_200_OK)


@router.post("/refresh/")
def token_refresh(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return JSONResponse(
            {"detail": "no refresh token"}, status_code=status.HTTP_400_BAD_REQUEST
        )
    try:
        payload = decode_token(refresh_token)
        if payload.get("token_type") != "refresh":
            raise jwt.InvalidTokenError()
    except jwt.PyJWTError:
        return JSONResponse(
            {"detail": "please signin again."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    res = JSONResponse({"detail": "token refreshed"}, status_code=status.HTTP_200_OK)
    set_access_cookie(res, payload["user_id"])
    return res


@router.post("/signout/", status_code=status.HTTP_204_NO_CONTENT)
def signout(request: Request, user: User = Depends(get_current_user)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return JSONResponse(
            {"detail": "no refresh token"}, status_code=status.HTTP_400_BAD_REQUEST
        )
    blacklist_token(refresh_token)
    res = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(res)
    return res


@router.get("/userinfo/")
def userprofile_list(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    profiles = session.exec(select(UserProfile)).all()
    return [serialize_userprofile(session, p) for p in profiles]


@router.get("/me/")
def userprofile_detail(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user.id)
    ).first()
    if profile is None:
        return JSONResponse(
            {"detail": "UserProfile Not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return serialize_userprofile(session, profile)


@router.put("/me/")
def userprofile_update(
    body: UserProfileUpdateRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user.id)
    ).first()
    if profile is None:
        return JSONResponse(
            {"detail": "UserProfile Not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if not body.profilepic_id or not body.nickname:
        return JSONResponse(
            {"detail": "[profilepic_id, nickname] fields missing."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    profile.profilepic_id = body.profilepic_id
    profile.nickname = body.nickname
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return serialize_userprofile_for_update(session, profile)


@router.put("/pointreduce/")
def remaining_point_deduct(
    body: PointDeductRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user.id)
    ).first()
    if profile is None:
        return JSONResponse(
            {"detail": "UserProfile Not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if not body.point_to_deduct:
        return JSONResponse(
            {"detail": "point_to_deduct field missing."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if profile.remaining_points < body.point_to_deduct:
        return JSONResponse(
            {"detail": "Not enough points."}, status_code=status.HTTP_400_BAD_REQUEST
        )
    profile.remaining_points -= body.point_to_deduct
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return serialize_userprofile_for_update(session, profile)


@router.post("/check/")
def check_username(body: CheckUsernameRequest, session: Session = Depends(get_session)):
    exists = session.exec(select(User).where(User.username == body.username)).first()
    if exists:
        return JSONResponse(
            {"message": "Username already exists"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return {"message": "Username is available"}


@router.api_route("/kakao/callback/", methods=["GET", "POST"])
async def kakao_callback(request: Request, session: Session = Depends(get_session)):
    """카카오 간편 로그인. code 로 카카오 access_token → 유저 정보 → 자체 토큰 발급."""
    import httpx

    code = request.query_params.get("code")
    token_uri = (
        "https://kauth.kakao.com/oauth/token?grant_type=authorization_code"
        f"&client_id={settings.KAKAO_SECRET_KEY}"
        f"&redirect_uri={settings.KAKAO_REDIRECT_URI}&code={code}"
    )
    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_uri)
        access_token = token_res.json().get("access_token")
        info_res = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    user_info = info_res.json()
    kakao_username = str(user_info.get("id"))

    user = session.exec(select(User).where(User.username == kakao_username)).first()
    if user is None:
        user = User(
            username=kakao_username, password=hash_password("social_login_password")
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(UserProfile(user_id=user.id, is_social_login=True))
        session.commit()

    return _auth_response(session, user, status.HTTP_200_OK)
