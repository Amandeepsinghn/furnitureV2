import json
import re
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.schemas import Category, Product, ProductImage, ProductVariant
from app.schemas.product import ProductCreate, ProductImageCreate, ProductUpdate, ProductVariantCreate, ProductVariantUpdate
from app.services.cloudinary.cloudinary_service import CloudinaryService


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-")


def unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while db.scalar(select(Product.id).where(Product.slug == slug)):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class ProductService:
    def __init__(self, session: Session, cloudinary_service: CloudinaryService | None = None):
        self.db = session
        self.cloudinary = cloudinary_service or CloudinaryService()

    def _attach_images(
        self,
        product: Product,
        image_payloads: list[ProductImageCreate],
    ) -> None:
        for image_data in image_payloads:
            if not image_data.url:
                raise HTTPException(
                    status_code=400,
                    detail="Image url is required when images are provided in JSON",
                )
            product.images.append(ProductImage(**image_data.model_dump()))

        if image_payloads and not any(image.is_primary for image in image_payloads):
            product.images[0].is_primary = True

    async def _upload_and_attach_images(
        self,
        product: Product,
        files: list[UploadFile],
        alt_texts: list[str] | None = None,
    ) -> None:
        if not files:
            return

        uploads = await self.cloudinary.upload_images(
            files,
            folder=f"furniture/products/{product.slug}",
        )

        for index, upload in enumerate(uploads):
            alt_text = alt_texts[index] if alt_texts and index < len(alt_texts) else None
            product.images.append(
                ProductImage(
                    url=upload["url"],
                    public_id=upload["public_id"],
                    alt_text=alt_text,
                    is_primary=index == 0 and not product.images,
                    sort_order=index,
                )
            )

    def create_product_record(self, payload: ProductCreate, base_slug: str) -> Product:
        category = self.db.get(Category, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")

        if payload.sku and self.db.scalar(select(Product.id).where(Product.sku == payload.sku)):
            raise HTTPException(status_code=409, detail="Product SKU already exists")

        product = Product(
            category_id=payload.category_id,
            name=payload.name,
            slug=unique_slug(self.db, base_slug),
            description=payload.description,
            short_description=payload.short_description,
            sku=payload.sku,
            price=payload.price,
            compare_at_price=payload.compare_at_price,
            currency=payload.currency,
            material=payload.material,
            color=payload.color,
            style=payload.style,
            room_type=payload.room_type,
            width_cm=payload.width_cm,
            height_cm=payload.height_cm,
            depth_cm=payload.depth_cm,
            weight_kg=payload.weight_kg,
            extra_specs=payload.extra_specs,
            is_featured=payload.is_featured,
            is_active=payload.is_active,
            stock_quantity=payload.stock_quantity,
        )

        for variant_data in payload.variants:
            existing_variant = self.db.scalar(
                select(ProductVariant.id).where(ProductVariant.sku == variant_data.sku)
            )
            if existing_variant:
                raise HTTPException(
                    status_code=409,
                    detail=f"Variant SKU '{variant_data.sku}' already exists",
                )
            if variant_data.seating_capacity is not None:
                duplicate_capacity = any(
                    v.seating_capacity == variant_data.seating_capacity
                    for v in product.variants
                )
                if duplicate_capacity:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Seating capacity {variant_data.seating_capacity} already exists for this product",
                    )
            product.variants.append(ProductVariant(**variant_data.model_dump()))

        return product

    async def create_product(
        self,
        payload: ProductCreate,
        *,
        image_files: list[UploadFile] | None = None,
        alt_texts: list[str] | None = None,
    ) -> Product:
        base_slug = slugify(payload.slug or payload.name)
        if not base_slug:
            raise HTTPException(status_code=400, detail="Unable to generate a valid slug")

        product = self.create_product_record(payload, base_slug)

        if image_files:
            await self._upload_and_attach_images(product, image_files, alt_texts)
        elif payload.images:
            self._attach_images(product, payload.images)

        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    async def add_product_images(
        self,
        product_id: int,
        files: list[UploadFile],
        alt_texts: list[str] | None = None,
    ) -> Product:
        product = self.db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        await self._upload_and_attach_images(product, files, alt_texts)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product_image(self, product_id: int, image_id: int) -> None:
        product = self.db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        image = self.db.get(ProductImage, image_id)
        if image is None or image.product_id != product.id:
            raise HTTPException(status_code=404, detail="Product image not found")

        if image.public_id:
            self.cloudinary.delete_image(image.public_id)

        self.db.delete(image)
        self.db.commit()

    @staticmethod
    def parse_product_form_data(data: str) -> ProductCreate:
        try:
            raw_data: dict[str, Any] = json.loads(data)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid product JSON in form data") from exc

        return ProductCreate.model_validate(raw_data)

    def _get_product_or_404(self, product_id: int) -> Product:
        product = self.db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def update_product(self, product_id: int, payload: ProductUpdate) -> Product:
        product = self._get_product_or_404(product_id)
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        if "category_id" in update_data:
            category = self.db.get(Category, update_data["category_id"])
            if category is None:
                raise HTTPException(status_code=404, detail="Category not found")

        if update_data.get("sku"):
            existing_sku = self.db.scalar(
                select(Product.id).where(
                    Product.sku == update_data["sku"],
                    Product.id != product_id,
                )
            )
            if existing_sku:
                raise HTTPException(status_code=409, detail="Product SKU already exists")

        if "slug" in update_data and update_data["slug"]:
            base_slug = slugify(update_data["slug"])
            if not base_slug:
                raise HTTPException(status_code=400, detail="Unable to generate a valid slug")
            update_data["slug"] = base_slug

            existing_slug = self.db.scalar(
                select(Product.id).where(
                    Product.slug == update_data["slug"],
                    Product.id != product_id,
                )
            )
            if existing_slug:
                raise HTTPException(status_code=409, detail="Product slug already exists")

        for field, value in update_data.items():
            setattr(product, field, value)

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, product_id: int) -> None:
        product = self._get_product_or_404(product_id)

        for image in list(product.images):
            if image.public_id:
                self.cloudinary.delete_image(image.public_id)

        self.db.delete(product)
        self.db.commit()

    def _get_variant_or_404(self, product_id: int, variant_id: int) -> ProductVariant:
        self._get_product_or_404(product_id)
        variant = self.db.get(ProductVariant, variant_id)
        if variant is None or variant.product_id != product_id:
            raise HTTPException(status_code=404, detail="Product variant not found")
        return variant

    def _ensure_unique_variant_sku(self, sku: str, exclude_variant_id: int | None = None) -> None:
        stmt = select(ProductVariant.id).where(ProductVariant.sku == sku)
        if exclude_variant_id is not None:
            stmt = stmt.where(ProductVariant.id != exclude_variant_id)
        if self.db.scalar(stmt):
            raise HTTPException(status_code=409, detail=f"Variant SKU '{sku}' already exists")

    def _ensure_unique_seating_capacity(
        self,
        product_id: int,
        seating_capacity: int | None,
        exclude_variant_id: int | None = None,
    ) -> None:
        if seating_capacity is None:
            return
        stmt = select(ProductVariant.id).where(
            ProductVariant.product_id == product_id,
            ProductVariant.seating_capacity == seating_capacity,
        )
        if exclude_variant_id is not None:
            stmt = stmt.where(ProductVariant.id != exclude_variant_id)
        if self.db.scalar(stmt):
            raise HTTPException(
                status_code=409,
                detail=f"Seating capacity {seating_capacity} already exists for this product",
            )

    def add_product_variant(self, product_id: int, payload: ProductVariantCreate) -> Product:
        product = self._get_product_or_404(product_id)
        self._ensure_unique_variant_sku(payload.sku)
        self._ensure_unique_seating_capacity(product_id, payload.seating_capacity)

        product.variants.append(ProductVariant(**payload.model_dump()))
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product_variant(
        self,
        product_id: int,
        variant_id: int,
        payload: ProductVariantUpdate,
    ) -> Product:
        product = self._get_product_or_404(product_id)
        variant = self._get_variant_or_404(product_id, variant_id)
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        if update_data.get("sku"):
            self._ensure_unique_variant_sku(update_data["sku"], exclude_variant_id=variant_id)

        if "seating_capacity" in update_data:
            self._ensure_unique_seating_capacity(
                product_id,
                update_data["seating_capacity"],
                exclude_variant_id=variant_id,
            )

        for field, value in update_data.items():
            setattr(variant, field, value)

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product_variant(self, product_id: int, variant_id: int) -> None:
        variant = self._get_variant_or_404(product_id, variant_id)
        self.db.delete(variant)
        self.db.commit()
