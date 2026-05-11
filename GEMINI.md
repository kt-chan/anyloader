# Anyloader Project Context for Gemini CLI

## Overview
Anyloader is a solution python script that loading text, markdown, pdf, word, powerpoint, excel, and other types of documents into a fastapi application that wrapping lancedb as the vector database. The solution as a whole serve as a Retrieval-Augmented Generation (RAG) system for deep document analysis and chat. Supports multiple vector DBs and LLM integrations.

## Tech Stack
- **Runtime:** python 3.13
- **Vector DBs:** LanceDB
- **Embedding Models:** vllm local deployment
## Features
- **Data Ingestion**: Automatically extracts text from PDF, DOCX, PPTX, XLSX, MD, and TXT files.
- **Metadata Tagging**: Infers tags (degree level, academic year, faculty) from the `data/` directory structure.
- **Query Service**: FastAPI-powered RAG query endpoint with support for:
    - Vector similarity search with Metadata filtering (Exact faculty, Academic year range, Doc title substring).
    - /query endpoint API request contract as follow:
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
     - /query endpoint API response contract as follow:
        {
        "query": "What are the prerequisites for ELEC2843?",
        "tag_filters": {
            "exact": {"faculty": "Engineering", "department": "cs"},
            "range": {"academic_year": [2023, 2025]},
            "fuzzy": {"doc_title": "Syllabus"}
        }
        "results": [
            {
            "text": "Example retrieved chunk text...",
            "doc_title": "Example Course Document",
            "section": "Prerequisites",
            "metadata": {
                "exact": {"faculty": "Engineering", "department": "cs"},
                "range": {"academic_year": [2023, 2025]},
                "fuzzy": {"doc_title": "Syllabus"}
            },
            "source": "source reference list"
            }
        ]
        }
- **Dockerized**: Ready for containerized deployment.

## Usage
1. **Ingest Data**: Run `python src/loader/ingest.py` to populate LanceDB.
2. **Start Server**: Run `python src/server/main.py`.
3. **Query**: Send a POST request to `/query` with your search term and filters.


## Environment
- **LLM endpoint** from `.env` variables `LLM_HOST_PATH`, `LLM_MODEL_NAME`, `LLM_API_KEY`.
- **Local** Windows, VS Code, PowerShell.
- **Storage** lancedb files should put under `storage/` folder at project root.
- **Data** rich document data are put under `data/` folder at project root.
- **Scripts** powershell scripts are under `scripts/` folder at project root.

## Development Practice
- write the code under `src/` folder at project root.
- Write unit tests for updates unless explicitly skipped under `tests/` folder at project root.

## Project Structure
- `.env`: define the environment variable
- `requirements.txt`: define all required library
- `src/server`: Core API wrapping around lancedb for document loading and search retreival
- `src/loader`: Data ingestion (file parsers, web scraper, processing queue) to load data from rich document into vectordb wrapped by src/server codes.
- `docker/`: Container configurations with dockerfile and build scripts