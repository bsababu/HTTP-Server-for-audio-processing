import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_storage():
    with patch('app.main.storage') as mock:
        mock.list_user_uploads = AsyncMock()
        mock.store_file = AsyncMock()
        mock.delete_file = AsyncMock()
        mock.get_user_file_path = AsyncMock()
        yield mock

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_uploads_no_userid():
    response = client.get("/list")
    assert response.status_code == 422

def test_list_uploads_empty(mock_storage):
    mock_storage.list_user_uploads.return_value = []
    response = client.get("/list?user_id=test_user")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user"
    assert data["count"] == 0
    assert data["items"] == []

def test_upload_no_userid():
    response = client.post("/upload", data={})
    assert response.status_code == 422

def test_upload_no_file():
    response = client.post("/upload", data={"user_id": "test_user"})
    assert response.status_code == 422

def test_upload_success(mock_storage):
    mock_storage.store_file.return_value = "test-id-1"
    mock_storage.save_upload = AsyncMock()
    mock_storage.metadata_path = "/mock/metadata/path"

    test_file = io.BytesIO(b"test audio content")
    files = {"audio": ("test.mp3", test_file, "audio/mp3")}
    data = {
        "user_id": "test_user",
        "tags": "tag1,tag2",
        "title": "Test Song",
        "artist": "Test Artist",
        "description": "Test Description"
    }
    response = client.post("/upload", data=data, files=files)
    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["status"] == "ok"


def test_download_no_userid():
    response = client.get("/download")
    assert response.status_code == 422

def test_download_nonexistent_user(mock_storage):
    mock_storage.list_user_uploads.return_value = []
    mock_storage.get_user_file_path.side_effect = FileNotFoundError
    response = client.get("/download?user_id=nonexistent")
    assert response.status_code == 404

def test_get_file_no_userid():
    response = client.get("/files/some-id")
    assert response.status_code == 422

def test_get_file_not_found(mock_storage):
    mock_storage.list_user_uploads.return_value = []
    response = client.get("/files/nonexistent-id?user_id=test_user")
    assert response.status_code == 404

def test_delete_file_no_userid():
    response = client.delete("/files/some-id")
    assert response.status_code == 422

def test_delete_file_not_found(mock_storage):
    mock_storage.list_user_uploads.return_value = []
    response = client.delete("/files/nonexistent-id?user_id=test_user")
    assert response.status_code == 404

def test_file_info_no_userid():
    response = client.get("/files/some-id/info")
    assert response.status_code == 422

def test_file_info_not_found(mock_storage):
    mock_storage.list_user_uploads.return_value = []
    response = client.get("/files/nonexistent-id/info?user_id=test_user")
    assert response.status_code == 404