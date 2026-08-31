"""전역 알림 SSE 엔드포인트 (Server-Sent Events).

경로: GET /sse/notifications  (Content-Type: text/event-stream)

'새 경매 등록' 같은 서버 → 클라이언트 단방향 알림을 흘려보냅니다.
브라우저는 표준 EventSource API 로 이 엔드포인트에 연결합니다.

SSE 와이어 포맷은 아주 단순합니다:
    data: {"message": "..."}\\n\\n
한 이벤트는 빈 줄(\\n\\n)로 끝납니다.
"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.realtime.broker import broker

router = APIRouter()


@router.get("/sse/notifications")
async def notifications(request: Request):
    queue = await broker.subscribe()

    async def event_stream():
        try:
            # 연결 직후 한 번 코멘트를 보내 프록시/브라우저의 연결을 확립
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 15초마다 keep-alive 코멘트 (연결 유지)
                    yield ": keep-alive\n\n"
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
