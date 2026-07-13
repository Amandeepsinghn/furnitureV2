from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductImageCreate(BaseModel):
    url: str | None = Field(default=None, max_length=500)
    public_id: str | None = Field(default=None, max_length=200)
    alt_text: str | None = Field(default=None, max_length=200)
    is_primary: bool = False
    sort_order: int = 0


class ProductVariantCreate(BaseModel):
    sku: str = Field(..., max_length=80)
    name: str = Field(..., max_length=120)
    price: Decimal | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=80)
    material: str | None = Field(default=None, max_length=80)
    size_label: str | None = Field(default=None, max_length=80)
    width_cm: Decimal | None = Field(default=None, ge=0)
    height_cm: Decimal | None = Field(default=None, ge=0)
    depth_cm: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductCreate(BaseModel):
    category_id: int
    name: str = Field(..., min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=300)
    sku: str | None = Field(default=None, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    material: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=80)
    style: str | None = Field(default=None, max_length=80)
    room_type: str | None = Field(default=None, max_length=80)
    width_cm: Decimal | None = Field(default=None, ge=0)
    height_cm: Decimal | None = Field(default=None, ge=0)
    depth_cm: Decimal | None = Field(default=None, ge=0)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    extra_specs: dict[str, Any] | None = None
    is_featured: bool = False
    is_active: bool = True
    stock_quantity: int = Field(default=0, ge=0)
    images: list[ProductImageCreate] = []
    variants: list[ProductVariantCreate] = []


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    public_id: str | None
    alt_text: str | None
    is_primary: bool
    sort_order: int
    created_at: datetime


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    price: Decimal | None
    color: str | None
    material: str | None
    size_label: str | None
    width_cm: Decimal | None
    height_cm: Decimal | None
    depth_cm: Decimal | None
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    short_description: str | None
    price: Decimal | None
    compare_at_price: Decimal | None
    currency: str
    material: str | None
    color: str | None
    is_featured: bool
    primary_image_url: str | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    slug: str
    description: str | None
    short_description: str | None
    sku: str | None
    price: Decimal | None
    compare_at_price: Decimal | None
    currency: str
    material: str | None
    color: str | None
    style: str | None
    room_type: str | None
    width_cm: Decimal | None
    height_cm: Decimal | None
    depth_cm: Decimal | None
    weight_kg: Decimal | None
    extra_specs: dict[str, Any] | None
    is_featured: bool
    is_active: bool
    stock_quantity: int
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageResponse] = []
    variants: list[ProductVariantResponse] = []
