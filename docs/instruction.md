# objective
write a complete Python implementation that builds a LanceDB-backed FastAPI service for querying course prerequisites, using the provided query and tag_filters as a reference. It includes:

Sample data are put under data/ directory at project root.

# Task
1. analyze the path under data/ directory, and make the directory name as metadata tags
2. design metadata filter for the fastapi wrapping lancedb to support Exact, range, and fuzzy filtering (academic_year range, faculty/department exact, doc_title fuzzy match).
3. make a /query endpoint that accepts the exact JSON structure from the image and returns the prerequisites.


# Objective
update @src\server\main.py that implements all the endpoints exactly as described by the examples below. The POST /upload_file – accepts a file upload (multipart/form-data), saves file metadata and returns it with an id, The /process endpoint must trigger a truly asynchronous background task that put a file into temp directory under storage\temp at project root directory, returning a task_id immediately, and a /process/status/{task_id} endpoint to query its progress.

# Endpoints  Requirements:

GET /health → {"status": "healthy"}

POST /upload_file – accepts a file upload (multipart/form-data), saves file metadata and returns it with an id, name, size, extension, mime_type, created_at (unix timestamp). File content can be stored in temp directory under storage\temp at project root directory.

POST /process – accepts JSON {"file_id": <int>, "input_tags": { … }}, starts an async background job that “processes” the file (see below), returns {"task_id": "<uuid>"} immediately.

GET /process/status/{task_id} – returns {"task_id": "...", "status": "PENDING|PROCESSING|COMPLETED|FAILED", "error": null|<string>}.

POST /search_chunks – accepts a JSON body matching the example (query, collection, top_k, fetch_k, dense_weight, sparse_weight, tag_filters with exact, range, fuzzy, rerank, score_threshold, use_sparse). It must search among stored chunks (generated during processing) and return a list of results. The chunk storage should be filterable by tags; implement a simple keyword match scoring (no real vector DB needed).



# Objective
Update main.py to build FastAPI application for RAG solution. Currently exposes these endpoints (as per the examples below):
- GET /health → {“status”: “healthy”}
- POST /upload_file – accepts a file, returns file metadata (id, name, size, extension, mime_type, created_at)
- POST /process – accepts {“file_id”: int, “input_tags”: {“academic_year”: int, “department”: str, ...}} and starts an async background task the run embedding and insert into lancedb, and immediately returning {“task_id”: “<uuid>”}
- GET /process/status/{task_id} – returns task status (PENDING/PROCESSING/COMPLETED/FAILED), If it is finished it means the file is being processed and loaded into lancedb, and ready for search.
- POST /search_chunks – accepts a JSON body with query, collection, top_k, fetch_k, dense_weight, sparse_weight, tag_filters (exact, range, fuzzy), rerank, score_threshold, use_sparse and returns a list of chunks.

Your task is to **modify the code** so that:
1. The `/process` endpoint implements a complete RAG workflow with metadata filter defined in the `input_tags`: `data/{academic_year}_{department}/<filename>`.
   - Asynchronously process the saved PDF: extract text with PyPDF2, split the text into chunks of ~500 characters with overlap, compute a embedding for each chunk (using model service definted in .env file), and store each chunk in a LanceDB table with columns: `id`, `text`, `vector` (the embedding), `academic_year`, `department`, `doc_title` (the filename), `chunk_index`.
   - Update the task status through PENDING → PROCESSING → COMPLETED (or FAILED if something goes wrong). If the file_id doesn’t exist, mark as FAILED.
2. The `/search_chunks` endpoint must be **fully rewritten** to use LanceDB:
   - Accept the same JSON body as the original example (including `tag_filters` with `exact`, `range`, `fuzzy`).
   - Translate `tag_filters` into a LanceDB `WHERE` clause:
       - Exact: `department = 'CS'` (if provided)
       - Range: `academic_year BETWEEN min AND max` (if provided)
       - Fuzzy: `doc_title LIKE '%term%'` (if provided, using the fuzzy filter – assume it contains a key `doc_title` with a search string)
   - Perform a simple text‑search on the `text` column: for each chunk whose text contains the `query` string (case‑insensitive), assign a score of 1.0, else 0. Use the `WHERE` clause to limit the candidate set. Respect `fetch_k` to limit the number of candidates before scoring, and then apply `score_threshold` and `top_k` to return the best results (sorted by score if `rerank` is true). Ignore `dense_weight`, `sparse_weight`, `use_sparse` for now but keep them in the model.
   - The response must match the original shape: a list of chunk objects (with `id`, `text`, `score`, `metadata` containing the tags).
3. **Metadata filtering must support the exact, range, and fuzzy patterns** described above, using the fields `academic_year` (range), `department` (exact), and `doc_title` (fuzzy).
4. Keep all other endpoints (`/health`, `/upload_file`, `/process/status`) unchanged in terms of their request/response contracts.
5. Use `lancedb` (connect to a local storage\lancedb directory), `sentence-transformers` for embeddings, `PyPDF2` for PDF reading, and `asyncio` for background tasks.
6. Run the server with `uvicorn` on environment variable defined in .env file. 
7. update  `requirements.txt` with all needed packages.
8. Add comments where necessary.
9. update the unit test under tests\ directory