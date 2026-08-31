"""SSE(Server-Sent Events) 브로커 — 전역 알림 발행/구독.

'새 경매 등록' 같은 서버 → 전체 클라이언트 단방향 알림에 사용합니다.
(양방향이 필요한 경매방 입찰은 웹소켓, 단방향 알림은 SSE — 세미나의 핵심 대비!)

동작:
- 각 SSE 연결(브라우저)마다 asyncio.Queue 를 하나씩 구독자로 등록
- publish(event) 가 모든 구독자 큐에 이벤트를 넣음
- SSE 엔드포인트는 자기 큐에서 이벤트를 꺼내 `data: ...\\n\\n` 형식으로 흘려보냄
"""
import asyncio


class Broker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: dict) -> None:
        """모든 구독자에게 이벤트를 전달."""
        for queue in list(self._subscribers):
            await queue.put(event)


# 앱 전역에서 공유하는 단일 인스턴스
broker = Broker()
