"""Reporting & Analytics endpoints with RBAC enforcement."""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.models.customer import Customer
from app.models.inventory import InventoryAdjustment
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/reports", tags=["reports"])


# Response schemas
class DailySalesItem(BaseModel):
    date: date
    total_orders: int
    total_revenue: Decimal = Field(..., decimal_places=2)
    avg_order_value: Decimal = Field(..., decimal_places=2)


class DailySalesReport(BaseModel):
    items: list[DailySalesItem]
    period_start: date
    period_end: date
    total_revenue: Decimal = Field(..., decimal_places=2)
    total_orders: int


class TopProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    product_id: str
    product_name: str
    sku: str
    total_quantity: int
    total_revenue: Decimal = Field(..., decimal_places=2)


class TopProductsReport(BaseModel):
    items: list[TopProduct]
    period_start: date
    period_end: date


class PaymentMethodStat(BaseModel):
    payment_method: PaymentMethod
    total_orders: int
    total_revenue: Decimal = Field(..., decimal_places=2)
    percentage: Decimal = Field(..., decimal_places=2)


class PaymentMethodReport(BaseModel):
    items: list[PaymentMethodStat]
    period_start: date
    period_end: date
    total_revenue: Decimal = Field(..., decimal_places=2)


class InventoryTurnoverItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    product_id: str
    product_name: str
    sku: str
    current_stock: int
    units_sold: int
    turnover_ratio: Decimal | None = Field(None, decimal_places=2)


class InventoryTurnoverReport(BaseModel):
    items: list[InventoryTurnoverItem]
    period_start: date
    period_end: date


class CustomerAnalyticsItem(BaseModel):
    customer_id: str
    customer_name: str
    total_orders: int
    total_spent: Decimal = Field(..., decimal_places=2)
    avg_order_value: Decimal = Field(..., decimal_places=2)
    loyalty_points: int


class CustomerAnalyticsReport(BaseModel):
    items: list[CustomerAnalyticsItem]
    period_start: date
    period_end: date
    total_customers: int


@router.get("/daily-sales", response_model=DailySalesReport)
async def get_daily_sales_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(require_permission("report:sales")),
    db: AsyncSession = Depends(get_db),
):
    """Get daily sales report (requires report:sales permission)."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date",
        )

    # Query orders by date range
    query = select(
        func.date(Order.created_at).label("date"),
        func.count(Order.id).label("total_orders"),
        func.sum(Order.total).label("total_revenue"),
        func.avg(Order.total).label("avg_order_value"),
    ).where(
        and_(
            Order.store_id == current_user.store_id,
            Order.status == OrderStatus.COMPLETED,
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
        )
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at))

    result = await db.execute(query)
    daily_stats = result.all()

    # Calculate totals
    total_revenue = sum(row.total_revenue or Decimal("0.00") for row in daily_stats)
    total_orders = sum(row.total_orders or 0 for row in daily_stats)

    items = [
        DailySalesItem(
            date=row.date,
            total_orders=row.total_orders,
            total_revenue=row.total_revenue or Decimal("0.00"),
            avg_order_value=row.avg_order_value or Decimal("0.00"),
        )
        for row in daily_stats
    ]

    return DailySalesReport(
        items=items,
        period_start=start_date,
        period_end=end_date,
        total_revenue=total_revenue,
        total_orders=total_orders,
    )


@router.get("/top-products", response_model=TopProductsReport)
async def get_top_products_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Number of top products"),
    current_user: CurrentUser = Depends(require_permission("report:sales")),
    db: AsyncSession = Depends(get_db),
):
    """Get top-selling products report (requires report:sales permission)."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date",
        )

    # Query top products by quantity sold
    query = (
        select(
            OrderItem.product_id,
            Product.name.label("product_name"),
            Product.sku,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            and_(
                Order.store_id == current_user.store_id,
                Order.status == OrderStatus.COMPLETED,
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
            )
        )
        .group_by(OrderItem.product_id, Product.name, Product.sku)
        .order_by(desc(func.sum(OrderItem.quantity)))
        .limit(limit)
    )

    result = await db.execute(query)
    top_products = result.all()

    items = [
        TopProduct(
            product_id=str(row.product_id),
            product_name=row.product_name,
            sku=row.sku,
            total_quantity=row.total_quantity,
            total_revenue=row.total_revenue or Decimal("0.00"),
        )
        for row in top_products
    ]

    return TopProductsReport(
        items=items,
        period_start=start_date,
        period_end=end_date,
    )


@router.get("/payment-methods", response_model=PaymentMethodReport)
async def get_payment_method_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(require_permission("report:sales")),
    db: AsyncSession = Depends(get_db),
):
    """Get payment method breakdown report (requires report:sales permission)."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date",
        )

    # Query payment method stats
    query = (
        select(
            Order.payment_method,
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_revenue"),
        )
        .where(
            and_(
                Order.store_id == current_user.store_id,
                Order.status == OrderStatus.COMPLETED,
                Order.payment_method.isnot(None),
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
            )
        )
        .group_by(Order.payment_method)
        .order_by(desc(func.sum(Order.total)))
    )

    result = await db.execute(query)
    payment_stats = result.all()

    # Calculate total revenue for percentage
    total_revenue = sum(row.total_revenue or Decimal("0.00") for row in payment_stats)

    items = [
        PaymentMethodStat(
            payment_method=row.payment_method,
            total_orders=row.total_orders,
            total_revenue=row.total_revenue or Decimal("0.00"),
            percentage=(
                (row.total_revenue / total_revenue * 100)
                if total_revenue > 0
                else Decimal("0.00")
            ),
        )
        for row in payment_stats
    ]

    return PaymentMethodReport(
        items=items,
        period_start=start_date,
        period_end=end_date,
        total_revenue=total_revenue,
    )


@router.get("/inventory-turnover", response_model=InventoryTurnoverReport)
async def get_inventory_turnover_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    sort_by: Literal["turnover", "stock", "sold"] = Query("turnover", description="Sort by field"),
    current_user: CurrentUser = Depends(require_permission("report:inventory")),
    db: AsyncSession = Depends(get_db),
):
    """Get inventory turnover report (requires report:inventory permission)."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date",
        )

    # Subquery for units sold
    sold_subquery = (
        select(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("units_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            and_(
                Order.store_id == current_user.store_id,
                Order.status == OrderStatus.COMPLETED,
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
            )
        )
        .group_by(OrderItem.product_id)
        .subquery()
    )

    # Main query with turnover calculation
    query = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku,
            Product.in_stock.label("current_stock"),
            func.coalesce(sold_subquery.c.units_sold, 0).label("units_sold"),
            func.case(
                (Product.in_stock > 0, sold_subquery.c.units_sold / Product.in_stock),
                else_=None,
            ).label("turnover_ratio"),
        )
        .outerjoin(sold_subquery, Product.id == sold_subquery.c.product_id)
        .where(Product.store_id == current_user.store_id)
    )

    # Apply sorting
    if sort_by == "turnover":
        query = query.order_by(desc("turnover_ratio"))
    elif sort_by == "stock":
        query = query.order_by(desc(Product.in_stock))
    elif sort_by == "sold":
        query = query.order_by(desc("units_sold"))

    query = query.limit(limit)

    result = await db.execute(query)
    turnover_data = result.all()

    items = [
        InventoryTurnoverItem(
            product_id=str(row.product_id),
            product_name=row.product_name,
            sku=row.sku,
            current_stock=row.current_stock,
            units_sold=row.units_sold,
            turnover_ratio=row.turnover_ratio,
        )
        for row in turnover_data
    ]

    return InventoryTurnoverReport(
        items=items,
        period_start=start_date,
        period_end=end_date,
    )


@router.get("/customer-analytics", response_model=CustomerAnalyticsReport)
async def get_customer_analytics_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    min_orders: int = Query(1, ge=1, description="Minimum orders threshold"),
    current_user: CurrentUser = Depends(require_permission("report:sales")),
    db: AsyncSession = Depends(get_db),
):
    """Get customer analytics report (requires report:sales permission)."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date",
        )

    # Query customer purchase behavior
    query = (
        select(
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            Customer.loyalty_points,
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_spent"),
            func.avg(Order.total).label("avg_order_value"),
        )
        .join(Order, Customer.id == Order.customer_id)
        .where(
            and_(
                Order.store_id == current_user.store_id,
                Order.status == OrderStatus.COMPLETED,
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
            )
        )
        .group_by(Customer.id, Customer.name, Customer.loyalty_points)
        .having(func.count(Order.id) >= min_orders)
        .order_by(desc(func.sum(Order.total)))
        .limit(limit)
    )

    result = await db.execute(query)
    customer_data = result.all()

    # Count total unique customers in period
    total_count_query = (
        select(func.count(func.distinct(Order.customer_id)))
        .where(
            and_(
                Order.store_id == current_user.store_id,
                Order.status == OrderStatus.COMPLETED,
                Order.customer_id.isnot(None),
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
            )
        )
    )
    total_customers_result = await db.execute(total_count_query)
    total_customers = total_customers_result.scalar_one()

    items = [
        CustomerAnalyticsItem(
            customer_id=str(row.customer_id),
            customer_name=row.customer_name,
            total_orders=row.total_orders,
            total_spent=row.total_spent or Decimal("0.00"),
            avg_order_value=row.avg_order_value or Decimal("0.00"),
            loyalty_points=row.loyalty_points,
        )
        for row in customer_data
    ]

    return CustomerAnalyticsReport(
        items=items,
        period_start=start_date,
        period_end=end_date,
        total_customers=total_customers,
    )
