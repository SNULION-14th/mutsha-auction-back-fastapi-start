"""테스트 데이터 시드 (Django `create_test_data` management command 대체).

실행:  python -m app.seed

경매 이미지는 원본 저장소(mutsha-auction-back-professor)에서 실제로 업로드됐던
사진들을 `media/seed_images/` 로 가져와 사용합니다. (currency 단위는 '잔' = 포인트)
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

        # 이미지는 원본 저장소에서 가져온 media/seed_images/* 사진을 사용합니다.
        _get_or_create_auction(
            session, "🍰 맛있는 케이크", seller,
            description="정성껏 구운 홈메이드 케이크입니다. 직거래 가능해요.",
            starting_price=500000, current_price=850000,
            status="active", end_time=now + timedelta(days=2),
            image_file="seed_images/cake.png",
        )
        _get_or_create_auction(
            session, "💄 명품 향수", seller,
            description="한 번도 사용하지 않은 새 향수예요.",
            starting_price=1000000, current_price=1200000,
            status="active", end_time=now + timedelta(days=5),
            image_file="seed_images/perfume.jpg",
        )
        _get_or_create_auction(
            session, "🧸 곰인형", seller,
            description="포근하고 귀여운 곰인형, 미개봉 새 상품입니다.",
            starting_price=150000, current_price=200000,
            status="ended", end_time=now - timedelta(days=1), winner_id=competitor.id,
            image_file="seed_images/teddybear.jpg",
        )
        auction4 = _get_or_create_auction(
            session, "🥭 신선한 망고", competitor,
            description="달콤하고 신선한 프리미엄 망고입니다.",
            starting_price=800000, current_price=950000,
            status="active", end_time=now + timedelta(days=3),
            image_file="seed_images/mango.jpg",
        )
        auction5 = _get_or_create_auction(
            session, "🍗 바삭한 치킨", competitor,
            description="방금 튀긴 따끈한 치킨입니다.",
            starting_price=500000, current_price=700000,
            status="active", end_time=now + timedelta(days=1),
            image_file="seed_images/chicken.jpg",
        )
        _get_or_create_auction(
            session, "🎟️ 떡볶이 쿠폰", competitor,
            description="어디서나 쓸 수 있는 떡볶이 교환 쿠폰입니다.",
            starting_price=600000, current_price=750000,
            status="ended", end_time=now - timedelta(days=2), winner_id=bidder.id,
            image_file="seed_images/tteokbbeoki_coupon.jpg",
        )
        _get_or_create_auction(
            session, "🎄 크리스마스 트리", competitor,
            description="연말 분위기를 위한 예쁜 트리입니다.",
            starting_price=250000, current_price=320000,
            status="ended", end_time=now - timedelta(days=3), winner_id=competitor.id,
            image_file="seed_images/christmastree.jpg",
        )

        # 입찰 내역 몇 개 (test_bidder 의 '내 입찰' 시나리오용)
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
