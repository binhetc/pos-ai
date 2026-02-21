"""Customer Management endpoints with RBAC enforcement."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.customer import Customer
from app.schemas.auth import CurrentUser
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List customers with pagination and optional search."""
    offset = (page - 1) * size

    # Base query - no store filter for customers (global)
    query = select(Customer)

    # Apply search filter
    if search:
        query = query.where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated items
    query = query.offset(offset).limit(size).order_by(Customer.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return CustomerListResponse(
        items=[CustomerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single customer by ID."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return CustomerResponse.model_validate(customer)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    current_user: CurrentUser = Depends(require_permission("customer:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new customer (requires customer:create permission)."""
    # Check phone uniqueness if provided
    if body.phone:
        existing = await db.execute(
            select(Customer).where(Customer.phone == body.phone)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this phone already exists",
            )

    # Check email uniqueness if provided
    if body.email:
        existing = await db.execute(
            select(Customer).where(Customer.email == body.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this email already exists",
            )

    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    body: CustomerUpdate,
    current_user: CurrentUser = Depends(require_permission("customer:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a customer (requires customer:update permission)."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Check phone uniqueness if updating
    if body.phone and body.phone != customer.phone:
        existing = await db.execute(
            select(Customer).where(
                Customer.phone == body.phone,
                Customer.id != customer_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this phone already exists",
            )

    # Check email uniqueness if updating
    if body.email and body.email != customer.email:
        existing = await db.execute(
            select(Customer).where(
                Customer.email == body.email,
                Customer.id != customer_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this email already exists",
            )

    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    current_user: CurrentUser = Depends(require_permission("customer:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a customer (requires customer:delete permission)."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    await db.delete(customer)
    await db.commit()


@router.post("/{customer_id}/loyalty/add", response_model=CustomerResponse)
async def add_loyalty_points(
    customer_id: UUID,
    points: int = Query(..., ge=1, description="Points to add"),
    current_user: CurrentUser = Depends(require_permission("customer:update")),
    db: AsyncSession = Depends(get_db),
):
    """Add loyalty points to customer (requires customer:update permission)."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    customer.loyalty_points += points
    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)


@router.post("/{customer_id}/loyalty/redeem", response_model=CustomerResponse)
async def redeem_loyalty_points(
    customer_id: UUID,
    points: int = Query(..., ge=1, description="Points to redeem"),
    current_user: CurrentUser = Depends(require_permission("customer:update")),
    db: AsyncSession = Depends(get_db),
):
    """Redeem loyalty points from customer (requires customer:update permission)."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    if customer.loyalty_points < points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient loyalty points. Customer has {customer.loyalty_points}, requested {points}",
        )

    customer.loyalty_points -= points
    await db.commit()
    await db.refresh(customer)

    return CustomerResponse.model_validate(customer)
