"""경매방 웹소켓 (Django Channels `consumers.AuctionConsumer` 대체).

경로: ws://<host>/ws/auction/{auction_id}

- 접속하면 해당 경매방 그룹에 추가되어, 이후 입찰 방송을 실시간으로 받습니다.
- 클라이언트가 {"type": "bid", "amount": N} 을 보내면(양방향!) 서버가 입찰을
  검증·저장한 뒤 그 방의 모두에게 최신 경매 정보를 방송합니다.
- 로그인하지 않은 사용자도 '관전'은 가능하지만 입찰은 로그인 쿠키가 필요합니다.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.core.database import engine
from app.core.deps import get_user_from_token
from app.realtime.manager import manager
from app.serializers import serialize_auction
from app.services import BidError, place_bid

router = APIRouter()


@router.websocket("/ws/auction/{auction_id}")
async def auction_ws(websocket: WebSocket, auction_id: int):
    await manager.connect(auction_id, websocket)
    try:
        while True:
            message = await websocket.receive_json()

            if message.get("type") == "bid":
                await _handle_bid(websocket, auction_id, message)
            # 그 외 타입은 무시 (확장 지점)
    except WebSocketDisconnect:
        manager.disconnect(auction_id, websocket)
    except Exception:
        manager.disconnect(auction_id, websocket)


async def _handle_bid(websocket: WebSocket, auction_id: int, message: dict) -> None:
    # 웹소켓 핸드셰이크에 실려온 쿠키로 사용자 인증
    token = websocket.cookies.get("access_token")
    amount = message.get("amount")

    # 같은 경매의 입찰을 직렬화 (동시 입찰 정합성)
    async with manager.lock_for(auction_id):
        with Session(engine) as session:
            user = get_user_from_token(token, session)
            if user is None:
                await websocket.send_json(
                    {"type": "error", "detail": "please signin"}
                )
                return
            try:
                auction = place_bid(session, auction_id, user, amount)
            except BidError as e:
                await websocket.send_json({"type": "error", "detail": e.detail})
                return

            # 이미지 절대경로용 base_url 은 http 스킴으로 (ws:// -> http://)
            http_base = (
                str(websocket.base_url)
                .replace("ws://", "http://", 1)
                .replace("wss://", "https://", 1)
            )
            data = serialize_auction(session, auction, http_base)

        # 방 전체에 최신 경매 상태 방송
        await manager.broadcast(auction_id, data)
