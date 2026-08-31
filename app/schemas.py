"""요청 본문 검증용 Pydantic 스키마 (DRF 의 request_serializers 대체).

응답 직렬화는 `app/serializers.py` 의 함수들이 담당합니다 (계산 필드가 많아
Django 의 SerializerMethodField 와 형태를 맞추기 위함).
"""
from pydantic import BaseModel


class SignUpRequest(BaseModel):
    username: str
    password: str


class SignInRequest(BaseModel):
    username: str
    password: str


class UserProfileUpdateRequest(BaseModel):
    profilepic_id: int | None = None
    nickname: str | None = None


class PointDeductRequest(BaseModel):
    point_to_deduct: int | None = None


class CheckUsernameRequest(BaseModel):
    username: str | None = None


class PointCreateRequest(BaseModel):
    price: str | None = None
    point: int | None = None


class PayReadyRequest(BaseModel):
    partner_order_id: str
    partner_user_id: str
    item_name: str
    total_amount: int


class PayApproveRequest(BaseModel):
    pg_token: str
    tid: str
