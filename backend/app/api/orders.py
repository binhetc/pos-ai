"""Order CRUD endpoints with RBAC enforcement."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.auth import CurrentUser
from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def generate_order_number() -> str:
    """Generate unique order number based on timestamp."""
    return f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    status_filter: OrderStatus | None = None,
    customer_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List orders with pagination and optional filters."""
    offset = (page - 1) * size

    # Base query - filter by store
    query = select(Order).where(Order.store_id == current_user.store_id)

    # Apply filters
    if status_filter:
        query = query.where(Order.status == status_filter)
    if customer_id:
        query = query.where(Order.customer_id == customer_id)
    if from_date:
        query = query.where(Order.created_at >= from_date)
    if to_date:
        query = query.where(Order.created_at <= to_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated items
    query = query.offset(offset).limit(size).order_by(Order.created_at.desc())
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single order by ID."""
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

    return OrderResponse.model_validate(order)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    current_user: CurrentUser = Depends(require_permission("order:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order (requires order:create permission)."""
    # Validate products and calculate totals
    product_ids = [item.product_id for item in body.items]
    result = await db.execute(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.store_id == current_user.store_id,
            Product.is_active == True,  # noqa: E712
        )
    )
    products = {p.id: p for p in result.scalars().all()}

    # Check all products exist
    missing_ids = set(product_ids) - set(products.keys())
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Products not found: {missing_ids}",
        )

    # Calculate order totals
    subtotal = Decimal("0.00")
    order_items = []

    for item_data in body.items:
        product = products[item_data.product_id]
        unit_price = product.price
        item_subtotal = (unit_price * item_data.quantity) - item_data.discount

        subtotal += item_subtotal

        order_items.append(
            OrderItem(
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                discount=item_data.discount,
                subtotal=item_subtotal,
            )
        )

    total = subtotal + body.tax_amount - body.discount_amount

    # Create order
    order = Order(
        order_number=generate_order_number(),
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        tax_amount=body.tax_amount,
        discount_amount=body.discount_amount,
        total=total,
        payment_method=body.payment_method,
        note=body.note,
        store_id=current_user.store_id,
        cashier_id=current_user.id,
        customer_id=body.customer_id,
        items=order_items,
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    return OrderResponse.model_validate(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    body: OrderUpdate,
    current_user: CurrentUser = Depends(require_permission("order:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an order (requires order:update permission)."""
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

    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    return OrderResponse.model_validate(order)


@router.post("/{order_id}/void", response_model=OrderResponse)
async def void_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(require_permission("order:void")),
    db: AsyncSession = Depends(get_db),
):
    """Void an order (requires order:void permission)."""
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

    if order.status not in [OrderStatus.PENDING, OrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot void order with status: {order.status}",
        )

    order.status = OrderStatus.VOIDED
    await db.commit()
    await db.refresh(order)

    return OrderResponse.model_validate(order)


@router.post("/{order_id}/refund", response_model=OrderResponse)
async def refund_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(require_permission("order:refund")),
    db: AsyncSession = Depends(get_db),
):
    """Refund an order (requires order:refund permission)."""
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

    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only refund completed orders, current status: {order.status}",
        )

    order.status = OrderStatus.REFUNDED
    await db.commit()
    await db.refresh(order)

    return OrderResponse.model_validate(order)


@router.post("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(require_permission("order:update")),
    db: AsyncSession = Depends(get_db),
):
    """Mark order as completed (requires order:update permission)."""
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

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only complete pending orders, current status: {order.status}",
        )

    if not order.payment_method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method required to complete order",
        )

    order.status = OrderStatus.COMPLETED
    await db.commit()
    await db.refresh(order)

    return OrderResponse.model_validate(order)
