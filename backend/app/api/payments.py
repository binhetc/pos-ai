"""Payment endpoints: CRUD + VNPay & MoMo webhook handlers."""

import datetime
import hashlib
import hmac
import json
import logging
import urllib.parse
import uuid as _uuid_module
from decimal import Decimal
from uuid import UUID

import httpx
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
    MoMoCreateResponse,
    MoMoPaymentRequest,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentUpdate,
    VNPayCreateResponse,
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
            order.status = OrderStatus.COMPLETED

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


# ---------------------------------------------------------------------------
# VNPay – create payment URL
# ---------------------------------------------------------------------------


def _build_vnpay_signature(params: dict, secret_key: str) -> str:
    """Build HMAC-SHA512 signature for VNPay payment creation."""
    sorted_params = sorted(params.items())
    hash_data = "&".join(
        f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params
    )
    return hmac.new(
        secret_key.encode("utf-8"), hash_data.encode("utf-8"), hashlib.sha512
    ).hexdigest()


@router.post("/vnpay/create", response_model=VNPayCreateResponse)
async def create_vnpay_payment(
    payload: VNPayPaymentRequest,
    current_user: CurrentUser = Depends(require_permission("payments:create")),
    db: AsyncSession = Depends(get_db),
):
    """Build a VNPay payment URL and persist a PENDING Payment record.

    Returns a redirect URL that the frontend uses to send the customer to VNPay.
    """
    order = await db.get(Order, payload.order_id)
    if not order or order.store_id != current_user.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    txn_ref = _uuid_module.uuid4().hex[:16].upper()  # short unique ref
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    amount_vnd = int(payload.amount * 100)  # VNPay requires no decimals × 100

    params: dict = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": getattr(settings, "VNPAY_TMN_CODE", ""),
        "vnp_Amount": str(amount_vnd),
        "vnp_CreateDate": now,
        "vnp_CurrCode": "VND",
        "vnp_IpAddr": "127.0.0.1",
        "vnp_Locale": "vn",
        "vnp_OrderInfo": payload.order_info,
        "vnp_OrderType": "other",
        "vnp_TxnRef": txn_ref,
    }
    if payload.return_url:
        params["vnp_ReturnUrl"] = payload.return_url
    if payload.ipn_url:
        params["vnp_IpnUrl"] = payload.ipn_url

    secret_key: str = getattr(settings, "VNPAY_HASH_SECRET", "")
    sig = _build_vnpay_signature(dict(params), secret_key)
    params["vnp_SecureHash"] = sig

    base_url: str = getattr(settings, "VNPAY_PAYMENT_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
    payment_url = base_url + "?" + urllib.parse.urlencode(params)

    # Persist PENDING payment
    payment = Payment(
        amount=payload.amount,
        gateway=PaymentGateway.VNPAY,
        note=payload.order_info,
        reference=txn_ref,
        order_id=payload.order_id,
        store_id=current_user.store_id,
        processed_by=current_user.id,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    logger.info("VNPay payment created: payment=%s txn_ref=%s", payment.id, txn_ref)
    return VNPayCreateResponse(payment_id=payment.id, payment_url=payment_url, txn_ref=txn_ref)


# ---------------------------------------------------------------------------
# MoMo – create payment (deeplink / QR)
# ---------------------------------------------------------------------------


def _build_momo_request_signature(data: dict, secret_key: str) -> str:
    """Build HMAC-SHA256 signature for MoMo payment creation request."""
    raw = (
        f"accessKey={data['accessKey']}"
        f"&amount={data['amount']}"
        f"&extraData={data['extraData']}"
        f"&ipnUrl={data['ipnUrl']}"
        f"&orderId={data['orderId']}"
        f"&orderInfo={data['orderInfo']}"
        f"&partnerCode={data['partnerCode']}"
        f"&redirectUrl={data['redirectUrl']}"
        f"&requestId={data['requestId']}"
        f"&requestType={data['requestType']}"
    )
    return hmac.new(
        secret_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@router.post("/momo/create", response_model=MoMoCreateResponse)
async def create_momo_payment(
    payload: MoMoPaymentRequest,
    current_user: CurrentUser = Depends(require_permission("payments:create")),
    db: AsyncSession = Depends(get_db),
):
    """Call MoMo API to create a payment and return deeplink/QR URL.

    MoMo docs: https://developers.momo.vn/v3/docs/payment/api/payment-api/create-payment
    """
    order = await db.get(Order, payload.order_id)
    if not order or order.store_id != current_user.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order_id_str = _uuid_module.uuid4().hex[:16].upper()
    request_id = _uuid_module.uuid4().hex

    partner_code: str = getattr(settings, "MOMO_PARTNER_CODE", "")
    access_key: str = getattr(settings, "MOMO_ACCESS_KEY", "")
    secret_key: str = getattr(settings, "MOMO_SECRET_KEY", "")
    endpoint: str = getattr(settings, "MOMO_ENDPOINT", "https://test-payment.momo.vn/v2/gateway/api/create")

    redirect_url = payload.redirect_url or ""
    ipn_url = payload.ipn_url or ""

    body: dict = {
        "partnerCode": partner_code,
        "accessKey": access_key,
        "requestId": request_id,
        "amount": int(payload.amount),
        "orderId": order_id_str,
        "orderInfo": payload.order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "extraData": "",
        "requestType": "captureWallet",
    }
    body["signature"] = _build_momo_request_signature(body, secret_key)

    # Call MoMo API
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(endpoint, json=body, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            momo_resp = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("MoMo API error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="MoMo API error")
    except httpx.RequestError as exc:
        logger.error("MoMo connection error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cannot reach MoMo API")

    result_code = momo_resp.get("resultCode", -1)
    if result_code != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MoMo rejected: {momo_resp.get('message', 'Unknown error')}",
        )

    # Persist PENDING payment
    payment = Payment(
        amount=payload.amount,
        gateway=PaymentGateway.MOMO,
        note=payload.order_info,
        reference=order_id_str,
        order_id=payload.order_id,
        store_id=current_user.store_id,
        processed_by=current_user.id,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    logger.info("MoMo payment created: payment=%s order_ref=%s", payment.id, order_id_str)
    return MoMoCreateResponse(
        payment_id=payment.id,
        pay_url=momo_resp.get("payUrl", ""),
        deeplink=momo_resp.get("deeplink"),
        qr_code_url=momo_resp.get("qrCodeUrl"),
        request_id=request_id,
    )
