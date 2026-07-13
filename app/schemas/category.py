from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductSummaryResponse


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    image_url: str | None
    parent_id: int | None
    sort_order: int


class CategoryProductsResponse(BaseModel):
    category: CategoryResponse
    products: list[ProductSummaryResponse]
    total: int
