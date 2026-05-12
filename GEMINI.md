# Anyloader Project Context for Gemini CLI

## Overview

Anyloader is a solution python script that loading text, markdown, pdf, word, powerpoint, excel, and other types of documents into a fastapi application that wrapping lancedb as the vector database. The solution as a whole serve as a Retrieval-Augmented Generation (RAG) system for deep document analysis and chat. Supports multiple vector DBs and LLM integrations.

## Tech Stack

* **Runtime:** python 3.13
* **Vector DBs:** LanceDB
* **Embedding Models:** vllm local deployment

## Features

* **Data Ingestion**: Automatically extracts text from PDF, DOCX, PPTX, XLSX, MD, and TXT files.
* **Metadata Tagging**: Infers tags (degree level, academic year, faculty) from the `data/` directory structure.
* **Query Service**: FastAPI-powered RAG query endpoint with support for:
* Vector similarity search with Metadata filtering (Exact faculty, Academic year range, Doc title substring).
* `/query` endpoint API request contract:
```bash
curl -X POST "http://localhost:8000/query" \
-H "Content-Type: application/json" \
-d '{
    "query": "What are the prerequisites for ELEC2843?",
    "tag_filters": {
        "exact": {"faculty": "Engineering", "department": "cs"},
        "range": {"academic_year": [2023, 2025]},
        "fuzzy": {"doc_title": "Syllabus"}
    }
}'

```





## Usage

1. **Ingest Data**: Run `python src/loader/ingest.py` to populate LanceDB.
2. **Start Server**: Run `python src/server/main.py`.
3. **Query**: Send a POST request to `/query` with your search term and filters.

## Environment

* **LLM endpoint** from `.env` variables `LLM_HOST_PATH`, `LLM_MODEL_NAME`, `LLM_API_KEY`.
* **Local** Windows, VS Code, PowerShell.
* **Storage** lancedb files should put under `storage/` folder at project root.
* **Data** rich document data are put under `data/` folder at project root.
* **Scripts** powershell scripts are under `scripts/` folder at project root.

## Development Practice

* **Code Location**: Write all application code under the `src/` folder at project root.
* **Testing**: Write unit tests for updates under `tests/` unless explicitly skipped.
* **Process Management (CRITICAL)**:
* **Do NOT terminate the caller**: The code agent must never execute commands that terminate the parent shell, command client, or the current terminal session (e.g., avoid `exit`, `taskkill /F /IM powershell.exe`, etc.).
* **Port Management**: To restart the server, specifically target and kill only the process listening on port 8000 (e.g., using `Stop-Process` on the specific PID found via `netstat -ano`).
* **Background Tasks**: When running the FastAPI server or long-running loaders, use separate threads or start them as background jobs to ensure the main command client remains interactive and alive.



## Project Structure

* `.env`: define the environment variable
* `requirements.txt`: define all required library
* `src/server`: Core API wrapping around lancedb for document loading and search retreival
* `src/loader`: Data ingestion (file parsers, processing queue) to load data into vectordb.
* `docker/`: Container configurations with dockerfile and build scripts.
