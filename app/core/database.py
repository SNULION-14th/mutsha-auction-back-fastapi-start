"""데이터베이스 엔진 / 세션 설정.

Django ORM 대신 SQLModel(= SQLAlchemy + Pydantic)을 사용합니다.
- Django: `settings.DATABASES` + 자동 마이그레이션
- 여기서는: `create_engine` + `SQLModel.metadata.create_all`
"""
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite 는 기본적으로 커넥션이 만들어진 스레드에서만 쓸 수 있습니다.
# FastAPI 는 여러 스레드에서 요청을 처리하므로 check_same_thread=False 가 필요합니다.
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    """앱 시작 시 모든 테이블을 생성합니다 (없을 때만)."""
    # models 를 반드시 import 해야 SQLModel.metadata 에 테이블이 등록됩니다.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI 의존성: 요청마다 DB 세션을 열고 닫습니다.

    Django 의 `Model.objects` 를 대신해, 각 뷰(라우터)에서 `session` 을 주입받아 사용합니다.
    """
    with Session(engine) as session:
        yield session
