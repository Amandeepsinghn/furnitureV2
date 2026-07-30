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


def test_update_product(client, test_product):
    response = client.patch(
        f"/api/v1/products/{test_product.id}",
        json={"name": "Updated Chair", "price": 5999.00, "stock_quantity": 20},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Chair"
    assert float(data["price"]) == 5999.00
    assert data["stock_quantity"] == 20


def test_update_product_not_found(client):
    response = client.patch(
        "/api/v1/products/999999",
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


def test_delete_product(client, test_category, unique_suffix, db):
    from sqlalchemy import select

    from app.db.schemas import Product

    product = Product(
        category_id=test_category.id,
        name=f"Delete Me {unique_suffix}",
        slug=f"delete-me-{unique_suffix}",
        is_active=True,
        stock_quantity=1,
    )
    db.add(product)
    db.commit()
    product_id = product.id

    response = client.delete(f"/api/v1/products/{product_id}")
    assert response.status_code == 204

    deleted = db.scalar(select(Product).where(Product.id == product_id))
    assert deleted is None


def test_delete_product_not_found(client):
    response = client.delete("/api/v1/products/999999")
    assert response.status_code == 404


def test_create_sofa_with_seating_variants(client, test_category, unique_suffix, db):
    from sqlalchemy import delete

    from app.db.schemas import Product, ProductVariant

    response = client.post(
        "/api/v1/products",
        json={
            "category_id": test_category.id,
            "name": f"Emerald Shell Velvet Sofa {unique_suffix}",
            "price": 29999,
            "variants": [
                {
                    "sku": f"EMERALD-3S-{unique_suffix}",
                    "name": "3 Seater",
                    "seating_capacity": 3,
                    "size_label": "3 Seater",
                    "price": 29999,
                },
                {
                    "sku": f"EMERALD-5S-{unique_suffix}",
                    "name": "5 Seater",
                    "seating_capacity": 5,
                    "size_label": "5 Seater",
                    "price": 44999,
                },
                {
                    "sku": f"EMERALD-7S-{unique_suffix}",
                    "name": "7 Seater",
                    "seating_capacity": 7,
                    "size_label": "7 Seater",
                    "price": 59999,
                },
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["variants"]) == 3
    capacities = {v["seating_capacity"] for v in data["variants"]}
    assert capacities == {3, 5, 7}
    assert "seatingOptions" in data
    assert [o["seatingCapacity"] for o in data["seatingOptions"]] == [3, 5, 7]
    assert float(data["seatingOptions"][0]["price"]) == 29999
    assert float(data["seatingOptions"][1]["price"]) == 44999
    assert float(data["seatingOptions"][2]["price"]) == 59999

    detail = client.get(f"/api/v1/products/{data['slug']}")
    assert detail.status_code == 200
    detail_data = detail.json()
    assert [o["seatingCapacity"] for o in detail_data["seatingOptions"]] == [3, 5, 7]

    category_list = client.get(f"/api/v1/categories/{test_category.slug}/products")
    assert category_list.status_code == 200
    listed = next(p for p in category_list.json()["products"] if p["id"] == data["id"])
    assert [o["seatingCapacity"] for o in listed["seatingOptions"]] == [3, 5, 7]

    db.execute(delete(ProductVariant).where(ProductVariant.product_id == data["id"]))
    db.execute(delete(Product).where(Product.id == data["id"]))
    db.commit()


def test_add_update_delete_seating_variant(client, test_product, unique_suffix):
    add_response = client.post(
        f"/api/v1/products/{test_product.id}/variants",
        json={
            "sku": f"SEAT-3-{unique_suffix}",
            "name": "3 Seater",
            "seating_capacity": 3,
            "size_label": "3 Seater",
            "price": 29999,
        },
    )
    assert add_response.status_code == 201
    variants = add_response.json()["variants"]
    assert len(variants) == 1
    variant_id = variants[0]["id"]
    assert variants[0]["seating_capacity"] == 3

    update_response = client.patch(
        f"/api/v1/products/{test_product.id}/variants/{variant_id}",
        json={"price": 31999, "seating_capacity": 5, "name": "5 Seater"},
    )
    assert update_response.status_code == 200
    updated = next(v for v in update_response.json()["variants"] if v["id"] == variant_id)
    assert float(updated["price"]) == 31999
    assert updated["seating_capacity"] == 5

    # Duplicate seating capacity should fail
    dup_response = client.post(
        f"/api/v1/products/{test_product.id}/variants",
        json={
            "sku": f"SEAT-5-DUP-{unique_suffix}",
            "name": "5 Seater Dup",
            "seating_capacity": 5,
            "price": 40000,
        },
    )
    assert dup_response.status_code == 409

    delete_response = client.delete(
        f"/api/v1/products/{test_product.id}/variants/{variant_id}"
    )
    assert delete_response.status_code == 204
