from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


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
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=80)
    material: str | None = Field(default=None, max_length=80)
    size_label: str | None = Field(default=None, max_length=80)
    seating_capacity: int | None = Field(default=None, ge=1)
    pack_quantity: int | None = Field(default=None, ge=1, le=6)
    includes_side_table: bool | None = None
    width_cm: Decimal | None = Field(default=None, ge=0)
    height_cm: Decimal | None = Field(default=None, ge=0)
    depth_cm: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductVariantUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, max_length=120)
    price: Decimal | None = Field(default=None, ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=80)
    material: str | None = Field(default=None, max_length=80)
    size_label: str | None = Field(default=None, max_length=80)
    seating_capacity: int | None = Field(default=None, ge=1)
    pack_quantity: int | None = Field(default=None, ge=1, le=6)
    includes_side_table: bool | None = None
    width_cm: Decimal | None = Field(default=None, ge=0)
    height_cm: Decimal | None = Field(default=None, ge=0)
    depth_cm: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SeatingOptionInput(BaseModel):
    """Simple sofa seating price input for create/update."""

    model_config = ConfigDict(populate_by_name=True)

    seating_capacity: int = Field(..., ge=1, alias="seatingCapacity")
    price: Decimal = Field(..., ge=0)
    compare_at_price: Decimal | None = Field(
        default=None, ge=0, alias="compareAtPrice"
    )
    label: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=80)
    width_cm: Decimal | None = Field(default=None, ge=0)
    height_cm: Decimal | None = Field(default=None, ge=0)
    depth_cm: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class QuantityOptionInput(BaseModel):
    """Chair pack quantity price input (1-6 chairs)."""

    model_config = ConfigDict(populate_by_name=True)

    quantity: int = Field(..., ge=1, le=6)
    price: Decimal = Field(..., ge=0)
    compare_at_price: Decimal | None = Field(
        default=None, ge=0, alias="compareAtPrice"
    )
    label: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=80)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class SideTableOptionInput(BaseModel):
    """Bed with/without side table price input."""

    model_config = ConfigDict(populate_by_name=True)

    includes_side_table: bool = Field(..., alias="includesSideTable")
    price: Decimal = Field(..., ge=0)
    compare_at_price: Decimal | None = Field(
        default=None, ge=0, alias="compareAtPrice"
    )
    label: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=80)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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
    seatingOptions: list[SeatingOptionInput] = Field(default_factory=list)
    quantityOptions: list[QuantityOptionInput] = Field(default_factory=list)
    sideTableOptions: list[SideTableOptionInput] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=300)
    sku: str | None = Field(default=None, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    material: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=80)
    style: str | None = Field(default=None, max_length=80)
    room_type: str | None = Field(default=None, max_length=80)
    width_cm: Decimal | None = Field(default=None, ge=0)
    height_cm: Decimal | None = Field(default=None, ge=0)
    depth_cm: Decimal | None = Field(default=None, ge=0)
    weight_kg: Decimal | None = Field(default=None, ge=0)
    extra_specs: dict[str, Any] | None = None
    is_featured: bool | None = None
    is_active: bool | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    seatingOptions: list[SeatingOptionInput] | None = None
    quantityOptions: list[QuantityOptionInput] | None = None
    sideTableOptions: list[SideTableOptionInput] | None = None


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
    compare_at_price: Decimal | None
    color: str | None
    material: str | None
    size_label: str | None
    seating_capacity: int | None
    pack_quantity: int | None
    includes_side_table: bool | None
    width_cm: Decimal | None
    height_cm: Decimal | None
    depth_cm: Decimal | None
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SeatingOptionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    variantId: int
    seatingCapacity: int
    label: str
    price: Decimal | None
    compare_at_price: Decimal | None = Field(default=None, alias="compareAtPrice")
    currency: str = "INR"
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    depth_cm: Decimal | None = None
    is_active: bool = True


class QuantityOptionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    variantId: int
    quantity: int
    label: str
    price: Decimal | None
    compare_at_price: Decimal | None = Field(default=None, alias="compareAtPrice")
    currency: str = "INR"
    is_active: bool = True


class SideTableOptionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    variantId: int
    includesSideTable: bool
    label: str
    price: Decimal | None
    compare_at_price: Decimal | None = Field(default=None, alias="compareAtPrice")
    currency: str = "INR"
    is_active: bool = True


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
    seatingOptions: list[SeatingOptionResponse] = []
    quantityOptions: list[QuantityOptionResponse] = []
    sideTableOptions: list[SideTableOptionResponse] = []

    @computed_field
    @property
    def productId(self) -> int:
        return self.id


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
    seatingOptions: list[SeatingOptionResponse] = []
    quantityOptions: list[QuantityOptionResponse] = []
    sideTableOptions: list[SideTableOptionResponse] = []

    @computed_field
    @property
    def productId(self) -> int:
        return self.id

    @model_validator(mode="after")
    def fill_option_lists(self) -> "ProductResponse":
        if not self.seatingOptions:
            seating: list[SeatingOptionResponse] = []
            for variant in self.variants:
                if not variant.is_active or variant.seating_capacity is None:
                    continue
                seating.append(
                    SeatingOptionResponse(
                        variantId=variant.id,
                        seatingCapacity=variant.seating_capacity,
                        label=variant.size_label
                        or variant.name
                        or f"{variant.seating_capacity} Seater",
                        price=variant.price,
                        compare_at_price=variant.compare_at_price
                        if variant.compare_at_price is not None
                        else self.compare_at_price,
                        currency=self.currency,
                        width_cm=variant.width_cm,
                        height_cm=variant.height_cm,
                        depth_cm=variant.depth_cm,
                        is_active=variant.is_active,
                    )
                )
            self.seatingOptions = sorted(seating, key=lambda option: option.seatingCapacity)

        if not self.quantityOptions:
            quantities: list[QuantityOptionResponse] = []
            for variant in self.variants:
                if not variant.is_active or variant.pack_quantity is None:
                    continue
                quantities.append(
                    QuantityOptionResponse(
                        variantId=variant.id,
                        quantity=variant.pack_quantity,
                        label=variant.size_label
                        or variant.name
                        or (
                            f"{variant.pack_quantity} Chair"
                            if variant.pack_quantity == 1
                            else f"{variant.pack_quantity} Chairs"
                        ),
                        price=variant.price,
                        compare_at_price=variant.compare_at_price
                        if variant.compare_at_price is not None
                        else self.compare_at_price,
                        currency=self.currency,
                        is_active=variant.is_active,
                    )
                )
            self.quantityOptions = sorted(quantities, key=lambda option: option.quantity)

        if not self.sideTableOptions:
            side_tables: list[SideTableOptionResponse] = []
            for variant in self.variants:
                if not variant.is_active or variant.includes_side_table is None:
                    continue
                side_tables.append(
                    SideTableOptionResponse(
                        variantId=variant.id,
                        includesSideTable=variant.includes_side_table,
                        label=variant.size_label
                        or variant.name
                        or (
                            "With side table"
                            if variant.includes_side_table
                            else "Without side table"
                        ),
                        price=variant.price,
                        compare_at_price=variant.compare_at_price
                        if variant.compare_at_price is not None
                        else self.compare_at_price,
                        currency=self.currency,
                        is_active=variant.is_active,
                    )
                )
            self.sideTableOptions = sorted(
                side_tables, key=lambda option: option.includesSideTable
            )

        return self
