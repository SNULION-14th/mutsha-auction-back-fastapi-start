"""응답 직렬화 함수 (Django REST Framework serializers 의 to_representation 대체).

계산 필드(time_remaining, bid_count, image_file_url, seller_nickname 등)를
원본 DRF 응답과 동일한 키/형태로 만들어 프론트엔드 호환성을 유지합니다.
"""
from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Auction, Bid, User, UserProfile


# --------------------------------------------------------------------------- #
# 공통 헬퍼
# --------------------------------------------------------------------------- #
def _media_url(base_url: str | None, image_file: str | None) -> str | None:
    if not image_file:
        return None
    path = f"/media/{image_file.lstrip('/')}"
    if base_url:
        return base_url.rstrip("/") + path
    return path


def _profile_of(session: Session, user_id: int) -> UserProfile | None:
    return session.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).first()


def _bid_count(session: Session, auction_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(Bid).where(Bid.auction_id == auction_id)
    ).one()


# --------------------------------------------------------------------------- #
# User / UserProfile
# --------------------------------------------------------------------------- #
def serialize_user(user: User) -> dict:
    return {"id": user.id, "username": user.username}


def serialize_userprofile(session: Session, profile: UserProfile) -> dict:
    user = session.get(User, profile.user_id)
    return {
        "id": profile.id,
        "user": serialize_user(user) if user else None,
        "profilepic_id": profile.profilepic_id,
        "nickname": profile.nickname,
        "remaining_points": profile.remaining_points,
        "is_social_login": profile.is_social_login,
    }


def serialize_userprofile_for_update(session: Session, profile: UserProfile) -> dict:
    user = session.get(User, profile.user_id)
    return {
        "user": serialize_user(user) if user else None,
        "nickname": profile.nickname,
        "profilepic_id": profile.profilepic_id,
        "remaining_points": profile.remaining_points,
    }


# --------------------------------------------------------------------------- #
# Auction
# --------------------------------------------------------------------------- #
def serialize_auction(
    session: Session, auction: Auction, base_url: str | None = None
) -> dict:
    """AuctionSerializer 에 대응 (경매 상세)."""
    seller_profile = _profile_of(session, auction.seller_id)
    return {
        "id": auction.id,
        "title": auction.title,
        "description": auction.description,
        "starting_price": auction.starting_price,
        "current_price": auction.current_price,
        "image_url": auction.image_url,
        "image_file": _media_url(base_url, auction.image_file),
        "image_file_url": _media_url(base_url, auction.image_file),
        "status": auction.status,
        "start_time": auction.start_time.isoformat() if auction.start_time else None,
        "end_time": auction.end_time.isoformat() if auction.end_time else None,
        "seller": auction.seller_id,
        "seller_nickname": seller_profile.nickname if seller_profile else None,
        "seller_profile_image": seller_profile.profilepic_id if seller_profile else None,
        "winner": auction.winner_id,
        "created_at": auction.created_at.isoformat() if auction.created_at else None,
        "updated_at": auction.updated_at.isoformat() if auction.updated_at else None,
        "time_remaining": str(auction.time_remaining),
        "is_active": auction.is_active,
        "bid_count": _bid_count(session, auction.id),
    }


def serialize_auction_list_item(
    session: Session, auction: Auction, base_url: str | None = None
) -> dict:
    """AuctionListSerializer 에 대응 (경매 목록)."""
    seller_profile = _profile_of(session, auction.seller_id)
    return {
        "id": auction.id,
        "title": auction.title,
        "description": auction.description,
        "starting_price": auction.starting_price,
        "current_price": auction.current_price,
        "image_url": auction.image_url,
        "image_file": _media_url(base_url, auction.image_file),
        "image_file_url": _media_url(base_url, auction.image_file),
        "status": auction.status,
        "end_time": auction.end_time.isoformat() if auction.end_time else None,
        "seller_nickname": seller_profile.nickname if seller_profile else None,
        "seller_profile_image": seller_profile.profilepic_id if seller_profile else None,
        "time_remaining": str(auction.time_remaining),
        "is_active": auction.is_active,
        "bid_count": _bid_count(session, auction.id),
    }


def serialize_my_auction_history(
    session: Session, auction: Auction, base_url: str | None = None
) -> dict:
    """MyAuctionHistorySerializer 에 대응."""
    return {
        "auction_id": auction.id,
        "title": auction.title,
        "current_price": auction.current_price,
        "start_price": auction.starting_price,
        "end_time": auction.end_time.isoformat() if auction.end_time else None,
        "status": auction.status,
        "image_url": auction.image_url,
        "image_file": _media_url(base_url, auction.image_file),
        "image_file_url": _media_url(base_url, auction.image_file),
    }


def serialize_my_bid_history(
    session: Session, auction: Auction, user: User, base_url: str | None = None
) -> dict:
    """MyBidHistorySerializer 에 대응."""
    user_bid = session.exec(
        select(Bid)
        .where(Bid.auction_id == auction.id, Bid.bidder_id == user.id)
        .order_by(Bid.amount.desc())
    ).first()
    return {
        "auction_id": auction.id,
        "title": auction.title,
        "status": auction.status,
        "current_price": auction.current_price,
        "my_bid": user_bid.amount if user_bid else 0,
        "end_time": auction.end_time.isoformat() if auction.end_time else None,
        "is_winner": auction.status == "ended" and auction.winner_id == user.id,
        "image_url": auction.image_url,
        "image_file": _media_url(base_url, auction.image_file),
        "image_file_url": _media_url(base_url, auction.image_file),
    }
