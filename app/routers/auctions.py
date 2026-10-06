"""경매 라우터 (Django `Auction/views.py` + `urls.py`).

경로/응답 형태를 원본과 1:1로 맞춰 기존 프론트엔드가 그대로 동작합니다.
- 실시간 입찰은 웹소켓(app/realtime/ws.py)이 담당하지만,
  호환성을 위해 HTTP 입찰 엔드포인트(/bid/)도 남겨두었습니다.
- 경매 생성 시 SSE 브로커로 '새 경매 등록' 전역 알림을 발행합니다.
"""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models import Auction, User, utcnow
from app.serializers import (
    serialize_auction,
    serialize_auction_list_item,
    serialize_my_auction_history,
    serialize_my_bid_history,
)
from app.services import BidError, close_expired_auctions, place_bid

router = APIRouter(prefix="/api/auction", tags=["auction"])


def _parse_end_time(value: str) -> datetime:
    # 프론트가 보내는 ISO 문자열(끝에 Z 가 붙을 수 있음)을 파싱
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.get("/recommended/")
def recommended_auctions(
    request: Request, session: Session = Depends(get_session)
):
    """오늘의 추천 경매: 진행중 경매 중 랜덤 2개."""
    auctions = session.exec(
        select(Auction)
        .where(Auction.status == "active", Auction.end_time > utcnow())
        .order_by(func.random())
        .limit(2)
    ).all()
    base = str(request.base_url)
    return [serialize_auction_list_item(session, a, base) for a in auctions]


@router.get("/")
def auction_list(request: Request, session: Session = Depends(get_session)):
    """경매 목록 (status / search 쿼리 지원)."""
    close_expired_auctions(session)

    query = select(Auction)
    status_filter = request.query_params.get("status")
    if status_filter:
        query = query.where(Auction.status == status_filter)
    search = request.query_params.get("search")
    if search:
        like = f"%{search}%"
        query = query.where(
            Auction.title.ilike(like) | Auction.description.ilike(like)
        )
    query = query.order_by(Auction.created_at.desc())

    auctions = session.exec(query).all()
    base = str(request.base_url)
    return [serialize_auction_list_item(session, a, base) for a in auctions]


@router.post("/create/", status_code=status.HTTP_201_CREATED)
async def create_auction(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """경매 생성. JSON 또는 multipart(form-data, 이미지 첨부) 모두 지원."""
    content_type = request.headers.get("content-type", "")
    image_relpath: str | None = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        title = form.get("title")
        description = form.get("description")
        starting_price = form.get("starting_price")
        end_time = form.get("end_time")
        image_url = form.get("image_url")
        upload = form.get("image_file")
        if upload is not None and hasattr(upload, "filename") and upload.filename:
            ext = Path(upload.filename).suffix
            fname = f"{uuid.uuid4().hex}{ext}"
            dest_dir = Path(settings.MEDIA_ROOT) / "auction_images"
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / fname).write_bytes(await upload.read())
            image_relpath = f"auction_images/{fname}"
    else:
        body = await request.json()
        title = body.get("title")
        description = body.get("description")
        starting_price = body.get("starting_price")
        end_time = body.get("end_time")
        image_url = body.get("image_url")

    # --- 검증 (AuctionCreateSerializer) ---
    if not all([title, description, starting_price, end_time]):
        return JSONResponse(
            {"detail": "필수 필드가 누락되었습니다."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        end_dt = _parse_end_time(str(end_time))
    except ValueError:
        return JSONResponse(
            {"end_time": ["올바른 날짜 형식이 아닙니다."]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if end_dt <= utcnow():
        return JSONResponse(
            {"end_time": ["종료 시간은 현재 시간보다 늦어야 합니다."]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    auction = Auction(
        title=str(title),
        description=str(description),
        starting_price=int(starting_price),
        image_url=str(image_url) if image_url else None,
        image_file=image_relpath,
        end_time=end_dt,
        seller_id=user.id,
    )
    session.add(auction)
    session.commit()
    session.refresh(auction)

    data = serialize_auction(session, auction, str(request.base_url))

    # TODO(실습): 여기서 SSE 브로커로 '새 경매 등록' 전역 알림을 발행하세요.

    return data


@router.get("/my-auctions/")
def my_auction_history(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    auctions = session.exec(
        select(Auction).where(Auction.seller_id == user.id).order_by(Auction.created_at.desc())
    ).all()
    base = str(request.base_url)
    return [serialize_my_auction_history(session, a, base) for a in auctions]


@router.get("/my-bids/")
def my_bid_history(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    from app.models import Bid

    auction_ids = session.exec(
        select(Bid.auction_id).where(Bid.bidder_id == user.id).distinct()
    ).all()
    auctions = session.exec(
        select(Auction).where(Auction.id.in_(auction_ids)).order_by(Auction.updated_at.desc())
    ).all()
    base = str(request.base_url)
    return [serialize_my_bid_history(session, a, user, base) for a in auctions]


@router.post("/{auction_id}/bid/", status_code=status.HTTP_201_CREATED)
async def bid_create(
    auction_id: int,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """HTTP 입찰(호환용 fallback). 성공 시 웹소켓으로도 방송합니다."""
    body = await request.json()
    amount = body.get("amount")

    try:
        auction = place_bid(session, auction_id, user, amount)
    except BidError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    data = serialize_auction(session, auction, str(request.base_url))

    # TODO(실습): 입찰 성공 후, 경매방(WebSocket)에 최신 정보를 방송하세요.

    return data


@router.get("/{auction_id}/")
def auction_detail(
    auction_id: int, request: Request, session: Session = Depends(get_session)
):
    auction = session.get(Auction, auction_id)
    if auction is None:
        raise HTTPException(status_code=404, detail="경매를 찾을 수 없습니다.")

    # 종료 시간이 지났으면 종료 처리 + 낙찰자 지정
    from app.models import Bid, _aware

    if auction.status == "active" and _aware(auction.end_time) < utcnow():
        auction.status = "ended"
        highest = session.exec(
            select(Bid).where(Bid.auction_id == auction.id).order_by(Bid.amount.desc())
        ).first()
        if highest:
            auction.winner_id = highest.bidder_id
        session.add(auction)
        session.commit()
        session.refresh(auction)

    return serialize_auction(session, auction, str(request.base_url))
