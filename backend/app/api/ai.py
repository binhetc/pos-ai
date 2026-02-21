"""AI Features API Endpoints - Product Recognition & Recommendations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.auth import CurrentUser
from app.ai.product_recognition import recognition_service
from app.ai.recommendations import recommendation_engine

router = APIRouter(prefix="/ai", tags=["ai"])


# ─── Request / Response Schemas ──────────────────────────────────────────────

class RecognizeProductRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded JPEG/PNG từ camera")


class RecognizedProduct(BaseModel):
    product_id: str
    confidence: float


class RecognizeProductResponse(BaseModel):
    success: bool
    product_id: str | None
    confidence: float
    top_k: list[RecognizedProduct]
    method: str  # 'ai' | 'fallback'
    message: str


class RecommendRequest(BaseModel):
    cart_product_ids: list[str] = Field(..., min_length=1, description="Product IDs đang trong giỏ")


class ProductSummary(BaseModel):
    id: str
    name: str
    price: float
    sku: str
    image_url: str | None


class RecommendResponse(BaseModel):
    products: list[ProductSummary]
    reason: str


class TrainRecommendResponse(BaseModel):
    success: bool
    orders_processed: int
    message: str


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/recognize-product", response_model=RecognizeProductResponse)
async def recognize_product(
    body: RecognizeProductRequest,
    current_user: CurrentUser = Depends(require_permission("ai:vision")),
    db: AsyncSession = Depends(get_db),
):
    """
    Nhận diện sản phẩm từ ảnh camera.
    Mobile app gửi 1 frame JPEG/PNG dưới dạng base64.
    Trả về product_id + confidence nếu nhận diện thành công.
    """
    # Lấy danh sách product IDs của store
    result = await db.execute(
        select(Product.id).where(
            Product.store_id == current_user.store_id,
            Product.is_active == True,  # noqa: E712
        )
    )
    store_product_ids = [str(pid) for pid in result.scalars().all()]

    if not store_product_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active products found in store",
        )

    # Chạy AI recognition
    ai_result = await recognition_service.recognize_from_base64(
        body.image_base64,
        store_product_ids,
    )

    if ai_result.success:
        message = f"Nhận diện thành công (confidence: {ai_result.confidence:.1%})"
    elif ai_result.confidence > 0:
        message = (
            f"Confidence thấp ({ai_result.confidence:.1%}). "
            "Vui lòng dùng barcode scanner để xác nhận."
        )
    else:
        message = "Không nhận diện được. Vui lòng dùng barcode scanner."

    return RecognizeProductResponse(
        success=ai_result.success,
        product_id=ai_result.product_id,
        confidence=ai_result.confidence,
        top_k=[
            RecognizedProduct(
                product_id=item["product_id"],
                confidence=item["confidence"],
            )
            for item in ai_result.top_k
        ],
        method=ai_result.method,
        message=message,
    )


@router.post("/recommend", response_model=RecommendResponse)
async def get_recommendations(
    body: RecommendRequest,
    current_user: CurrentUser = Depends(require_permission("ai:recommendations")),
    db: AsyncSession = Depends(get_db),
):
    """
    Gợi ý sản phẩm dựa trên giỏ hàng hiện tại.
    Dùng Frequently Bought Together algorithm.
    """
    # Validate cart products thuộc store
    result = await db.execute(
        select(Product).where(
            Product.id.in_(body.cart_product_ids),
            Product.store_id == current_user.store_id,
            Product.is_active == True,  # noqa: E712
        )
    )
    valid_products = result.scalars().all()

    if not valid_products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid products found in cart",
        )

    valid_ids = [str(p.id) for p in valid_products]

    # Get recommendations
    rec_result = recommendation_engine.get_frequently_bought_together(
        current_cart_product_ids=valid_ids,
        limit=5,
    )

    # Fallback: category-based nếu không có đủ data
    if not rec_result.product_ids:
        # Lấy sản phẩm cùng category với cart item đầu tiên
        first_product = valid_products[0]
        result = await db.execute(
            select(Product).where(
                Product.category_id == first_product.category_id,
                Product.store_id == current_user.store_id,
                Product.id.notin_(body.cart_product_ids),
                Product.is_active == True,  # noqa: E712
            ).limit(5)
        )
        category_products = result.scalars().all()

        return RecommendResponse(
            products=[
                ProductSummary(
                    id=str(p.id),
                    name=p.name,
                    price=float(p.price),
                    sku=p.sku,
                    image_url=p.image_url,
                )
                for p in category_products
            ],
            reason="category_based",
        )

    # Fetch recommended products từ DB
    result = await db.execute(
        select(Product).where(
            Product.id.in_(rec_result.product_ids),
            Product.store_id == current_user.store_id,
            Product.is_active == True,  # noqa: E712
        )
    )
    recommended_products = result.scalars().all()

    return RecommendResponse(
        products=[
            ProductSummary(
                id=str(p.id),
                name=p.name,
                price=float(p.price),
                sku=p.sku,
                image_url=p.image_url,
            )
            for p in recommended_products
        ],
        reason=rec_result.reason,
    )


@router.post("/train-recommendations", response_model=TrainRecommendResponse)
async def train_recommendation_model(
    current_user: CurrentUser = Depends(require_permission("ai:recommendations")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrain recommendation model từ lịch sử đơn hàng.
    Nên chạy định kỳ (daily) hoặc khi có nhiều đơn hàng mới.
    """
    # Fetch completed orders của store
    result = await db.execute(
        select(Order).where(
            Order.store_id == current_user.store_id,
            Order.status == OrderStatus.COMPLETED,
        )
    )
    orders = result.scalars().all()

    if not orders:
        return TrainRecommendResponse(
            success=False,
            orders_processed=0,
            message="Không có đơn hàng nào để train",
        )

    # Build order items list
    order_items_list = []
    for order in orders:
        item_product_ids = [str(item.product_id) for item in order.items]
        if len(item_product_ids) >= 2:  # Chỉ train với đơn có >= 2 sản phẩm
            order_items_list.append(item_product_ids)

    # Train model
    recommendation_engine.train_from_orders(order_items_list)

    return TrainRecommendResponse(
        success=True,
        orders_processed=len(order_items_list),
        message=f"Đã train recommendation model với {len(order_items_list)} đơn hàng",
    )
