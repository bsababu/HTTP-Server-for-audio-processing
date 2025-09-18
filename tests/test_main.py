import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.storage import Storage

# Test client
client = TestClient(app)

# Test data
TEST_USER_ID = "test_user"
TEST_AUDIO_CONTENT = b"fake audio content for testing"


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Replace the global storage instance
        import app.main
        original_storage = app.main.storage
        temp_storage_instance = Storage(base_path=temp_dir)
        
        # Create the metadata file manually for testing
        os.makedirs(temp_storage_instance.uploads_path, exist_ok=True)
        with open(temp_storage_instance.metadata_path, 'w') as f:
            f.write('[]')
        
        app.main.storage = temp_storage_instance
        
        yield temp_storage_instance
        
        # Restore original storage
        app.main.storage = original_storage


def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_audio(temp_storage):
    """Test audio upload"""
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {
        "user_id": TEST_USER_ID,
        "tags": "music,test",
        "title": "Test Song",
        "artist": "Test Artist"
    }
    
    response = client.post("/upload", files=files, data=data)
    assert response.status_code == 200
    
    json_response = response.json()
    assert json_response["status"] == "ok"
    assert "id" in json_response


def test_upload_missing_user_id():
    """Test upload without user_id"""
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 422  # Validation error


def test_list_empty_user(temp_storage):
    """Test listing files for user with no uploads"""
    response = client.get(f"/list?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    
    json_response = response.json()
    assert json_response["user_id"] == TEST_USER_ID
    assert json_response["count"] == 0
    assert json_response["items"] == []


def test_list_with_uploads(temp_storage):
    """Test listing files after upload"""
    # First upload a file
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {"user_id": TEST_USER_ID, "tags": "music,test"}
    upload_response = client.post("/upload", files=files, data=data)
    assert upload_response.status_code == 200
    
    # Then list files
    response = client.get(f"/list?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    
    json_response = response.json()
    assert json_response["count"] == 1
    assert len(json_response["items"]) == 1
    assert json_response["items"][0]["filename"] == "test.mp3"


def test_list_with_tag_filter(temp_storage):
    """Test listing files with tag filter"""
    # Upload file with specific tag
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {"user_id": TEST_USER_ID, "tags": "music,rock"}
    client.post("/upload", files=files, data=data)
    
    # List with matching tag
    response = client.get(f"/list?user_id={TEST_USER_ID}&tag=music")
    assert response.status_code == 200
    assert response.json()["count"] == 1
    
    # List with non-matching tag
    response = client.get(f"/list?user_id={TEST_USER_ID}&tag=jazz")
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_download_no_files(temp_storage):
    """Test download for user with no files"""
    response = client.get(f"/download?user_id={TEST_USER_ID}")
    assert response.status_code == 404
    assert "no uploads found" in response.json()["detail"]


def test_download_with_files(temp_storage):
    """Test download with files"""
    # Upload a file first
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {"user_id": TEST_USER_ID, "tags": "music"}
    client.post("/upload", files=files, data=data)
    
    # Download files
    response = client.get(f"/download?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_get_file_info(temp_storage):
    """Test getting file info"""
    # Upload a file first
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {"user_id": TEST_USER_ID, "title": "Test Song"}
    upload_response = client.post("/upload", files=files, data=data)
    file_id = upload_response.json()["id"]
    
    # Get file info
    response = client.get(f"/files/{file_id}/info?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    
    json_response = response.json()
    assert json_response["id"] == file_id
    assert json_response["filename"] == "test.mp3"
    assert json_response["title"] == "Test Song"


def test_get_file_info_not_found(temp_storage):
    """Test getting info for non-existent file"""
    response = client.get(f"/files/nonexistent/info?user_id={TEST_USER_ID}")
    assert response.status_code == 404


def test_download_individual_file(temp_storage):
    """Test downloading individual file"""
    # Upload a file first
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {"user_id": TEST_USER_ID}
    upload_response = client.post("/upload", files=files, data=data)
    file_id = upload_response.json()["id"]
    
    # Download the file
    response = client.get(f"/files/{file_id}?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    assert response.content == TEST_AUDIO_CONTENT


def test_delete_file(temp_storage):
    """Test deleting a file"""
    # Upload a file first
    files = {"audio": ("test.mp3", TEST_AUDIO_CONTENT, "audio/mpeg")}
    data = {"user_id": TEST_USER_ID}
    upload_response = client.post("/upload", files=files, data=data)
    file_id = upload_response.json()["id"]
    
    # Delete the file
    response = client.delete(f"/files/{file_id}?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    
    # Verify file is gone
    response = client.get(f"/files/{file_id}/info?user_id={TEST_USER_ID}")
    assert response.status_code == 404


def test_delete_nonexistent_file(temp_storage):
    """Test deleting non-existent file"""
    response = client.delete(f"/files/nonexistent?user_id={TEST_USER_ID}")
    assert response.status_code == 404


def test_missing_user_id_endpoints():
    """Test endpoints without required user_id parameter"""
    # List endpoint
    response = client.get("/list")
    assert response.status_code == 422
    
    # Download endpoint  
    response = client.get("/download")
    assert response.status_code == 422
    
    # File info endpoint
    response = client.get("/files/test_id/info")
    assert response.status_code == 422
