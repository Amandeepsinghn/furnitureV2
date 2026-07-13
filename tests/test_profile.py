def test_get_profile_success(client, test_user, auth_headers):
    response = client.get("/api/v1/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["full_name"] == test_user["full_name"]
    assert data["role"] == "customer"
    assert "hashed_password" not in data


def test_get_profile_unauthorized(client):
    response = client.get("/api/v1/profile")
    assert response.status_code == 401


def test_get_profile_invalid_token(client):
    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
