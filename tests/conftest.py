import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.schemas import Cart, CartItem, Category, Product, ProductImage, ProductVariant, User
from app.main import app


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture(autouse=True)
def mock_email_service(monkeypatch: pytest.MonkeyPatch) -> None:
    def noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        "app.services.email.email_service.EmailService.send_cart_notification",
        noop,
    )


@pytest.fixture(autouse=True)
def mock_cloudinary_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_upload_image(self, file, *, folder: str = "furniture/products"):
        return {
            "url": f"https://res.cloudinary.com/demo/image/upload/{folder}/test.jpg",
            "public_id": f"{folder}/test_{uuid.uuid4().hex[:8]}",
        }

    async def fake_upload_images(self, files, *, folder: str = "furniture/products"):
        return [await fake_upload_image(self, file, folder=folder) for file in files]

    monkeypatch.setattr(
        "app.services.cloudinary.cloudinary_service.CloudinaryService.upload_image",
        fake_upload_image,
    )
    monkeypatch.setattr(
        "app.services.cloudinary.cloudinary_service.CloudinaryService.upload_images",
        fake_upload_images,
    )
    monkeypatch.setattr(
        "app.services.cloudinary.cloudinary_service.CloudinaryService.delete_image",
        lambda self, public_id: None,
    )


@pytest.fixture
def test_category(db: Session, unique_suffix: str) -> Generator[Category, None, None]:
    category = Category(
        name=f"Test Chairs {unique_suffix}",
        slug=f"test-chairs-{unique_suffix}",
        description="Test category",
        is_active=True,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    yield category
    db.execute(delete(Product).where(Product.category_id == category.id))
    db.delete(category)
    db.commit()


@pytest.fixture
def test_product(db: Session, test_category: Category, unique_suffix: str) -> Generator[Product, None, None]:
    product = Product(
        category_id=test_category.id,
        name=f"Test Chair {unique_suffix}",
        slug=f"test-chair-{unique_suffix}",
        short_description="Comfortable test chair",
        price=4999.00,
        currency="INR",
        material="Wood",
        is_featured=True,
        is_active=True,
        stock_quantity=10,
    )
    product.images.append(
        ProductImage(
            url="https://res.cloudinary.com/demo/image/upload/chair.jpg",
            public_id=f"test/chair_{unique_suffix}",
            is_primary=True,
        )
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    yield product
    db.execute(delete(CartItem).where(CartItem.product_id == product.id))
    db.execute(delete(ProductImage).where(ProductImage.product_id == product.id))
    db.execute(delete(ProductVariant).where(ProductVariant.product_id == product.id))
    db.delete(product)
    db.commit()


@pytest.fixture
def test_user(client: TestClient, unique_suffix: str, db: Session) -> Generator[dict, None, None]:
    payload = {
        "email": f"testuser_{unique_suffix}@example.com",
        "password": "testpassword123",
        "full_name": f"Test User {unique_suffix}",
        "phone": "9876543210",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    user = db.scalar(select(User).where(User.email == payload["email"]))
    assert user is not None
    yield {
        "email": payload["email"],
        "password": payload["password"],
        "full_name": payload["full_name"],
        "access_token": data["access_token"],
        "id": user.id,
    }
    if user:
        db.execute(delete(CartItem).where(CartItem.cart_id.in_(select(Cart.id).where(Cart.user_id == user.id))))
        db.execute(delete(Cart).where(Cart.user_id == user.id))
        db.delete(user)
        db.commit()


@pytest.fixture
def auth_headers(test_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {test_user['access_token']}"}
