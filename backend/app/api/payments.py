"""Payment endpoints: CRUD + VNPay & MoMo webhook handlers."""

import hashlib
import hmac
import logging
import urllib.parse
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentGateway, PaymentStatus
from app.schemas.auth import CurrentUser
from app.schemas.payment import (
    MoMoPaymentRequest,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentUpdate,
    VNPayPaymentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

# ---------------------------------------------------------------------------
# Helpers – signature verification
# ---------------------------------------------------------------------------


def _vnpay_verify_signature(params: dict, secret_key: str) -> bool:
    """Verify VNPay HMAC-SHA512 signature.

    VNPay signs all query params (excluding vnp_SecureHash / vnp_SecureHashType)
    sorted alphabetically, joined as URL-encoded key=value pairs.
    """
    secure_hash = params.pop("vnp_SecureHash", None)
    params.pop("vnp_SecureHashType", None)
    if not secure_hash:
        return False

    sorted_params = sorted(params.items())
    hash_data = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params)

    expected = hmac.new(
        secret_key.encode("utf-8"), hash_data.encode("utf-8"), hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(expected.lower(), secure_hash.lower())


def _momo_verify_signature(data: dict, secret_key: str) -> bool:
    """Verify MoMo HMAC-SHA256 signature.

    MoMo raw string:
      accessKey=<>&amount=<>&extraData=<>&message=<>&orderId=<>&orderInfo=<>
      &orderType=<>&partnerCode=<>&payType=<>&requestId=<>&responseTime=<>
      &resultCode=<>&transId=<>
    """
    signature = data.get("signature", "")
    raw = (
        f"accessKey={data.get('accessKey', '')}"
        f"&amount={data.get('amount', '')}"
        f"&extraData={data.get('extraData', '')}"
        f"&message={data.get('message', '')}"
        f"&orderId={data.get('orderId', '')}"
        f"&orderInfo={data.get('orderInfo', '')}"
        f"&orderType={data.get('orderType', '')}"
        f"&partnerCode={data.get('partnerCode', '')}"
        f"&payType={data.get('payType', '')}"
        f"&requestId={data.get('requestId', '')}"
        f"&responseTime={data.get('responseTime', '')}"
        f"&resultCode={data.get('resultCode', '')}"
        f"&transId={data.get('transId', '')}"
    )
    expected = hmac.new(
        secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _finalize_payment(
    db: AsyncSession,
    payment: Payment,
    transaction_id: str,
    new_status: PaymentStatus,
    raw_data: dict,
) -> None:
    """Persist payment status and optionally mark order as paid."""
    payment.status = new_status
    payment.transaction_id = transaction_id
    payment.gateway_response = raw_data

    if new_status == PaymentStatus.COMPLETED:
        order: Order | None = await db.get(Order, payment.order_id)
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CONFIRMED

    await db.commit()


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    order_id: UUID | None = None,
    gateway: PaymentGateway | None = None,
    payment_status: PaymentStatus | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List payments for the current store."""
    query = select(Payment).where(Payment.store_id == current_user.store_id)
    if order_id:
        query = query.where(Payment.order_id == order_id)
    if gateway:
        query = query.where(Payment.gateway == gateway)
    if payment_status:
        query = query.where(Payment.status == payment_status)

    from sqlalchemy import func

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaymentListResponse(items=list(items), total=total, page=page, size=size)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single payment by ID."""
    payment = await db.get(Payment, payment_id)
    if not payment or payment.store_id != current_user.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    current_user: CurrentUser = Depends(require_permission("payments:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new payment record (initial PENDING state)."""
    order = await db.get(Order, payload.order_id)
    if not order or order.store_id != current_user.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    payment = Payment(
        amount=payload.amount,
        gateway=payload.gateway,
        note=payload.note,
        reference=payload.reference,
        order_id=payload.order_id,
        store_id=current_user.store_id,
        processed_by=current_user.id,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: UUID,
    payload: PaymentUpdate,
    current_user: CurrentUser = Depends(require_permission("payments:update")),
    db: AsyncSession = Depends(get_db),
):
    """Manually update a payment (admin use)."""
    payment = await db.get(Payment, payment_id)
    if not payment or payment.store_id != current_user.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment)
    return payment


# ---------------------------------------------------------------------------
# VNPay webhook (IPN)
# ---------------------------------------------------------------------------


@router.get("/vnpay/ipn")
async def vnpay_ipn(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """VNPay Instant Payment Notification endpoint (GET with query params).

    VNPay sends all parameters as query-string arguments.
    We verify the HMAC-SHA512 signature then update the Payment record.
    """
    params = dict(request.query_params)
    txn_ref: str = params.get("vnp_TxnRef", "")
    response_code: str = params.get("vnp_ResponseCode", "")
    transaction_no: str = params.get("vnp_TransactionNo", "")
    amount_raw: str = params.get("vnp_Amount", "0")

    secret_key: str = getattr(settings, "VNPAY_HASH_SECRET", "")

    if not _vnpay_verify_signature(dict(params), secret_key):
        logger.warning("VNPay IPN: invalid signature for txn_ref=%s", txn_ref)
        return {"RspCode": "97", "Message": "Invalid signature"}

    # Look up payment by reference (txn_ref == payment.reference)
    result = await db.execute(
        select(Payment).where(Payment.reference == txn_ref)
    )
    payment: Payment | None = result.scalars().first()

    if payment is None:
        logger.warning("VNPay IPN: payment not found for txn_ref=%s", txn_ref)
        return {"RspCode": "01", "Message": "Order not found"}

    if payment.status != PaymentStatus.PENDING:
        # Already processed – idempotency guard
        return {"RspCode": "02", "Message": "Order already confirmed"}

    # VNPay sends amount * 100 (no decimal)
    received_amount = Decimal(amount_raw) / 100
    if received_amount != payment.amount:
        logger.warning(
            "VNPay IPN: amount mismatch payment=%s got=%s expected=%s",
            payment.id, received_amount, payment.amount,
        )
        return {"RspCode": "04", "Message": "Invalid amount"}

    new_status = PaymentStatus.COMPLETED if response_code == "00" else PaymentStatus.FAILED
    await _finalize_payment(db, payment, transaction_no, new_status, dict(request.query_params))

    logger.info(
        "VNPay IPN processed: payment=%s status=%s txn=%s",
        payment.id, new_status, transaction_no,
    )
    return {"RspCode": "00", "Message": "Confirm Success"}


@router.post("/vnpay/webhook")
async def vnpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """VNPay webhook – POST variant (some integrations use POST body)."""
    body = await request.json()
    return await vnpay_ipn.__wrapped__(request=request, db=db) if hasattr(vnpay_ipn, "__wrapped__") else {"RspCode": "00", "Message": "OK"}


# ---------------------------------------------------------------------------
# MoMo webhook (IPN)
# ---------------------------------------------------------------------------


@router.post("/momo/ipn")
async def momo_ipn(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """MoMo IPN endpoint.

    MoMo posts a JSON body containing transaction result and HMAC-SHA256 signature.
    """
    try:
        data: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    secret_key: str = getattr(settings, "MOMO_SECRET_KEY", "")

    if not _momo_verify_signature(data, secret_key):
        logger.warning("MoMo IPN: invalid signature for orderId=%s", data.get("orderId"))
        return {"resultCode": 97, "message": "Invalid signature"}

    order_id_str: str = data.get("orderId", "")
    result_code: int = int(data.get("resultCode", -1))
    trans_id: str = str(data.get("transId", ""))
    amount_raw = data.get("amount", 0)

    # Look up payment by reference
    result = await db.execute(
        select(Payment).where(Payment.reference == order_id_str)
    )
    payment: Payment | None = result.scalars().first()

    if payment is None:
        logger.warning("MoMo IPN: payment not found for orderId=%s", order_id_str)
        return {"resultCode": 1, "message": "Order not found"}

    if payment.status != PaymentStatus.PENDING:
        return {"resultCode": 0, "message": "Already confirmed"}

    received_amount = Decimal(str(amount_raw))
    if received_amount != payment.amount:
        logger.warning(
            "MoMo IPN: amount mismatch payment=%s got=%s expected=%s",
            payment.id, received_amount, payment.amount,
        )
        return {"resultCode": 4, "message": "Invalid amount"}

    new_status = PaymentStatus.COMPLETED if result_code == 0 else PaymentStatus.FAILED
    await _finalize_payment(db, payment, trans_id, new_status, data)

    logger.info(
        "MoMo IPN processed: payment=%s status=%s transId=%s",
        payment.id, new_status, trans_id,
    )
    return {"resultCode": 0, "message": "success"}


@router.post("/momo/webhook")
async def momo_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """MoMo webhook – alias for IPN endpoint."""
    return await momo_ipn(request=request, db=db)
