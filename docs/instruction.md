# objective
write a complete Python implementation that builds a LanceDB-backed FastAPI service for querying course prerequisites, using the provided query and tag_filters as a reference. It includes:

Sample data are put under data/ directory at project root.

# Task
1. analyze the path under data/ directory, and make the directory name as metadata tags
2. design metadata filter for the fastapi wrapping lancedb to support Exact, range, and fuzzy filtering (academic_year range, faculty/department exact, doc_title fuzzy match).
3. make a /query endpoint that accepts the exact JSON structure from the image and returns the prerequisites.