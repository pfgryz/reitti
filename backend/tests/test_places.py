from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_list_places():
    res = client.get("/places")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if data:
        place = data[0]
        assert "name" in place
        assert "lat" in place
        assert "lng" in place
        assert "hours" in place
