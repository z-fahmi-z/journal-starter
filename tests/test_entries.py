from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_entries_endpoint():
    response = client.get("/entries")
    assert response.status_code == 200
