def test_signup_success(client, test_user):
    assert test_user["access_token"]
    assert test_user["email"].startswith("testuser_")


def test_signup_duplicate_email_returns_409(client, test_user):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user["email"],
            "password": "anotherpassword123",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid credentials"


def test_signup_short_password_rejected(client, unique_suffix):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"shortpw_{unique_suffix}@example.com",
            "password": "short",
            "full_name": "Short Password User",
        },
    )
    assert response.status_code == 422
