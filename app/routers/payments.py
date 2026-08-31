"""카카오페이 결제 라우터 (Django `Payment/views.py`).

외부 카카오페이 API 를 그대로 호출합니다(비동기 httpx 사용).
실제 동작에는 KAKAO_PAY_KEY 등 환경변수가 필요합니다.
"""
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models import Payment, User, UserProfile
from app.schemas import PayApproveRequest, PayReadyRequest

router = APIRouter(prefix="/api/payment", tags=["payment"])

PAYREADY_URL = "https://open-api.kakaopay.com/online/v1/payment/ready"
PAYAPPROVE_URL = "https://open-api.kakaopay.com/online/v1/payment/approve"
PAYMENT_DETAIL_URL = "https://open-api.kakaopay.com/online/v1/payment/order"


def _pay_header() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"SECRET_KEY {settings.KAKAO_PAY_KEY}",
    }


@router.post("/ready/")
async def pay_ready(
    body: PayReadyRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    pay_data = {
        "cid": settings.KAKAO_PAY_CID,
        "partner_order_id": body.partner_order_id,
        "partner_user_id": body.partner_user_id,
        "item_name": body.item_name,
        "total_amount": body.total_amount,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PAYREADY_URL, headers=_pay_header(), json=pay_data
        )
    response_data = response.json()

    if response.status_code == 200:
        session.add(
            Payment(
                tid=response_data["tid"],
                partner_order_id=body.partner_order_id,
                partner_user_id=body.partner_user_id,
                point=int(body.item_name),
                price=body.total_amount,
                user_id=user.id,
            )
        )
        session.commit()

    return JSONResponse(response_data, status_code=response.status_code)


@router.post("/approve/")
async def pay_approve(
    body: PayApproveRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    payment = session.exec(select(Payment).where(Payment.tid == body.tid)).first()
    if payment is None:
        return JSONResponse(
            {"detail": "결제 정보를 찾을 수 없습니다."}, status_code=404
        )

    if payment.pay_status == "approved":
        return JSONResponse(
            {
                "detail": "이미 처리된 결제입니다.",
                "point_info": {"old_points": 0, "added_points": 0, "new_points": 0},
            },
            status_code=200,
        )

    pay_data = {
        "cid": settings.KAKAO_PAY_CID,
        "tid": body.tid,
        "partner_order_id": payment.partner_order_id,
        "partner_user_id": payment.partner_user_id,
        "pg_token": body.pg_token,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PAYAPPROVE_URL, headers=_pay_header(), json=pay_data
        )

    if response.status_code != 200:
        return JSONResponse(response.json(), status_code=response.status_code)

    response_data = response.json()
    profile = session.exec(
        select(UserProfile).where(UserProfile.user_id == user.id)
    ).first()

    old_points = profile.remaining_points
    added_points = int(payment.point)
    new_points = old_points + added_points
    profile.remaining_points = new_points
    session.add(profile)

    payment.pay_status = "approved"
    payment.approved_at = datetime.now(timezone.utc)
    session.add(payment)
    session.commit()

    response_data["point_info"] = {
        "old_points": old_points,
        "added_points": added_points,
        "new_points": new_points,
    }
    return JSONResponse(response_data, status_code=200)


@router.get("/history/")
async def payment_history(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    payments = session.exec(
        select(Payment)
        .where(Payment.user_id == user.id, Payment.pay_status == "approved")
        .order_by(Payment.id.desc())
    ).all()

    history: list[dict] = []
    async with httpx.AsyncClient() as client:
        for payment in payments:
            try:
                response = await client.post(
                    PAYMENT_DETAIL_URL,
                    headers=_pay_header(),
                    json={"cid": settings.KAKAO_PAY_CID, "tid": payment.tid},
                )
                if response.status_code == 200:
                    d = response.json()
                    history.append(
                        {
                            "tid": payment.tid,
                            "item_name": d.get("item_name", ""),
                            "amount": d.get("amount", {}).get("total", 0),
                            "payment_method_type": d.get("payment_method_type", ""),
                            "approved_at": d.get("approved_at", ""),
                            "status": d.get("status", ""),
                            "point": payment.point,
                            "price": payment.price,
                        }
                    )
            except Exception:
                history.append(
                    {
                        "tid": payment.tid,
                        "item_name": f"{payment.point} 포인트",
                        "amount": payment.price,
                        "payment_method_type": "카카오페이",
                        "approved_at": payment.approved_at.isoformat()
                        if payment.approved_at
                        else "",
                        "status": "DONE",
                        "point": payment.point,
                        "price": payment.price,
                    }
                )

    return history
