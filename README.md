# Auction Backend (FastAPI) — 실습 시작점

세미나 **sem6 실습의 출발점(백엔드)** 입니다. FastAPI + SQLModel 로 리팩토링된 경매 앱이지만,
아직 **실시간 기능(WebSocket / SSE)이 비어 있는 "문제 상태"** 예요.

> 지금은 입찰(HTTP POST)을 해도 **입찰한 본인에게만** 최신 정보가 돌아옵니다.
> 같은 경매방을 보는 다른 사용자에게는 실시간으로 전달되지 않아요. 이 문제를 가이드를 따라
> **WebSocket(양방향 실시간 입찰)** 과 **SSE(전역 새 경매 알림)** 로 해결하는 것이 목표입니다.

`app/realtime/`, `app/main.py`, `app/routers/auctions.py` 안에 `TODO(실습)` 주석으로
구현할 지점을 표시해 두었습니다.

## 🚀 실행

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed                 # 테스트 데이터 (선택)
uvicorn app.main:app --reload --port 8000
```

- API 문서(Swagger): http://localhost:8000/docs
- 테스트 계정: `test_seller` / `test_bidder` / `test_competitor` (비밀번호 `test1234`)
- 카카오 로그인/카카오페이는 `.env` 에 키를 넣어야 실제로 동작합니다(기본 기능은 없이도 OK).

## 📁 구조

```
app/
  main.py            # FastAPI 앱 (실시간 라우터 include 는 TODO)
  core/              # config · database · security · deps
  models.py          # SQLModel 테이블
  schemas.py         # 요청 검증 스키마
  serializers.py     # 응답 직렬화
  services.py        # 도메인 로직 (place_bid 등)
  routers/           # users · points · auctions · payments
  realtime/          # TODO(실습): manager.py · ws.py · broker.py · sse.py 를 여기에 만듭니다
  seed.py            # 테스트 데이터 시드
```

정답 구현은 **`mutsha-auction-back-fastapi`** 저장소의 `main` 브랜치에서 확인할 수 있습니다.
