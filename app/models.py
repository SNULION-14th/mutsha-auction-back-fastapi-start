"""SQLModel 테이블 정의 (Django `models.py` 4개 앱을 한 파일로 통합).

Django 의 기본 `User` 모델을 직접 정의하고, 나머지는 원본 Django 모델과
필드/관계를 1:1로 맞췄습니다.
"""
from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """Django `django.contrib.auth.models.User` 를 대체하는 사용자 계정."""

    __tablename__ = "user_account"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=150)
    password: str  # 해시된 비밀번호
    is_active: bool = True

    profile: "UserProfile" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False},
    )


class UserProfile(SQLModel, table=True):
    """Django `UserProfile` (User 와 OneToOne)."""

    __tablename__ = "user_profile"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user_account.id", unique=True)
    profilepic_id: int | None = None
    nickname: str | None = Field(default=None, max_length=256)
    remaining_points: int = 0
    is_social_login: bool = False

    user: User = Relationship(back_populates="profile")


class Auction(SQLModel, table=True):
    """경매 (Django `Auction`)."""

    __tablename__ = "auction"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: str
    starting_price: int
    current_price: int = 0
    image_url: str | None = None
    image_file: str | None = None  # media 기준 상대 경로 (예: auction_images/foo.png)

    status: str = "active"  # active / ended / cancelled

    start_time: datetime = Field(default_factory=utcnow)
    end_time: datetime

    seller_id: int = Field(foreign_key="user_account.id")
    winner_id: int | None = Field(default=None, foreign_key="user_account.id")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    seller: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Auction.seller_id"}
    )
    winner: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Auction.winner_id"}
    )
    bids: list["Bid"] = Relationship(
        back_populates="auction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def is_active(self) -> bool:
        """경매가 진행중인지 확인 (Django 의 @property is_active 와 동일)."""
        return self.status == "active" and utcnow() < _aware(self.end_time)

    @property
    def time_remaining(self):
        if self.is_active:
            return _aware(self.end_time) - utcnow()
        return None


class Bid(SQLModel, table=True):
    """입찰 (Django `Bid`)."""

    __tablename__ = "bid"

    id: int | None = Field(default=None, primary_key=True)
    auction_id: int = Field(foreign_key="auction.id")
    bidder_id: int = Field(foreign_key="user_account.id")
    amount: int
    bid_time: datetime = Field(default_factory=utcnow)

    auction: Auction = Relationship(back_populates="bids")
    bidder: User = Relationship()


class Point(SQLModel, table=True):
    """포인트 상품 (Django `Point`)."""

    __tablename__ = "point"

    id: int | None = Field(default=None, primary_key=True)
    price: str = Field(max_length=256)
    point: int


class Payment(SQLModel, table=True):
    """카카오페이 결제 내역 (Django `Payment`)."""

    __tablename__ = "payment"

    id: int | None = Field(default=None, primary_key=True)
    tid: str = Field(max_length=100)
    partner_order_id: str = Field(max_length=100)
    partner_user_id: str = Field(max_length=100)
    point: int = 0
    price: int = 0
    pay_status: str = Field(default="ready", max_length=100)
    approved_at: datetime | None = None
    user_id: int | None = Field(default=None, foreign_key="user_account.id")

    user: User | None = Relationship()


def _aware(dt: datetime) -> datetime:
    """SQLite 에서 읽어온 naive datetime 을 UTC aware 로 보정."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
