from typing import Any, Mapping

from app.adapters.commerce.dataset.base_mapper import (
    PlatformDatasetMapper,
    ProductMappingContext,
)
from app.modules.market_intelligence.schemas import NormalizedProduct, ProductSort


class AmazonDatasetMapper(PlatformDatasetMapper):
    platform = "amazon"
    supported_sorts = frozenset(
        {ProductSort.DEFAULT, ProductSort.PRICE_ASC, ProductSort.PRICE_DESC}
    )

    def map_product(
        self,
        raw: Mapping[str, Any],
        context: ProductMappingContext,
    ) -> NormalizedProduct:
        self.validate_record_scope(raw, context)
        product_id = self.required_text(raw.get("parent_asin"), "parent_asin")
        title = self.required_text(raw.get("title"), "title")
        price = self.decimal_value(raw.get("price"), "price", required=True)
        price = self.decimal_value(
            raw.get("price"),
            "price",
            required=True,
        )

        assert price is not None
        categories = raw.get("categories")
        category = (
            self.optional_text(categories[-1])
            if isinstance(categories, list) and categories
            else self.optional_text(raw.get("main_category"))
        )
        rating = self.decimal_value(raw.get("average_rating"), "average_rating")
        review_count = self.integer_value(raw.get("rating_number"), "rating_number")
        source_ref = self.source_ref(raw, context, product_id)
        return self.build_product(
            context=context,
            source_ref=source_ref,
            product_id=product_id,
            title=title,
            brand=self.optional_text(raw.get("brand")),
            category=category,
            price=price,
            currency=self.optional_text(raw.get("currency")) or "USD",
            shop_name=self.optional_text(raw.get("store")),
            rating=rating,
            review_count=review_count,
            source_url=self.optional_text(raw.get("url")),
        )
