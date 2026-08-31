"""테스트 데이터 시드 (Django `create_test_data` management command 대체).

실행:  python -m app.seed
"""
from datetime import timedelta

from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.core.security import hash_password
from app.models import Auction, Bid, User, UserProfile, utcnow


def _get_or_create_user(session: Session, username: str) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if user:
        return user
    user = User(username=username, password=hash_password("test1234"))
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserProfile(user_id=user.id, nickname=username, remaining_points=1000000))
    session.commit()
    print(f"  ✓ 유저 생성: {username}")
    return user


def _get_or_create_auction(session: Session, title: str, seller: User, **kwargs) -> Auction:
    auction = session.exec(
        select(Auction).where(Auction.title == title, Auction.seller_id == seller.id)
    ).first()
    if auction:
        return auction
    auction = Auction(title=title, seller_id=seller.id, **kwargs)
    session.add(auction)
    session.commit()
    session.refresh(auction)
    print(f"  ✓ 경매 생성: {title} ({auction.status})")
    return auction


def run() -> None:
    create_db_and_tables()
    now = utcnow()
    with Session(engine) as session:
        print("테스트 데이터 생성 시작...")
        seller = _get_or_create_user(session, "test_seller")
        bidder = _get_or_create_user(session, "test_bidder")
        competitor = _get_or_create_user(session, "test_competitor")

        _get_or_create_auction(
            session, "[판매] 아이폰 15 Pro", seller,
            description="새 제품입니다. 직거래 가능합니다.",
            starting_price=500000, current_price=850000,
            status="active", end_time=now + timedelta(days=2),
        )
        _get_or_create_auction(
            session, "[판매] 맥북 프로 M3", seller,
            description="1년 사용, 거의 새 제품입니다.",
            starting_price=1000000, current_price=1200000,
            status="active", end_time=now + timedelta(days=5),
        )
        _get_or_create_auction(
            session, "[판매] 에어팟 프로 2", seller,
            description="미개봉 새 제품입니다.",
            starting_price=150000, current_price=200000,
            status="ended", end_time=now - timedelta(days=1), winner_id=competitor.id,
        )
        auction4 = _get_or_create_auction(
            session, "갤럭시 S24 Ultra", competitor,
            description="완전 새 제품, 미개봉입니다.",
            starting_price=800000, current_price=950000,
            status="active", end_time=now + timedelta(days=3),
        )
        auction5 = _get_or_create_auction(
            session, "애플워치 울트라 2", competitor,
            description="3개월 사용, 상태 좋습니다.",
            starting_price=500000, current_price=700000,
            status="active", end_time=now + timedelta(days=1),
        )
        _get_or_create_auction(
            session, "아이패드 프로 11인치", competitor,
            description="6개월 사용, 케이스 포함.",
            starting_price=600000, current_price=750000,
            status="ended", end_time=now - timedelta(days=2), winner_id=bidder.id,
        )
        _get_or_create_auction(
            session, "닌텐도 스위치 OLED", competitor,
            description="거의 새 제품, 게임 3개 포함.",
            starting_price=250000, current_price=320000,
            status="ended", end_time=now - timedelta(days=3), winner_id=competitor.id,
        )

        # 입찰 내역 몇 개
        for auction, amount in [(auction4, 900000), (auction4, 950000), (auction5, 700000)]:
            exists = session.exec(
                select(Bid).where(
                    Bid.auction_id == auction.id,
                    Bid.bidder_id == bidder.id,
                    Bid.amount == amount,
                )
            ).first()
            if not exists:
                session.add(Bid(auction_id=auction.id, bidder_id=bidder.id, amount=amount))
        session.commit()

        print("\n✅ 테스트 데이터 생성 완료!")
        print("   로그인 계정: test_seller / test_bidder / test_competitor (비번: test1234)")


if __name__ == "__main__":
    run()
