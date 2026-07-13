from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.schemas import Cart, CartItem, Product, ProductVariant, User
from app.schemas.cart import AddToCartRequest, CartItemResponse, CartResponse
from app.services.email.email_service import EmailService


def get_primary_image_url(product: Product) -> str | None:
    for image in product.images:
        if image.is_primary:
            return image.url
    return product.images[0].url if product.images else None


def get_unit_price(product: Product, variant: ProductVariant | None) -> Decimal | None:
    if variant and variant.price is not None:
        return variant.price
    return product.price


class CartService:
    def __init__(self, session: Session, email_service: EmailService | None = None):
        self.db = session
        self.email_service = email_service or EmailService()

    def _get_or_create_cart(self, user: User) -> Cart:
        cart = self.db.scalar(select(Cart).where(Cart.user_id == user.id))
        if cart is not None:
            return cart

        cart = Cart(user_id=user.id)
        self.db.add(cart)
        self.db.flush()
        return cart

    def _find_cart_item(
        self,
        cart_id: int,
        product_id: int,
        variant_id: int | None,
    ) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )
        if variant_id is None:
            stmt = stmt.where(CartItem.variant_id.is_(None))
        else:
            stmt = stmt.where(CartItem.variant_id == variant_id)
        return self.db.scalar(stmt)

    def add_to_cart(self, user: User, payload: AddToCartRequest) -> CartResponse:
        product = self.db.scalar(
            select(Product)
            .where(Product.id == payload.product_id, Product.is_active.is_(True))
            .options(selectinload(Product.images))
        )
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        variant: ProductVariant | None = None
        if payload.variant_id is not None:
            variant = self.db.scalar(
                select(ProductVariant).where(
                    ProductVariant.id == payload.variant_id,
                    ProductVariant.product_id == product.id,
                    ProductVariant.is_active.is_(True),
                )
            )
            if variant is None:
                raise HTTPException(status_code=404, detail="Product variant not found")

        cart = self._get_or_create_cart(user)
        existing_item = self._find_cart_item(cart.id, product.id, payload.variant_id)
        is_new_item = existing_item is None

        if existing_item:
            existing_item.quantity += payload.quantity
            final_quantity = existing_item.quantity
        else:
            cart.items.append(
                CartItem(
                    product_id=product.id,
                    variant_id=payload.variant_id,
                    quantity=payload.quantity,
                )
            )
            final_quantity = payload.quantity

        self.db.commit()

        unit_price = get_unit_price(product, variant)
        self.email_service.send_cart_notification(
            user_name=user.full_name,
            user_email=user.email,
            product_name=product.name,
            quantity=final_quantity,
            variant_name=variant.name if variant else None,
            unit_price=str(unit_price) if unit_price is not None else None,
            is_new_item=is_new_item,
        )

        return self.get_cart(user)

    def get_cart(self, user: User) -> CartResponse:
        stmt = (
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.cart)
                .selectinload(Cart.items)
                .selectinload(CartItem.product)
                .selectinload(Product.images),
                selectinload(User.cart)
                .selectinload(Cart.items)
                .selectinload(CartItem.variant),
            )
        )
        user_with_cart = self.db.scalar(stmt)
        if user_with_cart is None or user_with_cart.cart is None:
            return CartResponse(id=0, items=[], total_items=0, subtotal=Decimal("0"))

        cart = user_with_cart.cart
        items: list[CartItemResponse] = []
        subtotal = Decimal("0")
        total_items = 0

        for item in cart.items:
            unit_price = get_unit_price(item.product, item.variant)
            line_total = unit_price * item.quantity if unit_price is not None else None
            if line_total is not None:
                subtotal += line_total
            total_items += item.quantity

            items.append(
                CartItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=item.product.name,
                    product_slug=item.product.slug,
                    variant_id=item.variant_id,
                    variant_name=item.variant.name if item.variant else None,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    currency=item.product.currency,
                    primary_image_url=get_primary_image_url(item.product),
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

        return CartResponse(
            id=cart.id,
            items=items,
            total_items=total_items,
            subtotal=subtotal,
        )
