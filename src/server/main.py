from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import lancedb
import os
import httpx
import asyncio
import re
import io
import time
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from pptx import Presentation
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Configuration and Database Initialization ---
LANCEDB_URI = os.getenv("LANCEDB_URI", "./storage/lancedb")
TABLE_NAME = "course_prerequisites"
LLM_HOST_URL = os.getenv("LLM_HOST_PATH")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "embedding-3")
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
    all_fields: Optional[Dict[str, Any]] = None

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
def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text from various file formats given bytes and filename."""
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
        elif ext == ".docx":
            doc = DocxDocument(io.BytesIO(content))
            text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == ".pptx":
            prs = Presentation(io.BytesIO(content))
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(content))
            text = df.to_string()
        elif ext in [".md", ".txt"]:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
    return text

def chunk_text(text: str, chunk_size=1000, overlap=100):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks

async def get_embeddings(texts: List[str]):
    # Zhipu AI / OpenAI compatible embedding batching
    batch_size = 64
    url = f"{LLM_HOST_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    all_embeddings = []
    
    async with httpx.AsyncClient() as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            cleaned_batch = [t if t.strip() else "[empty]" for t in batch]
                
            payload = {
                "model": LLM_MODEL_NAME,
                "input": cleaned_batch
            }
            
            max_retries = 3
            batch_embeddings = []
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                    if response.status_code == 200:
                        data = response.json()
                        batch_embeddings = [item["embedding"] for item in data["data"]]
                        break
                    elif response.status_code == 429:
                        wait_time = (attempt + 1) * 2
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"Embedding error: {response.status_code} - {response.text}")
                        if attempt == max_retries - 1:
                            batch_embeddings = [[0.1] * 2048 for _ in batch]
                except Exception as e:
                    print(f"Embedding exception: {e}")
                    if attempt == max_retries - 1:
                        batch_embeddings = [[0.1] * 2048 for _ in batch]
                    await asyncio.sleep(1)
            
            all_embeddings.extend(batch_embeddings)
            await asyncio.sleep(0.1)

    return all_embeddings

async def get_embedding(text: str):
    embeddings = await get_embeddings([text])
    return embeddings[0] if embeddings else [0.1] * 2048

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
        table.delete("1=1")
        return {"message": f"Table '{TABLE_NAME}' has been truncated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to truncate table: {str(e)}")


@app.post("/v1/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("assistants"),
    degree_level: str = Form("unknown"),
    category: str = Form("unknown"),
    department: str = Form("unknown"),
    academic_year: str = Form("unknown"),
    faculty: str = Form("generic")
):
    """Chunk, embed, and load a document into the vector database using multipart/form-data."""
    content = await file.read()
    text = extract_text_from_bytes(content, file.filename)
    
    if not text.strip():
        return {"message": "No text content extracted from the file."}
    
    chunks = chunk_text(text)
    embeddings = await get_embeddings(chunks)
    
    # Standardize metadata
    std_meta = {
        "degree_level": degree_level.lower().replace(" ", "_"),
        "category": category.lower().replace(" ", "_"),
        "department": department.lower().replace(" ", "_"),
        "academic_year": academic_year.lower().replace(" ", "_"),
        "faculty": faculty.lower().replace(" ", "_"),
        "doc_title": file.filename.lower().replace(" ", "_"),
        "file_path": f"uploaded://{file.filename}"
    }
    
    start_year = 0
    try:
        match = re.search(r"(\d{4})", std_meta["academic_year"])
        if match:
            start_year = int(match.group(1))
    except:
        pass

    data = []
    for i, chunk in enumerate(chunks):
        first_line = chunk.split("\n")[0].strip()
        section = "general"
        if 3 < len(first_line) < 60:
            section = first_line.lower().replace(" ", "_").strip("_")
        
        row = {
            "vector": embeddings[i],
            "text": chunk,
            "section": section,
            "start_year": start_year
        }
        row.update(std_meta)
        data.append(row)
    
    try:
        if TABLE_NAME not in db.list_tables().tables:
            table = db.create_table(TABLE_NAME, data=data)
            table.create_fts_index("text")
        else:
            table = db.open_table(TABLE_NAME)
            table.add(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load document: {str(e)}")
    
    # Return OpenAI-like file object
    return {
        "id": f"file-{os.urandom(8).hex()}",
        "object": "file",
        "bytes": len(content),
        "created_at": int(time.time()),
        "filename": file.filename,
        "purpose": purpose,
        "message": f"Document '{file.filename}' loaded successfully with {len(chunks)} chunks."
    }

@app.post("/query", response_model=QueryResponse)
async def query_prerequisites(request: QueryRequest):
    if TABLE_NAME not in db.list_tables().tables:
        raise HTTPException(status_code=404, detail="Database table not found. Please run ingestion first.")
    
    table = db.open_table(TABLE_NAME)
    
    where_clauses = []
    if request.tag_filters:
        if request.tag_filters.exact:
            for key, value in request.tag_filters.exact.items():
                if value is not None:
                    formatted_key = key.lower().replace(" ", "_")
                    formatted_value = str(value).lower().replace(" ", "_").replace("'", "''")
                    where_clauses.append(f"{formatted_key} = '{formatted_value}'")
        
        if request.tag_filters.range:
            for key, values in request.tag_filters.range.items():
                if values and len(values) == 2:
                    formatted_key = key.lower().replace(" ", "_")
                    db_key = "start_year" if formatted_key == "academic_year" else formatted_key
                    where_clauses.append(f"{db_key} >= {values[0]}")
                    where_clauses.append(f"{db_key} <= {values[1]}")
        
        if request.tag_filters.fuzzy:
            for key, value in request.tag_filters.fuzzy.items():
                if value:
                    formatted_key = key.lower().replace(" ", "_")
                    formatted_value = str(value).lower().replace(" ", "_").replace("'", "''")
                    where_clauses.append(f"{formatted_key} LIKE '%{formatted_value}%'")

    where_str = " AND ".join(where_clauses) if where_clauses else None
    query_vector = await get_embedding(request.query)
    query_builder = table.search(query_vector).limit(5)
    if where_str:
        query_builder = query_builder.where(where_str)
    
    results = query_builder.to_list()
    
    formatted_results = []
    for r in results:
        res_metadata = {
            "exact": {
                "faculty": r.get("faculty"),
                "department": r.get("department"),
                "degree_level": r.get("degree_level"),
                "category": r.get("category")
            },
            "range": {
                "academic_year": [int(y) for y in re.findall(r"\d{4}", r.get("academic_year", "0-0"))]
            },
            "fuzzy": {
                "doc_title": r.get("doc_title")
            },
            "all_fields": {k: v for k, v in r.items() if k != "vector"}
        }
        
        formatted_results.append({
            "text": r["text"],
            "doc_title": r.get("doc_title", "unknown"),
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
