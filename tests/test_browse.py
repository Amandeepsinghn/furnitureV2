def test_list_categories(client, test_category):
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert any(category["slug"] == test_category.slug for category in data)


def test_get_category_by_slug(client, test_category):
    response = client.get(f"/api/v1/categories/{test_category.slug}")
    assert response.status_code == 200
    assert response.json()["name"] == test_category.name


def test_get_category_not_found(client):
    response = client.get("/api/v1/categories/does-not-exist")
    assert response.status_code == 404


def test_list_products_by_category(client, test_category, test_product):
    response = client.get(f"/api/v1/categories/{test_category.slug}/products")
    assert response.status_code == 200
    data = response.json()
    assert data["category"]["slug"] == test_category.slug
    assert data["total"] >= 1
    assert any(product["slug"] == test_product.slug for product in data["products"])


def test_get_product_by_slug(client, test_product):
    response = client.get(f"/api/v1/products/{test_product.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_product.name
    assert len(data["images"]) == 1


def test_get_product_not_found(client):
    response = client.get("/api/v1/products/does-not-exist")
    assert response.status_code == 404


def test_list_featured_products(client, test_product):
    response = client.get("/api/v1/products?featured=true")
    assert response.status_code == 200
    data = response.json()
    assert any(product["slug"] == test_product.slug for product in data)
