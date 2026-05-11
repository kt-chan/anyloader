from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import lancedb
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# --- Configuration and Database Initialization ---
LANCEDB_URI = os.getenv("LANCEDB_URI", "./.lancedb")
TABLE_NAME = "course_prerequisites"
LLM_HOST_URL = os.getenv("LLM_HOST_URL")
LLM_API_KEY = os.getenv("API_KEY")
RAG_HOST_PATH = os.getenv("RAG_HOST_PATH", "0.0.0.0")
RAG_PORT = int(os.getenv("RAG_PORT", "8000"))

db = lancedb.connect(LANCEDB_URI)

# --- FastAPI App Initialization ---
app = FastAPI(title="anyLoader Course Prerequisite API")

# --- Pydantic Models ---
class TagFilters(BaseModel):
    exact: Optional[Dict[str, Any]] = Field(None, description="Exact match filters (e.g., {'faculty': 'Engineering'})")
    range: Optional[Dict[str, List[Any]]] = Field(None, description="Range filters (e.g., {'academic_year': [2023, 2025]})")
    fuzzy: Optional[Dict[str, str]] = Field(None, description="Fuzzy match filters (e.g., {'doc_title': 'Syllabus'})")

class QueryRequest(BaseModel):
    query: str = Field(..., description="The search query or question (e.g., 'What are the prerequisites?')")
    tag_filters: Optional[TagFilters] = Field(None, description="Optional metadata filters")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What are the prerequisites for ELEC2843?",
                "tag_filters": {
                    "exact": {"faculty": "Engineering", "department": "cs"},
                    "range": {"academic_year": [2024, 2025]},
                    "fuzzy": {"doc_title": "Syllabus"}
                }
            }
        }
    }

class QueryResultMetadata(BaseModel):
    exact: Optional[Dict[str, Any]] = None
    range: Optional[Dict[str, List[Any]]] = None
    fuzzy: Optional[Dict[str, str]] = None

class QueryResult(BaseModel):
    text: str = Field(..., description="Example retrieved chunk text...")
    doc_title: str = Field(..., description="Example Course Document")
    section: Optional[str] = Field(None, description="Prerequisites")
    metadata: QueryResultMetadata = Field(..., description="Metadata tags")
    source: str = Field(..., description="source reference list")

class QueryResponse(BaseModel):
    query: str
    tag_filters: Optional[TagFilters] = None
    results: List[QueryResult] = Field(..., description="List of relevant document chunks and their metadata")

# --- Helper Functions ---
async def get_embedding(text: str):
    url = f"{LLM_HOST_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "embedding-3",
        "input": text
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}")
    # Fallback to mock (dimension 2048 for embedding-3)
    return [0.1] * 2048

# --- Endpoints ---
@app.get("/")
async def root():
    return {"message": "anyLoader API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint to verify service and database connectivity."""
    db_status = "connected"
    try:
        db.list_tables().tables
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "table": TABLE_NAME
    }

@app.post("/truncate")
async def truncate_table():
    """Truncate the database table by deleting all records."""
    if TABLE_NAME not in db.list_tables().tables:
        raise HTTPException(status_code=404, detail=f"Table '{TABLE_NAME}' not found. Please run ingestion first.")
    
    try:
        table = db.open_table(TABLE_NAME)
        # Delete all records using a filter that matches everything
        table.delete("1=1")
        return {"message": f"Table '{TABLE_NAME}' has been truncated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to truncate table: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_prerequisites(request: QueryRequest):
    if TABLE_NAME not in db.list_tables().tables:
        raise HTTPException(status_code=404, detail="Database table not found. Please run ingestion first.")
    
    table = db.open_table(TABLE_NAME)
    
    # Construct filter string
    where_clauses = []
    if request.tag_filters:
        if request.tag_filters.exact:
            for key, value in request.tag_filters.exact.items():
                if value is not None:
                    # Standardize key and value
                    formatted_key = key.lower().replace(" ", "_")
                    formatted_value = str(value).lower().replace(" ", "_").replace("'", "''")
                    where_clauses.append(f"{formatted_key} = '{formatted_value}'")
        
        if request.tag_filters.range:
            for key, values in request.tag_filters.range.items():
                if values and len(values) == 2:
                    # Standardize key
                    formatted_key = key.lower().replace(" ", "_")
                    # Map academic_year to start_year for range queries
                    db_key = "start_year" if formatted_key == "academic_year" else formatted_key
                    where_clauses.append(f"{db_key} >= {values[0]}")
                    where_clauses.append(f"{db_key} <= {values[1]}")
        
        if request.tag_filters.fuzzy:
            for key, value in request.tag_filters.fuzzy.items():
                if value:
                    # Standardize key and value
                    formatted_key = key.lower().replace(" ", "_")
                    formatted_value = str(value).lower().replace(" ", "_").replace("'", "''")
                    where_clauses.append(f"{formatted_key} LIKE '%{formatted_value}%'")

    where_str = " AND ".join(where_clauses) if where_clauses else None
    
    # Get query embedding
    query_vector = await get_embedding(request.query)
    
    # Perform vector search
    query_builder = table.search(query_vector).limit(5)
    if where_str:
        query_builder = query_builder.where(where_str)
    
    results = query_builder.to_list()
    
    # Format results
    formatted_results = []
    for r in results:
        # Construct metadata object from flat fields
        res_metadata = {
            "exact": {
                "faculty": r.get("faculty"),
                "department": r.get("department")
            },
            "range": {
                "academic_year": [int(y) for y in r.get("academic_year", "0-0").split("-") if y.isdigit()]
            },
            "fuzzy": {
                "doc_title": r.get("doc_title")
            }
        }
        
        formatted_results.append({
            "text": r["text"],
            "doc_title": r["doc_title"],
            "section": r.get("section", "general"),
            "metadata": res_metadata,
            "source": r.get("file_path", "unknown source")
        })
        
    return {
        "query": request.query,
        "tag_filters": request.tag_filters,
        "results": formatted_results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server.main:app", host=RAG_HOST_PATH, port=RAG_PORT, reload=True)
