import json
import re
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.schemas import Category, Product, ProductImage, ProductVariant
from app.schemas.product import (
    ProductCreate,
    ProductImageCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
    QuantityOptionInput,
    SeatingOptionInput,
    SideTableOptionInput,
)
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

    def _seating_option_to_variant(
        self,
        option: SeatingOptionInput,
        *,
        product_slug: str,
    ) -> ProductVariantCreate:
        label = option.label or f"{option.seating_capacity} Seater"
        sku = option.sku or f"{product_slug}-{option.seating_capacity}s"
        return ProductVariantCreate(
            sku=sku[:80],
            name=label,
            price=option.price,
            compare_at_price=option.compare_at_price,
            size_label=label,
            seating_capacity=option.seating_capacity,
            width_cm=option.width_cm,
            height_cm=option.height_cm,
            depth_cm=option.depth_cm,
            stock_quantity=option.stock_quantity,
            is_active=option.is_active,
        )

    def _merge_seating_options_into_variants(
        self,
        variants: list[ProductVariantCreate],
        seating_options: list[SeatingOptionInput],
        *,
        product_slug: str,
    ) -> list[ProductVariantCreate]:
        if not seating_options:
            return variants

        capacities = [option.seating_capacity for option in seating_options]
        if len(capacities) != len(set(capacities)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate seatingCapacity values are not allowed",
            )

        merged = list(variants)
        existing_capacities = {
            variant.seating_capacity
            for variant in merged
            if variant.seating_capacity is not None
        }
        for option in seating_options:
            if option.seating_capacity in existing_capacities:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Seating capacity {option.seating_capacity} is already set "
                        "in variants; use seatingOptions or variants, not both"
                    ),
                )
            merged.append(
                self._seating_option_to_variant(option, product_slug=product_slug)
            )
            existing_capacities.add(option.seating_capacity)
        return merged

    def _sync_seating_options(self, product: Product, seating_options: list[SeatingOptionInput]) -> None:
        if not seating_options:
            return

        capacities = [option.seating_capacity for option in seating_options]
        if len(capacities) != len(set(capacities)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate seatingCapacity values are not allowed",
            )

        existing_by_capacity = {
            variant.seating_capacity: variant
            for variant in product.variants
            if variant.seating_capacity is not None
        }

        for option in seating_options:
            label = option.label or f"{option.seating_capacity} Seater"
            existing = existing_by_capacity.get(option.seating_capacity)
            if existing:
                if option.sku and option.sku != existing.sku:
                    self._ensure_unique_variant_sku(option.sku, exclude_variant_id=existing.id)
                    existing.sku = option.sku
                existing.name = label
                existing.size_label = label
                existing.price = option.price
                existing.compare_at_price = option.compare_at_price
                existing.width_cm = option.width_cm
                existing.height_cm = option.height_cm
                existing.depth_cm = option.depth_cm
                existing.stock_quantity = option.stock_quantity
                existing.is_active = option.is_active
            else:
                sku = option.sku or f"{product.slug}-{option.seating_capacity}s"
                self._ensure_unique_variant_sku(sku[:80])
                product.variants.append(
                    ProductVariant(
                        sku=sku[:80],
                        name=label,
                        price=option.price,
                        compare_at_price=option.compare_at_price,
                        size_label=label,
                        seating_capacity=option.seating_capacity,
                        width_cm=option.width_cm,
                        height_cm=option.height_cm,
                        depth_cm=option.depth_cm,
                        stock_quantity=option.stock_quantity,
                        is_active=option.is_active,
                    )
                )

    def _quantity_option_to_variant(
        self,
        option: QuantityOptionInput,
        *,
        product_slug: str,
    ) -> ProductVariantCreate:
        label = option.label or (
            "1 Chair" if option.quantity == 1 else f"{option.quantity} Chairs"
        )
        sku = option.sku or f"{product_slug}-qty-{option.quantity}"
        return ProductVariantCreate(
            sku=sku[:80],
            name=label,
            price=option.price,
            compare_at_price=option.compare_at_price,
            size_label=label,
            pack_quantity=option.quantity,
            stock_quantity=option.stock_quantity,
            is_active=option.is_active,
        )

    def _merge_quantity_options_into_variants(
        self,
        variants: list[ProductVariantCreate],
        quantity_options: list[QuantityOptionInput],
        *,
        product_slug: str,
    ) -> list[ProductVariantCreate]:
        if not quantity_options:
            return variants

        quantities = [option.quantity for option in quantity_options]
        if len(quantities) != len(set(quantities)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate quantity values are not allowed",
            )

        merged = list(variants)
        existing_quantities = {
            variant.pack_quantity for variant in merged if variant.pack_quantity is not None
        }
        for option in quantity_options:
            if option.quantity in existing_quantities:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Pack quantity {option.quantity} is already set "
                        "in variants; use quantityOptions or variants, not both"
                    ),
                )
            merged.append(
                self._quantity_option_to_variant(option, product_slug=product_slug)
            )
            existing_quantities.add(option.quantity)
        return merged

    def _sync_quantity_options(
        self,
        product: Product,
        quantity_options: list[QuantityOptionInput],
    ) -> None:
        if not quantity_options:
            return

        quantities = [option.quantity for option in quantity_options]
        if len(quantities) != len(set(quantities)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate quantity values are not allowed",
            )

        existing_by_quantity = {
            variant.pack_quantity: variant
            for variant in product.variants
            if variant.pack_quantity is not None
        }

        for option in quantity_options:
            label = option.label or (
                "1 Chair" if option.quantity == 1 else f"{option.quantity} Chairs"
            )
            existing = existing_by_quantity.get(option.quantity)
            if existing:
                if option.sku and option.sku != existing.sku:
                    self._ensure_unique_variant_sku(option.sku, exclude_variant_id=existing.id)
                    existing.sku = option.sku
                existing.name = label
                existing.size_label = label
                existing.price = option.price
                existing.compare_at_price = option.compare_at_price
                existing.stock_quantity = option.stock_quantity
                existing.is_active = option.is_active
            else:
                sku = option.sku or f"{product.slug}-qty-{option.quantity}"
                self._ensure_unique_variant_sku(sku[:80])
                product.variants.append(
                    ProductVariant(
                        sku=sku[:80],
                        name=label,
                        price=option.price,
                        compare_at_price=option.compare_at_price,
                        size_label=label,
                        pack_quantity=option.quantity,
                        stock_quantity=option.stock_quantity,
                        is_active=option.is_active,
                    )
                )

    def _side_table_option_to_variant(
        self,
        option: SideTableOptionInput,
        *,
        product_slug: str,
    ) -> ProductVariantCreate:
        label = option.label or (
            "With side table" if option.includes_side_table else "Without side table"
        )
        suffix = "with-side-table" if option.includes_side_table else "no-side-table"
        sku = option.sku or f"{product_slug}-{suffix}"
        return ProductVariantCreate(
            sku=sku[:80],
            name=label,
            price=option.price,
            compare_at_price=option.compare_at_price,
            size_label=label,
            includes_side_table=option.includes_side_table,
            stock_quantity=option.stock_quantity,
            is_active=option.is_active,
        )

    def _merge_side_table_options_into_variants(
        self,
        variants: list[ProductVariantCreate],
        side_table_options: list[SideTableOptionInput],
        *,
        product_slug: str,
    ) -> list[ProductVariantCreate]:
        if not side_table_options:
            return variants

        flags = [option.includes_side_table for option in side_table_options]
        if len(flags) != len(set(flags)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate includesSideTable values are not allowed",
            )

        merged = list(variants)
        existing_flags = {
            variant.includes_side_table
            for variant in merged
            if variant.includes_side_table is not None
        }
        for option in side_table_options:
            if option.includes_side_table in existing_flags:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Side table option includesSideTable={option.includes_side_table} "
                        "is already set in variants; use sideTableOptions or variants, not both"
                    ),
                )
            merged.append(
                self._side_table_option_to_variant(option, product_slug=product_slug)
            )
            existing_flags.add(option.includes_side_table)
        return merged

    def _sync_side_table_options(
        self,
        product: Product,
        side_table_options: list[SideTableOptionInput],
    ) -> None:
        if not side_table_options:
            return

        flags = [option.includes_side_table for option in side_table_options]
        if len(flags) != len(set(flags)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate includesSideTable values are not allowed",
            )

        existing_by_flag = {
            variant.includes_side_table: variant
            for variant in product.variants
            if variant.includes_side_table is not None
        }

        for option in side_table_options:
            label = option.label or (
                "With side table" if option.includes_side_table else "Without side table"
            )
            existing = existing_by_flag.get(option.includes_side_table)
            if existing:
                if option.sku and option.sku != existing.sku:
                    self._ensure_unique_variant_sku(option.sku, exclude_variant_id=existing.id)
                    existing.sku = option.sku
                existing.name = label
                existing.size_label = label
                existing.price = option.price
                existing.compare_at_price = option.compare_at_price
                existing.stock_quantity = option.stock_quantity
                existing.is_active = option.is_active
            else:
                suffix = "with-side-table" if option.includes_side_table else "no-side-table"
                sku = option.sku or f"{product.slug}-{suffix}"
                self._ensure_unique_variant_sku(sku[:80])
                product.variants.append(
                    ProductVariant(
                        sku=sku[:80],
                        name=label,
                        price=option.price,
                        compare_at_price=option.compare_at_price,
                        size_label=label,
                        includes_side_table=option.includes_side_table,
                        stock_quantity=option.stock_quantity,
                        is_active=option.is_active,
                    )
                )

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

        product_slug = unique_slug(self.db, base_slug)
        variants = self._merge_seating_options_into_variants(
            list(payload.variants),
            payload.seatingOptions,
            product_slug=product_slug,
        )
        variants = self._merge_quantity_options_into_variants(
            variants,
            payload.quantityOptions,
            product_slug=product_slug,
        )
        variants = self._merge_side_table_options_into_variants(
            variants,
            payload.sideTableOptions,
            product_slug=product_slug,
        )

        # Default product price to the lowest option price if not provided
        product_price = payload.price
        if product_price is None and payload.seatingOptions:
            product_price = min(option.price for option in payload.seatingOptions)
        if product_price is None and payload.quantityOptions:
            product_price = min(option.price for option in payload.quantityOptions)
        if product_price is None and payload.sideTableOptions:
            product_price = min(option.price for option in payload.sideTableOptions)

        product = Product(
            category_id=payload.category_id,
            name=payload.name,
            slug=product_slug,
            description=payload.description,
            short_description=payload.short_description,
            sku=payload.sku,
            price=product_price,
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

        for variant_data in variants:
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
            if variant_data.pack_quantity is not None:
                duplicate_quantity = any(
                    v.pack_quantity == variant_data.pack_quantity for v in product.variants
                )
                if duplicate_quantity:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Pack quantity {variant_data.pack_quantity} already exists for this product",
                    )
            if variant_data.includes_side_table is not None:
                duplicate_side_table = any(
                    v.includes_side_table == variant_data.includes_side_table
                    for v in product.variants
                    if v.includes_side_table is not None
                )
                if duplicate_side_table:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Side table option includesSideTable="
                            f"{variant_data.includes_side_table} already exists for this product"
                        ),
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
        seating_options = update_data.pop("seatingOptions", None)
        quantity_options = update_data.pop("quantityOptions", None)
        side_table_options = update_data.pop("sideTableOptions", None)

        if (
            not update_data
            and seating_options is None
            and quantity_options is None
            and side_table_options is None
        ):
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

        if seating_options is not None:
            options = [SeatingOptionInput.model_validate(option) for option in seating_options]
            self._sync_seating_options(product, options)

        if quantity_options is not None:
            options = [QuantityOptionInput.model_validate(option) for option in quantity_options]
            self._sync_quantity_options(product, options)

        if side_table_options is not None:
            options = [SideTableOptionInput.model_validate(option) for option in side_table_options]
            self._sync_side_table_options(product, options)

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

    def _ensure_unique_pack_quantity(
        self,
        product_id: int,
        pack_quantity: int | None,
        exclude_variant_id: int | None = None,
    ) -> None:
        if pack_quantity is None:
            return
        stmt = select(ProductVariant.id).where(
            ProductVariant.product_id == product_id,
            ProductVariant.pack_quantity == pack_quantity,
        )
        if exclude_variant_id is not None:
            stmt = stmt.where(ProductVariant.id != exclude_variant_id)
        if self.db.scalar(stmt):
            raise HTTPException(
                status_code=409,
                detail=f"Pack quantity {pack_quantity} already exists for this product",
            )

    def _ensure_unique_side_table_option(
        self,
        product_id: int,
        includes_side_table: bool | None,
        exclude_variant_id: int | None = None,
    ) -> None:
        if includes_side_table is None:
            return
        stmt = select(ProductVariant.id).where(
            ProductVariant.product_id == product_id,
            ProductVariant.includes_side_table == includes_side_table,
        )
        if exclude_variant_id is not None:
            stmt = stmt.where(ProductVariant.id != exclude_variant_id)
        if self.db.scalar(stmt):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Side table option includesSideTable={includes_side_table} "
                    "already exists for this product"
                ),
            )

    def add_product_variant(self, product_id: int, payload: ProductVariantCreate) -> Product:
        product = self._get_product_or_404(product_id)
        self._ensure_unique_variant_sku(payload.sku)
        self._ensure_unique_seating_capacity(product_id, payload.seating_capacity)
        self._ensure_unique_pack_quantity(product_id, payload.pack_quantity)
        self._ensure_unique_side_table_option(product_id, payload.includes_side_table)

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

        if "pack_quantity" in update_data:
            self._ensure_unique_pack_quantity(
                product_id,
                update_data["pack_quantity"],
                exclude_variant_id=variant_id,
            )

        if "includes_side_table" in update_data:
            self._ensure_unique_side_table_option(
                product_id,
                update_data["includes_side_table"],
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
