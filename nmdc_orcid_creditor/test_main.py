from fastapi.testclient import TestClient

from nmdc_orcid_creditor.main import app

client = TestClient(app)


def test_get_greeting():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"greeting": "Hello world"}
