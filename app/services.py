"""도메인 로직 (뷰/컨슈머가 공유하는 순수 비즈니스 로직).

- close_expired_auctions: 종료 시간이 지난 경매를 'ended' 로 바꾸고 낙찰자 지정
- place_bid: 입찰 처리 (검증 + 저장 + current_price 갱신)

place_bid 는 HTTP 입찰(fallback)과 웹소켓 입찰 양쪽에서 재사용됩니다.
"""
from app.models import Auction, Bid, User, utcnow
from app.models import _aware
from sqlmodel import Session, select


class BidError(Exception):
    """입찰 실패를 status_code 와 함께 표현하는 예외."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def close_expired_auctions(session: Session) -> None:
    """진행중이지만 종료 시간이 지난 경매를 종료 처리 (Django 목록/상세 뷰 로직)."""
    now = utcnow()
    expired = session.exec(
        select(Auction).where(Auction.status == "active")
    ).all()
    changed = False
    for auction in expired:
        if _aware(auction.end_time) < now:
            auction.status = "ended"
            highest = session.exec(
                select(Bid)
                .where(Bid.auction_id == auction.id)
                .order_by(Bid.amount.desc())
            ).first()
            if highest:
                auction.winner_id = highest.bidder_id
            session.add(auction)
            changed = True
    if changed:
        session.commit()


def place_bid(session: Session, auction_id: int, user: User, amount: int) -> Auction:
    """입찰 처리. 성공 시 갱신된 Auction 반환, 실패 시 BidError.

    Django `BidCreateView.post` 의 검증/저장 로직과 동일합니다.
    """
    if not amount:
        raise BidError("입찰가를 입력해주세요.", 400)

    auction = session.get(Auction, auction_id)
    if auction is None:
        raise BidError("경매를 찾을 수 없습니다.", 404)

    if not auction.is_active:
        raise BidError("진행중인 경매가 아닙니다.", 400)

    if amount <= auction.current_price:
        raise BidError("현재가보다 높은 금액을 입찰해야 합니다.", 400)

    bid = Bid(auction_id=auction.id, bidder_id=user.id, amount=amount)
    session.add(bid)
    auction.current_price = amount
    auction.updated_at = utcnow()
    session.add(auction)
    session.commit()
    session.refresh(auction)
    return auction
