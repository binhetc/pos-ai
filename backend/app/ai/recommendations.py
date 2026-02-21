"""
AI Recommendation Engine
Gợi ý sản phẩm dựa trên hành vi mua hàng.

Algorithms:
1. Frequently Bought Together (Association Rules - Apriori)
2. Category-based suggestions
3. Customer purchase history (Collaborative Filtering lite)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

logger = logging.getLogger(__name__)


class RecommendationResult:
    def __init__(self, product_ids: list[str], reason: str):
        self.product_ids = product_ids
        self.reason = reason


class RecommendationEngine:
    """
    Lightweight recommendation engine cho POS.
    Không cần heavy ML - dùng association rules từ order history.
    """

    def __init__(self):
        # co-occurrence matrix: {product_id: {other_product_id: count}}
        self._co_occurrence: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._is_trained = False

    def train_from_orders(self, order_items_list: list[list[str]]) -> None:
        """
        Train co-occurrence matrix từ lịch sử đơn hàng.

        Args:
            order_items_list: Danh sách các đơn hàng, mỗi đơn là list product_ids
        """
        self._co_occurrence.clear()

        for items in order_items_list:
            # Build co-occurrence pairs
            unique_items = list(set(items))
            for i, item_a in enumerate(unique_items):
                for item_b in unique_items[i + 1:]:
                    self._co_occurrence[item_a][item_b] += 1
                    self._co_occurrence[item_b][item_a] += 1

        self._is_trained = True
        total_pairs = sum(len(v) for v in self._co_occurrence.values())
        logger.info(f"Recommendation model trained: {len(order_items_list)} orders, {total_pairs} pairs")

    def get_frequently_bought_together(
        self,
        current_cart_product_ids: list[str],
        exclude_ids: list[str] | None = None,
        limit: int = 5,
    ) -> RecommendationResult:
        """
        Gợi ý sản phẩm thường được mua cùng với giỏ hàng hiện tại.

        Args:
            current_cart_product_ids: Các sản phẩm đang trong giỏ
            exclude_ids: Loại trừ (chính là sản phẩm đã có trong giỏ)
            limit: Số gợi ý tối đa
        """
        if not self._is_trained:
            return RecommendationResult(product_ids=[], reason="model_not_trained")

        exclude = set(exclude_ids or []) | set(current_cart_product_ids)
        score: dict[str, int] = defaultdict(int)

        for product_id in current_cart_product_ids:
            for related_id, count in self._co_occurrence.get(product_id, {}).items():
                if related_id not in exclude:
                    score[related_id] += count

        # Sort by score descending
        top_products = sorted(score.items(), key=lambda x: x[1], reverse=True)[:limit]

        return RecommendationResult(
            product_ids=[pid for pid, _ in top_products],
            reason="frequently_bought_together",
        )

    def get_category_suggestions(
        self,
        category_id: str,
        exclude_ids: list[str] | None = None,
        limit: int = 5,
    ) -> RecommendationResult:
        """
        Gợi ý sản phẩm cùng category (fallback khi không đủ data).
        Thực tế query DB theo category - xử lý ở API layer.
        """
        return RecommendationResult(
            product_ids=[],
            reason="category_based",
        )


# Singleton
recommendation_engine = RecommendationEngine()
