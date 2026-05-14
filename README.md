# Anyloader

Anyloader is a high-performance Python-based document ingestion and retrieval system designed for Retrieval-Augmented Generation (RAG). It streamlines the process of loading diverse document types into a vector database (LanceDB) and provides a robust FastAPI-based query service for semantic search with advanced metadata filtering.

## 🚀 Features

*   **Multi-format Ingestion**: Automatically extracts text from PDF, DOCX, PPTX, XLSX, MD, and TXT files.
*   **Intelligent Metadata Tagging**: Infers academic metadata (degree level, academic year, faculty) based on directory structures.
*   **FastAPI Query Service**: High-performance semantic search endpoint.
*   **Advanced Filtering**: Supports vector similarity search combined with:
    *   Exact matches (e.g., faculty, department).
    *   Range filters (e.g., academic year).
    *   Fuzzy matching on document titles.
*   **Vector Database**: Powered by LanceDB for efficient storage and retrieval.

## 🛠️ Tech Stack

*   **Language**: Python 3.13
*   **Web Framework**: FastAPI & Uvicorn
*   **Vector Database**: LanceDB
*   **Embedding Models**: vLLM (Local deployment supported)
*   **Document Parsing**: PyMuPDF, python-docx, python-pptx, Pandas, etc.

## 📁 Project Structure

```text
anyLoader/
├── data/               # Source documents (PDF, Docx, etc.)
├── src/
│   ├── loader/         # Ingestion scripts and parsers
│   └── server/         # FastAPI application and database logic
├── storage/            # LanceDB vector database files
├── tests/              # Unit and integration tests
├── scripts/            # Utility PowerShell scripts
└── .env                # Environment configuration
```

## ⚙️ Setup

### Prerequisites

*   Python 3.13+
*   Local vLLM deployment or access to an LLM endpoint.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/anyLoader.git
    cd anyLoader
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory and configure your LLM settings:
    ```env
    LLM_HOST_PATH=http://your-vllm-endpoint:8000/v1
    LLM_MODEL_NAME=your-model-name
    LLM_API_KEY=your-api-key
    ```

### Docker Setup (Recommended)

The easiest way to run anyLoader is using Docker and Docker Compose. This ensures all dependencies and environment settings are correctly configured.

1.  **Build and Start Services**:
    From the project root, run:
    ```bash
    cd docker
    docker-compose up --build
    ```
    This will:
    *   Build and start the **Server** (FastAPI RAG API).
    *   Start the **Loader** (Ingestion service) which will wait for the server to be healthy before processing documents in the `data/` directory.

2.  **Verify Status**:
    *   The API will be available at `http://localhost:8000`.
    *   Check logs to see ingestion progress: `docker-compose logs -f loader`.

## 📖 Usage

### Linux Management Scripts
For Linux (Ubuntu) users, management scripts are provided in the `scripts/` directory:
*   **Manage Server**: `./scripts/manage_server.sh {start|stop|restart|status}`
*   **Run Loader**: `./scripts/run_loader.sh`

### 1. Ingest Data
Place your documents in the `data/` folder following the established directory hierarchy, then run the ingestion script:
```bash
python src/loader/ingest.py
```

### 2. Start the Server
Run the FastAPI application:
```bash
python src/server/main.py
```

### 3. Query the System
Send a semantic search request with optional metadata filters:
```bash
curl -X POST "http://localhost:8000/query" \
-H "Content-Type: application/json" \
-d '{
    "query": "What are the prerequisites for ELEC2843?",
    "tag_filters": {
        "exact": {"faculty": "Engineering"},
        "range": {"academic_year": [2023, 2025]},
        "fuzzy": {"doc_title": "Syllabus"}
    }
}'
```

## 🧪 Testing
Run the test suite using pytest:
```bash
pytest
```

## 📄 License
This project is licensed under the terms of the LICENSE file included in the root directory.
