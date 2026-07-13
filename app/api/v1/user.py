from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db
from app.db.schemas import Category, Product, User
from app.schemas.cart import AddToCartRequest, CartResponse
from app.schemas.category import CategoryProductsResponse, CategoryResponse
from app.schemas.product import ProductResponse, ProductSummaryResponse
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
    )


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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CategoryProductsResponse:
    category = db.scalar(
        select(Category).where(Category.slug == slug, Category.is_active.is_(True))
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    base_filter = (
        Product.category_id == category.id,
        Product.is_active.is_(True),
    )

    total = db.scalar(
        select(func.count()).select_from(Product).where(*base_filter)
    ) or 0

    stmt = (
        select(Product)
        .where(*base_filter)
        .options(selectinload(Product.images))
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


@router.get("/products/{slug}", response_model=ProductResponse)
def get_product(slug: str, db: Session = Depends(get_db)) -> Product:
    product = db.scalar(
        select(Product)
        .where(Product.slug == slug, Product.is_active.is_(True))
        .options(selectinload(Product.images), selectinload(Product.variants))
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/products", response_model=list[ProductSummaryResponse])
def list_featured_products(
    featured: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ProductSummaryResponse]:
    filters = [Product.is_active.is_(True)]
    if featured:
        filters.append(Product.is_featured.is_(True))

    stmt = (
        select(Product)
        .where(*filters)
        .options(selectinload(Product.images))
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
