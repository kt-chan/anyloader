import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import os
import time
import uuid
from src.server.main import app, uploaded_files_store, tasks_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Clear stores
    uploaded_files_store.clear()
    tasks_store.clear()
    # Truncate DB
    client.post("/truncate")
    yield

def test_health_check():
    """Test the /health status endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_truncate_database():
    """Test the /truncate endpoint."""
    # First, upload and "process" something to ensure table exists (mocked or real)
    # Actually, /truncate just drops the table if it exists.
    response = client.post("/truncate")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_upload_file():
    """Test the /upload_file endpoint."""
    file_content = b"This is a test document for Anyloader RAG flow."
    files = {"file": ("test.txt", file_content, "text/plain")}
    response = client.post("/upload_file", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "test.txt"
    assert data["size"] == len(file_content)
    assert data["extension"] == "txt"

@patch("src.server.main.background_process_file", new_callable=MagicMock)
def test_process_file(mock_bg_task):
    """Test the /process endpoint."""
    # First upload
    file_content = b"Content for processing."
    files = {"file": ("proc_test.txt", file_content, "text/plain")}
    upload_res = client.post("/upload_file", files=files)
    file_id = upload_res.json()["id"]

    # Then process
    payload = {
        "file_id": file_id,
        "input_tags": {
            "academic_year": 2024,
            "department": "CS"
        }
    }
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    # Verify background task was called (though it's wrapped in BackgroundTasks)
    # Since we use TestClient, we can't easily check mock_bg_task if it runs in a background thread
    # But we can check if it's in the tasks_store
    assert data["task_id"] in tasks_store

def test_process_status():
    """Test the /process/status endpoint."""
    # Manually insert a task
    task_id = str(uuid.uuid4())
    tasks_store[task_id] = {"status": "COMPLETED", "error": None}
    
    response = client.get(f"/process/status/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "COMPLETED"

def test_process_status_not_found():
    """Test /process/status with invalid task_id."""
    response = client.get("/process/status/non-existent-task")
    assert response.status_code == 404

@patch("src.server.main.get_embedding", new_callable=AsyncMock)
def test_search_chunks(mock_embedding):
    """Test the /search_chunks endpoint."""
    # Mock embedding response
    mock_embedding.return_value = [0.1] * 1536 # Example vector length
    
    # We need some data in LanceDB to search. 
    # Instead of real background processing, let's manually inject into LanceDB if possible,
    # or just rely on the fact that if it's empty it returns empty list.
    
    # Let's try to do a real process with mocked embeddings to populate DB
    file_content = b"The quick brown fox jumps over the lazy dog."
    files = {"file": ("search_test.txt", file_content, "text/plain")}
    upload_res = client.post("/upload_file", files=files)
    file_id = upload_res.json()["id"]
    
    # We need to mock the embedding call inside background_process_file too.
    # background_process_file uses httpx.AsyncClient directly for batch embeddings.
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": [{"embedding": [0.1] * 1536}]}
        )
        
        client.post("/process", json={
            "file_id": file_id,
            "input_tags": {
                "academic_year": 2025,
                "department": "AI",
                "faculty": "Science",
                "degree_level": "undergraduate",
                "category": "course"
            }
        })
        
        # Wait for background task to complete in TestClient
        # TestClient runs background tasks before returning if configured, 
        # but here it might not. Let's poll tasks_store.
        
        max_retries = 10
        task_id = list(tasks_store.keys())[0]
        for _ in range(max_retries):
            if tasks_store[task_id]["status"] in ["COMPLETED", "FAILED"]:
                break
            time.sleep(0.5)
            
        assert tasks_store[task_id]["status"] == "COMPLETED"

        # Now Search
        payload = {
            "query": "fox",
            "tag_filters": {
                "exact": {
                    "department": "AI",
                    "faculty": "Science",
                    "degree_level": "undergraduate",
                    "category": "course"
                },
                "range": {"academic_year": [2024, 2026]},
                "fuzzy": {"doc_title": "search"}
            },
            "top_k": 5
        }
        response = client.post("/search_chunks", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result
            assert "metadata" in result
            assert result["metadata"]["department"] == "AI"
            assert result["metadata"]["faculty"] == "Science"
            assert result["metadata"]["degree_level"] == "undergraduate"
            assert result["metadata"]["category"] == "course"

@patch("src.server.main.get_embedding", new_callable=AsyncMock)
@patch("httpx.AsyncClient.post")
def test_query_rag(mock_post, mock_embedding):
    """Test the /query endpoint."""
    # 1. Mock Search results (by mocking search_chunks internals or just having data)
    # To keep it simple, let's mock search_chunks by ensuring it finds nothing or something.
    # Actually, /query calls search_chunks.
    
    mock_embedding.return_value = [0.1] * 1536
    
    # Mock LLM response
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "choices": [
                {"message": {"content": "The fox is quick and brown."}}
            ]
        }
    )
    
    # We need to ensure search_chunks returns something or we get the "I couldn't find..." answer.
    # Let's test the "no results" case first.
    payload = {
        "query": "What color is the fox?",
        "top_k": 5
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    # Since DB is truncated, it should return "I couldn't find..."
    assert "couldn't find" in data["answer"] or "The fox is quick" in data["answer"]

def test_process_invalid_file_id():
    """Test /process with non-existent file_id."""
    payload = {"file_id": 9999, "input_tags": {}}
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    assert tasks_store[task_id]["status"] == "FAILED"
    assert "not found" in tasks_store[task_id]["error"]
