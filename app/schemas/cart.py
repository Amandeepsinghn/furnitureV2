from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AddToCartRequest(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(default=1, ge=1)


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_slug: str
    variant_id: int | None
    variant_name: str | None
    quantity: int
    unit_price: Decimal | None
    line_total: Decimal | None
    currency: str
    primary_image_url: str | None
    created_at: datetime
    updated_at: datetime


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    total_items: int
    subtotal: Decimal
