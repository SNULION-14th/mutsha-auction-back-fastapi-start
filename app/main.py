"""FastAPI 진입점 (Django 의 asgi.py + settings.py + urls.py 를 한 곳으로).

핵심: FastAPI 는 처음부터 ASGI 네이티브라, WebSocket/SSE 를 위해 Django Channels 나
별도의 ProtocolTypeRouter 설정이 필요 없습니다. 라우터만 등록하면 됩니다.

실행:  uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import create_db_and_tables
# TODO(실습): 실시간 모듈을 만든 뒤, 해당 실습 단계에서 아래 import 주석을 하나씩 해제하세요.
# from app.realtime import ws    # 실습 1-3 (ws.py 를 만든 뒤)
# from app.realtime import sse   # 실습 2-2 (sse.py 를 만든 뒤)
from app.routers import auctions, payments, points, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 테이블 생성 (Django 의 migrate 대체 — 데모용)
    create_db_and_tables()
    yield


app = FastAPI(title="Auction API (FastAPI)", lifespan=lifespan)

# --- CORS (Django corsheaders 대체) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,  # 쿠키 인증을 위해 필수
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 미디어 파일 서빙 (Django static() 대체) ---
Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
app.mount(
    settings.MEDIA_URL.rstrip("/"),
    StaticFiles(directory=settings.MEDIA_ROOT),
    name="media",
)

# --- HTTP 라우터 (Django 의 include(...)) ---
app.include_router(users.router)
app.include_router(points.router)
app.include_router(auctions.router)
app.include_router(payments.router)

# --- 실시간 라우터 (실습에서 추가) ---
# TODO(실습): 위 import 와 같은 단계에서 아래 주석을 하나씩 해제하세요.
# app.include_router(ws.router)   # 실습 1-3 — WebSocket: /ws/auction/{id}
# app.include_router(sse.router)  # 실습 2-2 — SSE:       /sse/notifications


@app.get("/")
def root():
    return {"service": "Auction API (FastAPI)", "docs": "/docs"}
