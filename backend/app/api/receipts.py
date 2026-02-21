"""Receipt generation endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.order import Order, OrderStatus
from app.models.store import Store
from app.schemas.auth import CurrentUser
from app.services.receipt import (
    ReceiptData,
    ReceiptItem,
    generate_receipt_lines,
    format_receipt_text,
    generate_esc_pos_commands,
    ReceiptLine,
)

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("/{order_id}/data", response_model=ReceiptData)
async def get_receipt_data(
    order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get receipt data for an order."""
    # Fetch order with relationships
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.store_id == current_user.store_id,
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    if order.status not in [OrderStatus.COMPLETED, OrderStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot print receipt for order with status: {order.status}",
        )
    
    # Fetch store info
    store_result = await db.execute(
        select(Store).where(Store.id == current_user.store_id)
    )
    store = store_result.scalar_one()
    
    # Build receipt data
    receipt_data = ReceiptData(
        store_name=store.name,
        store_address=store.address,
        store_phone=store.phone,
        store_tax_id=store.tax_id,
        order_number=order.order_number,
        order_date=order.created_at,
        cashier_name=current_user.full_name,
        customer_name=order.customer.name if order.customer else None,
        customer_phone=order.customer.phone if order.customer else None,
        items=[
            ReceiptItem(
                name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                discount=item.discount,
            )
            for item in order.items
        ],
        subtotal=order.subtotal,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total=order.total,
        payment_method=order.payment_method.value if order.payment_method else "N/A",
        note=order.note,
    )
    
    return receipt_data


@router.get("/{order_id}/preview", response_model=list[ReceiptLine])
async def get_receipt_preview(
    order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get formatted receipt lines for preview."""
    receipt_data = await get_receipt_data(order_id, current_user, db)
    return generate_receipt_lines(receipt_data)


@router.get("/{order_id}/text", response_class=Response)
async def get_receipt_text(
    order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get plain text receipt."""
    receipt_data = await get_receipt_data(order_id, current_user, db)
    text = format_receipt_text(receipt_data)
    return Response(content=text, media_type="text/plain; charset=utf-8")


@router.get("/{order_id}/escpos", response_class=Response)
async def get_receipt_escpos(
    order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get ESC/POS binary commands for thermal printer.
    Send this directly to USB/Bluetooth thermal printer from mobile app.
    """
    receipt_data = await get_receipt_data(order_id, current_user, db)
    escpos_bytes = generate_esc_pos_commands(receipt_data)
    
    return Response(
        content=escpos_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="receipt_{order_id}.bin"'
        },
    )
