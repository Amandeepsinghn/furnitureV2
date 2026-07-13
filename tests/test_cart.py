def test_add_to_cart(client, test_user, auth_headers, test_product):
    response = client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": test_product.id, "quantity": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == test_product.id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["product_name"] == test_product.name


def test_add_same_product_increases_quantity(client, test_user, auth_headers, test_product):
    client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": test_product.id, "quantity": 1},
    )
    response = client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": test_product.id, "quantity": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["quantity"] == 3
    assert data["total_items"] == 3


def test_get_cart(client, test_user, auth_headers, test_product):
    client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": test_product.id, "quantity": 1},
    )
    response = client.get("/api/v1/cart", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert float(data["subtotal"]) == float(test_product.price)


def test_add_to_cart_product_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": 999999, "quantity": 1},
    )
    assert response.status_code == 404


def test_cart_requires_auth(client, test_product):
    response = client.post(
        "/api/v1/cart/items",
        json={"product_id": test_product.id, "quantity": 1},
    )
    assert response.status_code == 401
