"""포인트 라우터 (Django `Point/views.py`)."""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.core.database import get_session
from app.models import Point
from app.schemas import PointCreateRequest

router = APIRouter(prefix="/api/point", tags=["point"])


def _serialize(point: Point) -> dict:
    return {"id": point.id, "price": point.price, "point": point.point}


@router.get("/")
def point_list(session: Session = Depends(get_session)):
    points = session.exec(select(Point)).all()
    return [_serialize(p) for p in points]


@router.post("/", status_code=status.HTTP_201_CREATED)
def point_create(body: PointCreateRequest, session: Session = Depends(get_session)):
    if not body.price or not body.point:
        return JSONResponse(
            {"detail": "fields missing."}, status_code=status.HTTP_400_BAD_REQUEST
        )
    point = Point(price=body.price, point=body.point)
    session.add(point)
    session.commit()
    session.refresh(point)
    return _serialize(point)
