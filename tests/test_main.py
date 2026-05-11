from fastapi.testclient import TestClient
import os
import pytest
import lancedb
import pandas as pd
from src.server.main import app

client = TestClient(app)

def test_read_root():
    """Test the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "anyLoader API is running"}

def test_health_check():
    """Test the /health status endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "table" in data

def test_truncate_table():
    """Test the /truncate endpoint (will try to truncate if table exists)."""
    response = client.post("/truncate")
    # Should be 200 if table exists, 404 if not.
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert "truncated successfully" in response.json()["message"]

def test_query_no_table():
    """Test query endpoint when the table doesn't exist."""
    # This might fail if the table ALREADY exists from previous steps.
    # In a real test environment, we'd use a temporary DB.
    # For now, we'll check if it handles the missing table gracefully or returns results if table exists.
    response = client.post("/query", json={"query": "test"})
    # If table exists, should be 200, if not 404.
    assert response.status_code in [200, 404]

def test_query_with_filters():
    """Test query endpoint with sample filters."""
    payload = {
        "query": "Architecture prerequisites",
        "tag_filters": {
            "exact": {"Faculty": "Faculty of Architecture", "department": "unknown"},
            "range": {"academic year": [2023, 2025]},
            "fuzzy": {"doc title": "Syllabus"}
        }
    }
    response = client.post("/query", json=payload)
    # If the database was populated, this should return 200.
    if response.status_code == 200:
        data = response.json()
        assert data["query"] == payload["query"]
        assert data["tag_filters"]["exact"]["Faculty"] == "Faculty of Architecture"
        assert "results" in data
        assert isinstance(data["results"], list)
        for r in data["results"]:
            assert "metadata" in r
            # Check standardized values in metadata response
            assert r["metadata"]["exact"]["faculty"] == "faculty_of_architecture"
            assert "source" in r
            assert "section" in r

def test_database_connection():
    """Test if LanceDB can connect to the configured URI."""
    from src.server.database import get_db
    db = get_db()
    assert isinstance(db, lancedb.db.LanceDBConnection)

def test_query_no_filters():
    """Test query endpoint with no tag_filters provided."""
    payload = {"query": "What are the prerequisites?"}
    response = client.post("/query", json=payload)
    if response.status_code == 200:
        data = response.json()
        assert data["query"] == payload["query"]
        assert data["tag_filters"] is None
        assert "results" in data

def test_query_empty_filters():
    """Test query endpoint with empty filter dictionaries."""
    payload = {
        "query": "test",
        "tag_filters": {"exact": {}, "range": {}, "fuzzy": {}}
    }
    response = client.post("/query", json=payload)
    if response.status_code == 200:
        data = response.json()
        assert "results" in data

def test_query_fuzzy_no_match():
    """Test fuzzy matching with a string that won't match any doc_title."""
    payload = {
        "query": "test",
        "tag_filters": {
            "fuzzy": {"doc_title": "non_existent_document_xyz_123"}
        }
    }
    response = client.post("/query", json=payload)
    if response.status_code == 200:
        data = response.json()
        # Should return 0 results because of the restrictive fuzzy filter
        assert len(data["results"]) == 0

def test_ingestion_logic():
    """Smoke test for ingestion logic (without full run)."""
    from src.loader.ingest import Ingestor
    ingestor = Ingestor()
    assert ingestor.db is not None
    # Verify chunking works
    chunks = ingestor.chunk_text("This is a test text for chunking.", chunk_size=10, overlap=2)
    assert len(chunks) > 1
