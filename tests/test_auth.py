import pytest

@pytest.mark.parametrize("lang, expected_message", [
    ("fr", "Adresse e-mail invalide."),
    ("en", "Invalid e-mail address.")
])
def test_login_with_reserved_domain_is_translated(client, lang, expected_message):
    response = client.post(
        "/api/login",
        json={"email": "someone@test.local", "password": "password"},
        headers={"Accept-Language": lang}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == expected_message
    assert response.json()["code"] == "auth.invalid_email"
    response_forgot = client.post(
        "/api/forgot-password",
        json={"email": "someone@test.local"},
        headers={"Accept-Language": lang}
    )
    assert response_forgot.status_code == 422
    assert response_forgot.json()["detail"] == expected_message
    assert response_forgot.json()["code"] == "auth.invalid_email"
