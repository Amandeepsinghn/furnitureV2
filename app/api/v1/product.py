from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps.database import get_db
from app.db.schemas import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.cloudinary.cloudinary_service import CloudinaryService
from app.services.product.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def get_cloudinary_service() -> CloudinaryService:
    return CloudinaryService()


def get_product_service(
    db: Session = Depends(get_db),
    cloudinary_service: CloudinaryService = Depends(get_cloudinary_service),
) -> ProductService:
    return ProductService(session=db, cloudinary_service=cloudinary_service)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return await service.create_product(payload)


@router.post(
    "/with-images",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_with_images(
    data: Annotated[str, Form(description="Product JSON (images field optional)")],
    images: list[UploadFile] = File(default=[]),
    alt_texts: Annotated[list[str] | None, Form(description="Optional alt text per image")] = None,
    service: ProductService = Depends(get_product_service),
) -> Product:
    if not images:
        raise HTTPException(status_code=400, detail="At least one image file is required")

    payload = ProductService.parse_product_form_data(data)
    return await service.create_product(payload, image_files=images, alt_texts=alt_texts)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return service.update_product(product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> None:
    service.delete_product(product_id)


@router.post("/{product_id}/images", response_model=ProductResponse)
async def upload_product_images(
    product_id: int,
    images: list[UploadFile] = File(...),
    alt_texts: Annotated[list[str] | None, Form()] = None,
    service: ProductService = Depends(get_product_service),
) -> Product:
    return await service.add_product_images(product_id, images, alt_texts)


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_image(
    product_id: int,
    image_id: int,
    service: ProductService = Depends(get_product_service),
) -> None:
    service.delete_product_image(product_id, image_id)
