def test_create_product(client, test_category, unique_suffix, db):
    payload = {
        "category_id": test_category.id,
        "name": f"New Sofa {unique_suffix}",
        "price": 15999.00,
        "material": "Fabric",
        "stock_quantity": 5,
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["slug"] == f"new-sofa-{unique_suffix}"
    assert float(data["price"]) == payload["price"]

    from sqlalchemy import delete

    from app.db.schemas import Product

    db.execute(delete(Product).where(Product.id == data["id"]))
    db.commit()


def test_create_product_category_not_found(client, unique_suffix):
    response = client.post(
        "/api/v1/products",
        json={
            "category_id": 999999,
            "name": f"Ghost Product {unique_suffix}",
        },
    )
    assert response.status_code == 404


def test_create_product_duplicate_sku(client, test_category, test_product, db):
    from sqlalchemy import delete

    from app.db.schemas import Product

    test_product.sku = f"TEST-SKU-{test_product.id}"
    db.add(test_product)
    db.commit()

    response = client.post(
        "/api/v1/products",
        json={
            "category_id": test_category.id,
            "name": "Duplicate SKU Product",
            "sku": test_product.sku,
        },
    )
    assert response.status_code == 409


def test_create_product_with_images(client, test_category, unique_suffix, db):
    import json

    product_data = {
        "category_id": test_category.id,
        "name": f"Cloudinary Chair {unique_suffix}",
        "price": 7999.00,
    }
    response = client.post(
        "/api/v1/products/with-images",
        data={"data": json.dumps(product_data)},
        files=[("images", ("chair.jpg", b"fake-image-bytes", "image/jpeg"))],
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["images"]) == 1
    assert data["images"][0]["url"].startswith("https://res.cloudinary.com/")

    from sqlalchemy import delete

    from app.db.schemas import Product, ProductImage

    db.execute(delete(ProductImage).where(ProductImage.product_id == data["id"]))
    db.execute(delete(Product).where(Product.id == data["id"]))
    db.commit()
