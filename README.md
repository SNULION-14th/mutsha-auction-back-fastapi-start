# Auction Backend (FastAPI)

경매 시스템 백엔드를 **Django → FastAPI** 로 리팩토링한 버전입니다.
실시간 기능으로 **WebSocket**(경매방 실시간 입찰)과 **SSE**(전역 새 경매 알림)를 함께 제공합니다.

> 원본 Django 버전(`mutsha-auction-back-professor`)과 **API 경로·응답 형태가 동일**하여
> 기존 프론트엔드가 거의 그대로 동작합니다. (실시간 부분만 프론트에서 새로 연결)

## 🛠 기술 스택

- **Framework**: FastAPI (ASGI 네이티브)
- **ORM**: SQLModel (SQLAlchemy + Pydantic) · SQLite
- **Auth**: PyJWT + bcrypt, 쿠키 기반 JWT (access/refresh)
- **Realtime**: WebSocket(Starlette 내장) + SSE(StreamingResponse)
- **Server**: Uvicorn

## 📁 구조

```
app/
  main.py            # FastAPI 앱 (asgi.py + settings.py + urls.py 통합)
  core/
    config.py        # 환경변수 (pydantic-settings)
    database.py      # 엔진 / 세션
    security.py      # JWT·비밀번호·쿠키
    deps.py          # 인증 의존성 (CookieJWTAuthentication 대체)
  models.py          # SQLModel 테이블 (4개 앱 통합)
  schemas.py         # 요청 검증 스키마
  serializers.py     # 응답 직렬화 (DRF serializer 대체)
  services.py        # 도메인 로직 (입찰/경매 종료)
  routers/           # users · points · auctions · payments
  realtime/
    manager.py       # 웹소켓 연결 관리자 (Channels channel-layer 대체)
    broker.py        # SSE 발행/구독 브로커
    ws.py            # /ws/auction/{id}  (양방향 입찰)
    sse.py           # /sse/notifications (전역 알림)
  seed.py            # 테스트 데이터 시드
```

## 🚀 실행

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # 필요 시 값 채우기 (카카오 등은 없어도 기본 기능 동작)
python -m app.seed                 # 테스트 데이터 생성 (선택)

uvicorn app.main:app --reload --port 8000
```

- API 문서(Swagger): http://localhost:8000/docs
- 미디어 파일: http://localhost:8000/media/...

테스트 계정: `test_seller` / `test_bidder` / `test_competitor` (비밀번호 `test1234`)

## 🔌 주요 엔드포인트

| 구분 | 메서드/경로 |
| --- | --- |
| 회원 | `POST /api/user/signup/` `POST /api/user/signin/` `POST /api/user/signout/` `POST /api/user/refresh/` `GET/PUT /api/user/me/` `GET /api/user/userinfo/` `POST /api/user/check/` `PUT /api/user/pointreduce/` `GET|POST /api/user/kakao/callback/` |
| 경매 | `GET /api/auction/` `GET /api/auction/recommended/` `GET /api/auction/{id}/` `POST /api/auction/create/` `POST /api/auction/{id}/bid/` `GET /api/auction/my-auctions/` `GET /api/auction/my-bids/` |
| 포인트 | `GET /api/point/` `POST /api/point/` |
| 결제 | `POST /api/payment/ready/` `POST /api/payment/approve/` `GET /api/payment/history/` |
| 실시간 | `WS /ws/auction/{id}` · `GET /sse/notifications` |

## ⚡ 실시간 동작 요약

- **경매방 입찰 (WebSocket, 양방향)**: 클라이언트가 `{"type":"bid","amount":N}` 를 소켓으로 전송 →
  서버가 인증·검증·저장 후 그 방의 모든 클라이언트에게 최신 경매 정보를 방송.
- **전역 알림 (SSE, 단방향)**: 누군가 새 경매를 등록하면 `/sse/notifications` 를 구독 중인
  모든 브라우저에게 `data: {...}` 이벤트를 push.

## 📝 원본(Django) 대비 참고

- Django 의 자동 마이그레이션 대신 앱 시작 시 `SQLModel.metadata.create_all` 로 테이블 생성.
- 기존 `db.sqlite3`(Django 스키마)는 재사용하지 않고 새 스키마 + 시드로 시작합니다.
- 카카오 로그인/카카오페이는 원본과 동일하게 이식되어 있으나 실제 동작에는 해당 키가 필요합니다.
- 비밀번호 해시는 bcrypt 를 사용하므로, 원본 Django 유저를 그대로 옮겨오려면 재가입/재해시가 필요합니다.
