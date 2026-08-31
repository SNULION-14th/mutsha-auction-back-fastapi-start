"""웹소켓 연결 관리자 (Django Channels 의 channel layer + group 을 대체).

Django Channels 에서는 `channel_layer.group_add / group_send` 로 '그룹'을 관리했지만,
FastAPI 에는 그런 내장 계층이 없습니다. 그래서 '경매방(room) 별 연결 목록'을 직접 들고
있는 아주 단순한 관리자를 만듭니다.

- rooms[auction_id] = {WebSocket, WebSocket, ...}
- broadcast(auction_id, message) 로 그 방의 모든 클라이언트에게 전송
- locks[auction_id] 로 같은 경매의 입찰을 직렬화 (동시 입찰 정합성)
"""
import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # 경매 ID -> 그 방에 접속 중인 웹소켓들
        self.rooms: dict[int, set[WebSocket]] = {}
        # 경매 ID -> 입찰 직렬화용 Lock (Django 의 select_for_update 역할)
        self._locks: dict[int, asyncio.Lock] = {}

    async def connect(self, auction_id: int, websocket: WebSocket) -> None:
        """핸드셰이크를 수락하고 해당 경매방에 연결을 추가."""
        await websocket.accept()
        self.rooms.setdefault(auction_id, set()).add(websocket)

    def disconnect(self, auction_id: int, websocket: WebSocket) -> None:
        """연결을 방에서 제거 (Django 의 group_discard)."""
        room = self.rooms.get(auction_id)
        if room:
            room.discard(websocket)
            if not room:
                self.rooms.pop(auction_id, None)

    async def broadcast(self, auction_id: int, message: dict) -> None:
        """경매방의 모든 클라이언트에게 JSON 을 전송 (Django 의 group_send)."""
        room = list(self.rooms.get(auction_id, set()))
        for connection in room:
            try:
                await connection.send_json(message)
            except Exception:
                # 이미 끊긴 연결은 조용히 정리
                self.disconnect(auction_id, connection)

    def lock_for(self, auction_id: int) -> asyncio.Lock:
        """경매별 입찰 Lock 을 가져옵니다 (없으면 생성)."""
        return self._locks.setdefault(auction_id, asyncio.Lock())


# 앱 전역에서 공유하는 단일 인스턴스
manager = ConnectionManager()
