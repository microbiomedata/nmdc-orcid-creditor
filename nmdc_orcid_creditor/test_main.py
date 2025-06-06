from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from nmdc_orcid_creditor.main import app, validate_orcid_access_token

client = TestClient(app)


def test_get_root():
    response = client.get("/")
    assert response.status_code == 200


def test_get_redirect_to_orcid_login_page():
    # Test: Initial response is an HTTP redirect.
    response = client.get("/redirect-to-orcid-login-page", follow_redirects=False)
    assert response.is_redirect

    # Test: Ultimate destination is an ORCID URL.
    response = client.get("/redirect-to-orcid-login-page")
    assert response.url.host.endswith("orcid.org")


def test_get_exchange_code_for_token():
    # Test: With an insufficient request, endpoint returns error page.
    response = client.get("/exchange-code-for-token", follow_redirects=False)
    assert not response.is_redirect
    assert "Failed" in response.text

    # TODO: Add test involving a sufficient request (whatever ORCID would send).


def test_validate_orcid_access_token():
    # Generate some timestamps.
    one_minute_into_the_past = int((datetime.now() - timedelta(minutes=1)).timestamp())
    one_minute_into_the_future = int((datetime.now() + timedelta(minutes=1)).timestamp())

    # Test: Returns `None` if token has expired.
    orcid_access_token = dict(orcid_access_token="0000-0000-0000-0000", expires_at=one_minute_into_the_past)
    assert validate_orcid_access_token(orcid_access_token) is None

    # Test: Returns token if token has not expired.
    orcid_access_token = dict(orcid_access_token="0000-0000-0000-0000", expires_at=one_minute_into_the_future)
    assert isinstance(orcid_access_token, dict)


def test_logout():
    # Test: Initial response is an HTTP redirect.
    response = client.get("/logout", follow_redirects=False)
    assert response.is_redirect

    # Test: Ultimate destination is the home page.
    response = client.get("/logout")
    assert response.status_code == 200


def test_get_credits():
    # Test: If request lacks valid ORCID access token, redirects to home page.
    response = client.get("/credits", follow_redirects=False)
    assert response.is_redirect

    # Test: Ultimate destination is the home page.
    response = client.get("/credits")
    assert response.status_code == 200

    # TODO: Add test involving a sufficient request (one having a valid ORCID access token).


def test_get_api_credits():
    # Test: If request lacks valid ORCID access token, returns an HTTP 401 response.
    response = client.get("/api/credits")
    assert response.status_code == 401

    # TODO: Add test involving a sufficient request (one having a valid ORCID access token).


def test_post_api_credits_claim():
    # Test: If request lacks valid ORCID access token, returns an HTTP 401 response.
    response = client.post("/api/credits/claim", json=dict(
        credit_type="foo",
        start_date="2023-01-01T00:00:00Z",
        end_date="2023-12-31T23:59:59Z",
    ))
    assert response.status_code == 401

    # TODO: Add test involving a sufficient request (one having a valid ORCID access token).
