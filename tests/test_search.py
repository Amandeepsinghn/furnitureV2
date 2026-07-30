def test_search_products(client, test_product):
    response = client.get("/api/v1/products/search", params={"q": test_product.name.split()[0]})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(p["id"] == test_product.id for p in data["products"])
    assert any(p["productId"] == test_product.id for p in data["products"])


def test_search_products_by_category(client, test_category, test_product):
    response = client.get(
        "/api/v1/products/search",
        params={"q": test_product.name.split()[0], "category": test_category.slug},
    )
    assert response.status_code == 200
    data = response.json()
    assert any(p["id"] == test_product.id for p in data["products"])


def test_search_within_category(client, test_category, test_product):
    response = client.get(
        f"/api/v1/categories/{test_category.slug}/products",
        params={"q": test_product.name.split()[0]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(p["id"] == test_product.id for p in data["products"])


def test_search_no_results(client):
    response = client.get(
        "/api/v1/products/search",
        params={"q": "zzzz-no-such-product-xyz"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["products"] == []
