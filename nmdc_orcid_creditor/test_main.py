from fastapi.testclient import TestClient

from nmdc_orcid_creditor.main import app

client = TestClient(app)


def test_get_root():
    response = client.get("/")
    assert response.status_code == 200
