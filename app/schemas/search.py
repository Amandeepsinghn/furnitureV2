from pydantic import BaseModel

from app.schemas.product import ProductSummaryResponse


class ProductSearchResponse(BaseModel):
    query: str | None = None
    products: list[ProductSummaryResponse]
    total: int
    skip: int = 0
    limit: int = 20
