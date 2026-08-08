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


def test_create_sofa_with_seating_options_field(client, test_category, unique_suffix, db):
    from sqlalchemy import delete

    from app.db.schemas import Product, ProductVariant

    response = client.post(
        "/api/v1/products",
        json={
            "category_id": test_category.id,
            "name": f"Emerald Shell Velvet Sofa {unique_suffix}",
            "compare_at_price": 69999,
            "seatingOptions": [
                {"seatingCapacity": 3, "price": 29999, "label": "3 Seater"},
                {"seatingCapacity": 5, "price": 44999, "label": "5 Seater"},
                {"seatingCapacity": 7, "price": 59999, "label": "7 Seater"},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert float(data["price"]) == 29999
    assert [o["seatingCapacity"] for o in data["seatingOptions"]] == [3, 5, 7]
    assert float(data["seatingOptions"][1]["price"]) == 44999

    update = client.patch(
        f"/api/v1/products/{data['id']}",
        json={
            "seatingOptions": [
                {"seatingCapacity": 3, "price": 31999, "label": "3 Seater"},
                {"seatingCapacity": 5, "price": 46999, "label": "5 Seater"},
                {"seatingCapacity": 7, "price": 62999, "label": "7 Seater"},
            ]
        },
    )
    assert update.status_code == 200
    updated = update.json()
    assert float(updated["seatingOptions"][0]["price"]) == 31999
    assert float(updated["seatingOptions"][2]["price"]) == 62999

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


def test_create_chair_with_quantity_options_field(client, test_category, unique_suffix, db):
    from sqlalchemy import delete

    from app.db.schemas import Product, ProductVariant

    response = client.post(
        "/api/v1/products",
        json={
            "category_id": test_category.id,
            "name": f"Luxury Cane Back Bar Stool {unique_suffix}",
            "compare_at_price": 50000,
            "quantityOptions": [
                {"quantity": 1, "price": 15, "label": "1 Chair"},
                {"quantity": 2, "price": 28, "label": "2 Chairs"},
                {"quantity": 3, "price": 40, "label": "3 Chairs"},
                {"quantity": 4, "price": 52, "label": "4 Chairs"},
                {"quantity": 5, "price": 64, "label": "5 Chairs"},
                {"quantity": 6, "price": 75, "label": "6 Chairs"},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert float(data["price"]) == 15
    assert [o["quantity"] for o in data["quantityOptions"]] == [1, 2, 3, 4, 5, 6]
    assert float(data["quantityOptions"][0]["price"]) == 15
    assert float(data["quantityOptions"][1]["price"]) == 28
    assert data["quantityOptions"][0]["variantId"] is not None

    update = client.patch(
        f"/api/v1/products/{data['id']}",
        json={
            "quantityOptions": [
                {"quantity": 1, "price": 16, "label": "1 Chair"},
                {"quantity": 2, "price": 30, "label": "2 Chairs"},
                {"quantity": 3, "price": 42, "label": "3 Chairs"},
                {"quantity": 4, "price": 54, "label": "4 Chairs"},
                {"quantity": 5, "price": 66, "label": "5 Chairs"},
                {"quantity": 6, "price": 78, "label": "6 Chairs"},
            ]
        },
    )
    assert update.status_code == 200
    updated = update.json()
    assert float(updated["quantityOptions"][0]["price"]) == 16
    assert float(updated["quantityOptions"][1]["price"]) == 30

    browse = client.get(f"/api/v1/products/{data['slug']}")
    assert browse.status_code == 200
    assert [o["quantity"] for o in browse.json()["quantityOptions"]] == [1, 2, 3, 4, 5, 6]
    assert float(browse.json()["quantityOptions"][1]["price"]) == 30

    db.execute(delete(ProductVariant).where(ProductVariant.product_id == data["id"]))
    db.execute(delete(Product).where(Product.id == data["id"]))
    db.commit()


def test_add_update_delete_pack_quantity_variant(client, test_product, unique_suffix):
    add_response = client.post(
        f"/api/v1/products/{test_product.id}/variants",
        json={
            "sku": f"QTY-1-{unique_suffix}",
            "name": "1 Chair",
            "pack_quantity": 1,
            "size_label": "1 Chair",
            "price": 15,
        },
    )
    assert add_response.status_code == 201
    variants = add_response.json()["variants"]
    assert len(variants) == 1
    variant_id = variants[0]["id"]
    assert variants[0]["pack_quantity"] == 1

    update_response = client.patch(
        f"/api/v1/products/{test_product.id}/variants/{variant_id}",
        json={"price": 28, "pack_quantity": 2, "name": "2 Chairs"},
    )
    assert update_response.status_code == 200
    updated = next(v for v in update_response.json()["variants"] if v["id"] == variant_id)
    assert float(updated["price"]) == 28
    assert updated["pack_quantity"] == 2

    dup_response = client.post(
        f"/api/v1/products/{test_product.id}/variants",
        json={
            "sku": f"QTY-2-DUP-{unique_suffix}",
            "name": "2 Chairs Dup",
            "pack_quantity": 2,
            "price": 30,
        },
    )
    assert dup_response.status_code == 409

    delete_response = client.delete(
        f"/api/v1/products/{test_product.id}/variants/{variant_id}"
    )
    assert delete_response.status_code == 204


def test_create_bed_with_side_table_options(client, test_category, unique_suffix, db):
    from sqlalchemy import delete

    from app.db.schemas import Product, ProductVariant

    response = client.post(
        "/api/v1/products",
        json={
            "category_id": test_category.id,
            "name": f"Crown Arch Upholstered Bed {unique_suffix}",
            "compare_at_price": 75999,
            "sideTableOptions": [
                {
                    "includesSideTable": False,
                    "price": 39999,
                    "label": "Without side table",
                },
                {
                    "includesSideTable": True,
                    "price": 45999,
                    "label": "With side table",
                },
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert float(data["price"]) == 39999
    assert len(data["sideTableOptions"]) == 2
    by_flag = {o["includesSideTable"]: o for o in data["sideTableOptions"]}
    assert float(by_flag[False]["price"]) == 39999
    assert float(by_flag[True]["price"]) == 45999
    assert by_flag[True]["label"] == "With side table"

    update = client.patch(
        f"/api/v1/products/{data['id']}",
        json={
            "sideTableOptions": [
                {
                    "includesSideTable": False,
                    "price": 38999,
                    "label": "Without side table",
                },
                {
                    "includesSideTable": True,
                    "price": 47999,
                    "label": "With side table",
                },
            ]
        },
    )
    assert update.status_code == 200
    updated = {o["includesSideTable"]: o for o in update.json()["sideTableOptions"]}
    assert float(updated[False]["price"]) == 38999
    assert float(updated[True]["price"]) == 47999

    browse = client.get(f"/api/v1/products/{data['slug']}")
    assert browse.status_code == 200
    browse_opts = {o["includesSideTable"]: o for o in browse.json()["sideTableOptions"]}
    assert float(browse_opts[True]["price"]) == 47999
    assert browse_opts[False]["variantId"] is not None

    db.execute(delete(ProductVariant).where(ProductVariant.product_id == data["id"]))
    db.execute(delete(Product).where(Product.id == data["id"]))
    db.commit()


def test_add_update_delete_side_table_variant(client, test_product, unique_suffix):
    add_response = client.post(
        f"/api/v1/products/{test_product.id}/variants",
        json={
            "sku": f"BED-NO-ST-{unique_suffix}",
            "name": "Without side table",
            "includes_side_table": False,
            "size_label": "Without side table",
            "price": 39999,
        },
    )
    assert add_response.status_code == 201
    variants = add_response.json()["variants"]
    assert len(variants) == 1
    variant_id = variants[0]["id"]
    assert variants[0]["includes_side_table"] is False

    update_response = client.patch(
        f"/api/v1/products/{test_product.id}/variants/{variant_id}",
        json={
            "price": 45999,
            "includes_side_table": True,
            "name": "With side table",
        },
    )
    assert update_response.status_code == 200
    updated = next(v for v in update_response.json()["variants"] if v["id"] == variant_id)
    assert float(updated["price"]) == 45999
    assert updated["includes_side_table"] is True

    dup_response = client.post(
        f"/api/v1/products/{test_product.id}/variants",
        json={
            "sku": f"BED-ST-DUP-{unique_suffix}",
            "name": "With side table Dup",
            "includes_side_table": True,
            "price": 47000,
        },
    )
    assert dup_response.status_code == 409

    delete_response = client.delete(
        f"/api/v1/products/{test_product.id}/variants/{variant_id}"
    )
    assert delete_response.status_code == 204
