from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db
from app.db.schemas import Category, Product, User
from app.schemas.cart import AddToCartRequest, CartResponse
from app.schemas.category import CategoryProductsResponse, CategoryResponse
from app.schemas.product import (
    ProductResponse,
    ProductSummaryResponse,
    QuantityOptionResponse,
    SeatingOptionResponse,
    SideTableOptionResponse,
)
from app.schemas.search import ProductSearchResponse
from app.schemas.user import UserProfileResponse
from app.services.cart.cart_service import CartService

router = APIRouter(tags=["browse"])


def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(session=db)


def get_primary_image_url(product: Product) -> str | None:
    for image in product.images:
        if image.is_primary:
            return image.url
    return product.images[0].url if product.images else None


def build_seating_options(product: Product) -> list[SeatingOptionResponse]:
    options: list[SeatingOptionResponse] = []
    for variant in product.variants:
        if not variant.is_active or variant.seating_capacity is None:
            continue
        options.append(
            SeatingOptionResponse(
                variantId=variant.id,
                seatingCapacity=variant.seating_capacity,
                label=variant.size_label or variant.name or f"{variant.seating_capacity} Seater",
                price=variant.price,
                compare_at_price=variant.compare_at_price
                if variant.compare_at_price is not None
                else product.compare_at_price,
                currency=product.currency,
                width_cm=variant.width_cm,
                height_cm=variant.height_cm,
                depth_cm=variant.depth_cm,
                is_active=variant.is_active,
            )
        )
    options.sort(key=lambda option: option.seatingCapacity)
    return options


def build_quantity_options(product: Product) -> list[QuantityOptionResponse]:
    options: list[QuantityOptionResponse] = []
    for variant in product.variants:
        if not variant.is_active or variant.pack_quantity is None:
            continue
        label = variant.size_label or variant.name
        if not label:
            label = "1 Chair" if variant.pack_quantity == 1 else f"{variant.pack_quantity} Chairs"
        options.append(
            QuantityOptionResponse(
                variantId=variant.id,
                quantity=variant.pack_quantity,
                label=label,
                price=variant.price,
                compare_at_price=variant.compare_at_price
                if variant.compare_at_price is not None
                else product.compare_at_price,
                currency=product.currency,
                is_active=variant.is_active,
            )
        )
    options.sort(key=lambda option: option.quantity)
    return options


def build_side_table_options(product: Product) -> list[SideTableOptionResponse]:
    options: list[SideTableOptionResponse] = []
    for variant in product.variants:
        if not variant.is_active or variant.includes_side_table is None:
            continue
        label = variant.size_label or variant.name
        if not label:
            label = "With side table" if variant.includes_side_table else "Without side table"
        options.append(
            SideTableOptionResponse(
                variantId=variant.id,
                includesSideTable=variant.includes_side_table,
                label=label,
                price=variant.price,
                compare_at_price=variant.compare_at_price
                if variant.compare_at_price is not None
                else product.compare_at_price,
                currency=product.currency,
                is_active=variant.is_active,
            )
        )
    options.sort(key=lambda option: option.includesSideTable)
    return options


def to_product_summary(product: Product) -> ProductSummaryResponse:
    return ProductSummaryResponse(
        id=product.id,
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        price=product.price,
        compare_at_price=product.compare_at_price,
        currency=product.currency,
        material=product.material,
        color=product.color,
        is_featured=product.is_featured,
        primary_image_url=get_primary_image_url(product),
        seatingOptions=build_seating_options(product),
        quantityOptions=build_quantity_options(product),
        sideTableOptions=build_side_table_options(product),
    )


def to_product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        short_description=product.short_description,
        sku=product.sku,
        price=product.price,
        compare_at_price=product.compare_at_price,
        currency=product.currency,
        material=product.material,
        color=product.color,
        style=product.style,
        room_type=product.room_type,
        width_cm=product.width_cm,
        height_cm=product.height_cm,
        depth_cm=product.depth_cm,
        weight_kg=product.weight_kg,
        extra_specs=product.extra_specs,
        is_featured=product.is_featured,
        is_active=product.is_active,
        stock_quantity=product.stock_quantity,
        created_at=product.created_at,
        updated_at=product.updated_at,
        images=product.images,
        variants=product.variants,
        seatingOptions=build_seating_options(product),
        quantityOptions=build_quantity_options(product),
        sideTableOptions=build_side_table_options(product),
    )


def product_with_images_and_variants():
    return (
        selectinload(Product.images),
        selectinload(Product.variants),
    )


def build_product_search_filters(
    *,
    q: str | None = None,
    category_id: int | None = None,
    material: str | None = None,
    color: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list:
    filters = [Product.is_active.is_(True)]

    if category_id is not None:
        filters.append(Product.category_id == category_id)

    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.slug.ilike(pattern),
                Product.description.ilike(pattern),
                Product.short_description.ilike(pattern),
                Product.material.ilike(pattern),
                Product.color.ilike(pattern),
                Product.style.ilike(pattern),
                Product.room_type.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    if material:
        filters.append(Product.material.ilike(f"%{material.strip()}%"))

    if color:
        filters.append(Product.color.ilike(f"%{color.strip()}%"))

    if min_price is not None:
        filters.append(Product.price >= min_price)

    if max_price is not None:
        filters.append(Product.price <= max_price)

    return filters


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    stmt = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.name)
    )
    return list(db.scalars(stmt).all())


@router.get("/categories/{slug}", response_model=CategoryResponse)
def get_category(slug: str, db: Session = Depends(get_db)) -> Category:
    category = db.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/categories/{slug}/products", response_model=CategoryProductsResponse)
def list_products_by_category(
    slug: str,
    q: str | None = Query(None, description="Search within this category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CategoryProductsResponse:
    category = db.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    filters = build_product_search_filters(q=q, category_id=category.id)

    total = db.scalar(
        select(func.count()).select_from(Product).where(*filters)
    ) or 0

    stmt = (
        select(Product)
        .where(*filters)
        .options(*product_with_images_and_variants())
        .order_by(Product.is_featured.desc(), Product.name)
        .offset(skip)
        .limit(limit)
    )
    products = list(db.scalars(stmt).all())

    return CategoryProductsResponse(
        category=CategoryResponse.model_validate(category),
        products=[to_product_summary(product) for product in products],
        total=total,
    )


@router.get("/products/search", response_model=ProductSearchResponse, tags=["search"])
def search_products(
    q: str | None = Query(None, min_length=1, description="Search text"),
    category: str | None = Query(None, description="Category slug filter, e.g. sofas"),
    material: str | None = Query(None),
    color: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ProductSearchResponse:
    category_id: int | None = None
    if category:
        category_row = db.scalar(
            select(Category).where(
                Category.slug == category,
                Category.is_active.is_(True),
            )
        )
        if category_row is None:
            raise HTTPException(status_code=404, detail="Category not found")
        category_id = category_row.id

    filters = build_product_search_filters(
        q=q,
        category_id=category_id,
        material=material,
        color=color,
        min_price=min_price,
        max_price=max_price,
    )

    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0

    stmt = (
        select(Product)
        .where(*filters)
        .options(*product_with_images_and_variants())
        .order_by(Product.is_featured.desc(), Product.name)
        .offset(skip)
        .limit(limit)
    )
    products = list(db.scalars(stmt).all())

    return ProductSearchResponse(
        query=q,
        products=[to_product_summary(product) for product in products],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/products/{slug}", response_model=ProductResponse)
def get_product(slug: str, db: Session = Depends(get_db)) -> ProductResponse:
    product = db.scalar(
        select(Product)
        .where(Product.slug == slug, Product.is_active.is_(True))
        .options(*product_with_images_and_variants())
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_product_response(product)


@router.get("/products", response_model=list[ProductSummaryResponse])
def list_featured_products(
    featured: bool = Query(True),
    q: str | None = Query(None, description="Optional search text"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ProductSummaryResponse]:
    filters = build_product_search_filters(q=q)
    if featured:
        filters.append(Product.is_featured.is_(True))

    stmt = (
        select(Product)
        .where(*filters)
        .options(*product_with_images_and_variants())
        .order_by(Product.name)
        .offset(skip)
        .limit(limit)
    )
    products = list(db.scalars(stmt).all())
    return [to_product_summary(product) for product in products]


@router.get("/profile", response_model=UserProfileResponse, tags=["profile"])
def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/cart/items", response_model=CartResponse, tags=["cart"])
def add_to_cart(
    payload: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return service.add_to_cart(current_user, payload)


@router.get("/cart", response_model=CartResponse, tags=["cart"])
def get_my_cart(
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return service.get_cart(current_user)
