"""Unit tests for Payment API — VNPay & MoMo webhook handlers."""

import hashlib
import hmac
import urllib.parse
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.api.payments import _vnpay_verify_signature, _momo_verify_signature, _finalize_payment
from app.models.payment import Payment, PaymentGateway, PaymentStatus
from app.models.order import Order, OrderStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_vnpay_params(amount_vnd: int, txn_ref: str, response_code: str, secret: str) -> dict:
    """Build a valid VNPay IPN query-param dict with correct signature."""
    params = {
        "vnp_TmnCode": "TEST_TMN",
        "vnp_Amount": str(amount_vnd),
        "vnp_BankCode": "NCB",
        "vnp_BankTranNo": "VNP" + txn_ref,
        "vnp_CardType": "ATM",
        "vnp_PayDate": "20240101120000",
        "vnp_OrderInfo": "Test order",
        "vnp_TransactionNo": txn_ref,
        "vnp_ResponseCode": response_code,
        "vnp_TransactionStatus": response_code,
        "vnp_TxnRef": txn_ref,
    }
    sorted_params = sorted(params.items())
    hash_data = "&".join(
        f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params
    )
    sig = hmac.new(secret.encode(), hash_data.encode(), hashlib.sha512).hexdigest()
    params["vnp_SecureHash"] = sig
    params["vnp_SecureHashType"] = "HMACSHA512"
    return params


def _build_momo_data(amount: int, order_id: str, result_code: int, secret: str, access_key: str = "AK") -> dict:
    """Build a valid MoMo IPN JSON body with correct signature."""
    data = {
        "partnerCode": "MOMO_TEST",
        "orderId": order_id,
        "requestId": "req_" + order_id,
        "amount": amount,
        "orderInfo": "Test order",
        "orderType": "momo_wallet",
        "transId": "TRANS_" + order_id,
        "resultCode": result_code,
        "message": "Success" if result_code == 0 else "Failed",
        "payType": "qr",
        "responseTime": 1706745600000,
        "extraData": "",
        "accessKey": access_key,
    }
    raw = (
        f"accessKey={data['accessKey']}"
        f"&amount={data['amount']}"
        f"&extraData={data['extraData']}"
        f"&message={data['message']}"
        f"&orderId={data['orderId']}"
        f"&orderInfo={data['orderInfo']}"
        f"&orderType={data['orderType']}"
        f"&partnerCode={data['partnerCode']}"
        f"&payType={data['payType']}"
        f"&requestId={data['requestId']}"
        f"&responseTime={data['responseTime']}"
        f"&resultCode={data['resultCode']}"
        f"&transId={data['transId']}"
    )
    data["signature"] = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return data


# ---------------------------------------------------------------------------
# Signature verification unit tests
# ---------------------------------------------------------------------------


class TestVNPaySignatureVerification:
    SECRET = "supersecret_vnpay"

    def test_valid_signature_passes(self):
        params = _build_vnpay_params(10000000, "TXN123", "00", self.SECRET)
        assert _vnpay_verify_signature(params, self.SECRET) is True

    def test_tampered_amount_fails(self):
        params = _build_vnpay_params(10000000, "TXN123", "00", self.SECRET)
        params["vnp_Amount"] = "9999999"  # tamper
        assert _vnpay_verify_signature(params, self.SECRET) is False

    def test_wrong_secret_fails(self):
        params = _build_vnpay_params(10000000, "TXN123", "00", self.SECRET)
        assert _vnpay_verify_signature(params, "wrong_secret") is False

    def test_missing_signature_fails(self):
        params = _build_vnpay_params(10000000, "TXN123", "00", self.SECRET)
        params.pop("vnp_SecureHash")
        assert _vnpay_verify_signature(params, self.SECRET) is False


class TestMoMoSignatureVerification:
    SECRET = "supersecret_momo"

    def test_valid_signature_passes(self):
        data = _build_momo_data(100000, "ORDER_001", 0, self.SECRET)
        assert _momo_verify_signature(data, self.SECRET) is True

    def test_failed_payment_valid_signature(self):
        data = _build_momo_data(100000, "ORDER_002", 11, self.SECRET)
        assert _momo_verify_signature(data, self.SECRET) is True

    def test_tampered_amount_fails(self):
        data = _build_momo_data(100000, "ORDER_001", 0, self.SECRET)
        data["amount"] = 50000  # tamper
        assert _momo_verify_signature(data, self.SECRET) is False

    def test_wrong_secret_fails(self):
        data = _build_momo_data(100000, "ORDER_001", 0, self.SECRET)
        assert _momo_verify_signature(data, "bad_key") is False


# ---------------------------------------------------------------------------
# _finalize_payment helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_payment_completed_updates_order():
    """_finalize_payment should set order to CONFIRMED when payment COMPLETED."""
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.status = OrderStatus.PENDING

    payment = MagicMock(spec=Payment)
    payment.order_id = order.id
    payment.status = PaymentStatus.PENDING

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=order)

    await _finalize_payment(mock_db, payment, "TXN999", PaymentStatus.COMPLETED, {})

    assert payment.status == PaymentStatus.COMPLETED
    assert payment.transaction_id == "TXN999"
    assert order.status == OrderStatus.COMPLETED
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_payment_failed_does_not_confirm_order():
    """Failed payment should NOT change order status."""
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.status = OrderStatus.PENDING

    payment = MagicMock(spec=Payment)
    payment.order_id = order.id
    payment.status = PaymentStatus.PENDING

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=order)

    await _finalize_payment(mock_db, payment, "TXN_FAIL", PaymentStatus.FAILED, {})

    assert payment.status == PaymentStatus.FAILED
    assert order.status == OrderStatus.PENDING  # unchanged
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# VNPay IPN endpoint integration-style tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vnpay_ipn_success():
    """VNPay IPN with valid signature + matching amount → COMPLETED payment."""
    from app.api.payments import vnpay_ipn

    SECRET = "test_secret_vnpay"
    txn_ref = "REF001"
    amount_vnd = 50000 * 100  # 50,000 VND → VNPay sends 5000000

    payment = MagicMock(spec=Payment)
    payment.id = uuid.uuid4()
    payment.reference = txn_ref
    payment.amount = Decimal("50000")
    payment.status = PaymentStatus.PENDING

    params = _build_vnpay_params(amount_vnd, txn_ref, "00", SECRET)

    mock_request = MagicMock()
    mock_request.query_params = params

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = payment
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    with patch("app.api.payments.settings") as mock_settings, \
         patch("app.api.payments._finalize_payment", new_callable=AsyncMock) as mock_fin:
        mock_settings.VNPAY_HASH_SECRET = SECRET
        response = await vnpay_ipn(request=mock_request, db=mock_db)

    assert response["RspCode"] == "00"
    mock_fin.assert_awaited_once()
    _, _, _, new_status, _ = mock_fin.call_args.args
    assert new_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_vnpay_ipn_invalid_signature():
    """VNPay IPN with bad signature → reject with code 97."""
    from app.api.payments import vnpay_ipn

    params = _build_vnpay_params(5000000, "REF002", "00", "correct_secret")
    params["vnp_SecureHash"] = "badhash"

    mock_request = MagicMock()
    mock_request.query_params = params
    mock_db = AsyncMock()

    with patch("app.api.payments.settings") as mock_settings:
        mock_settings.VNPAY_HASH_SECRET = "correct_secret"
        response = await vnpay_ipn(request=mock_request, db=mock_db)

    assert response["RspCode"] == "97"


@pytest.mark.asyncio
async def test_vnpay_ipn_payment_not_found():
    """VNPay IPN when payment reference not found → code 01."""
    from app.api.payments import vnpay_ipn

    SECRET = "test_secret_vnpay"
    params = _build_vnpay_params(5000000, "UNKNOWN_REF", "00", SECRET)

    mock_request = MagicMock()
    mock_request.query_params = params
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.payments.settings") as mock_settings:
        mock_settings.VNPAY_HASH_SECRET = SECRET
        response = await vnpay_ipn(request=mock_request, db=mock_db)

    assert response["RspCode"] == "01"


# ---------------------------------------------------------------------------
# MoMo IPN endpoint integration-style tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_momo_ipn_success():
    """MoMo IPN success → COMPLETED payment."""
    from app.api.payments import momo_ipn

    SECRET = "test_secret_momo"
    order_ref = "MOMO_ORDER_001"
    amount = 100000

    payment = MagicMock(spec=Payment)
    payment.id = uuid.uuid4()
    payment.reference = order_ref
    payment.amount = Decimal(str(amount))
    payment.status = PaymentStatus.PENDING

    data = _build_momo_data(amount, order_ref, 0, SECRET)

    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value=data)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = payment
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.payments.settings") as mock_settings, \
         patch("app.api.payments._finalize_payment", new_callable=AsyncMock) as mock_fin:
        mock_settings.MOMO_SECRET_KEY = SECRET
        response = await momo_ipn(request=mock_request, db=mock_db)

    assert response["resultCode"] == 0
    mock_fin.assert_awaited_once()
    _, _, _, new_status, _ = mock_fin.call_args.args
    assert new_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_momo_ipn_failed_payment():
    """MoMo IPN with resultCode != 0 → FAILED payment."""
    from app.api.payments import momo_ipn

    SECRET = "test_secret_momo"
    order_ref = "MOMO_ORDER_002"
    amount = 100000

    payment = MagicMock(spec=Payment)
    payment.id = uuid.uuid4()
    payment.reference = order_ref
    payment.amount = Decimal(str(amount))
    payment.status = PaymentStatus.PENDING

    data = _build_momo_data(amount, order_ref, 11, SECRET)  # 11 = user cancel

    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value=data)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = payment
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.payments.settings") as mock_settings, \
         patch("app.api.payments._finalize_payment", new_callable=AsyncMock) as mock_fin:
        mock_settings.MOMO_SECRET_KEY = SECRET
        response = await momo_ipn(request=mock_request, db=mock_db)

    assert response["resultCode"] == 0  # We still ACK the IPN
    _, _, _, new_status, _ = mock_fin.call_args.args
    assert new_status == PaymentStatus.FAILED


@pytest.mark.asyncio
async def test_momo_ipn_invalid_signature():
    """MoMo IPN bad signature → code 97."""
    from app.api.payments import momo_ipn

    data = _build_momo_data(100000, "ORDER_X", 0, "correct_secret")
    data["signature"] = "badhash"

    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value=data)
    mock_db = AsyncMock()

    with patch("app.api.payments.settings") as mock_settings:
        mock_settings.MOMO_SECRET_KEY = "correct_secret"
        response = await momo_ipn(request=mock_request, db=mock_db)

    assert response["resultCode"] == 97


@pytest.mark.asyncio
async def test_momo_ipn_amount_mismatch():
    """MoMo IPN with mismatched amount → code 4."""
    from app.api.payments import momo_ipn

    SECRET = "test_secret_momo"
    order_ref = "MOMO_AMT_001"

    payment = MagicMock(spec=Payment)
    payment.id = uuid.uuid4()
    payment.reference = order_ref
    payment.amount = Decimal("200000")  # expected
    payment.status = PaymentStatus.PENDING

    data = _build_momo_data(100000, order_ref, 0, SECRET)  # sends 100000 != 200000

    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value=data)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = payment
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.payments.settings") as mock_settings:
        mock_settings.MOMO_SECRET_KEY = SECRET
        response = await momo_ipn(request=mock_request, db=mock_db)

    assert response["resultCode"] == 4
