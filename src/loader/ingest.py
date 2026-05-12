import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
import asyncio
import re

load_dotenv()

RAG_HOST = os.getenv("RAG_HOST", "localhost")
RAG_PORT = os.getenv("RAG_PORT", "8000")
SERVER_URL = f"http://{RAG_HOST}:{RAG_PORT}"
INPUT_DIR = os.getenv("INPUT_DIR", "data")

class Ingestor:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)

    async def close(self):
        await self.client.aclose()

    async def upload_document(self, file_path: Path, metadata: dict):
        url = f"{SERVER_URL}/v1/files"
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                data = {
                    "purpose": "enquiry",
                    "degree_level": metadata.get("degree_level", "unknown"),
                    "category": metadata.get("category", "unknown"),
                    "department": metadata.get("department", "unknown"),
                    "academic_year": metadata.get("academic_year", "unknown"),
                    "faculty": metadata.get("faculty", "generic")
                }
                response = await self.client.post(url, files=files, data=data)
            
            if response.status_code == 200:
                print(f"Successfully loaded: {metadata['doc_title']}, from {metadata['file_path']}")
            else:
                print(f"Failed to load {metadata['doc_title']}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error calling /v1/files for {metadata['doc_title']}: {e}")

    async def truncate_table(self):
        url = f"{SERVER_URL}/truncate"
        try:
            response = await self.client.post(url)
            if response.status_code == 200:
                print("Database table truncated successfully.")
            else:
                print(f"Truncate failed (might be first run): {response.status_code}")
        except Exception as e:
            print(f"Error truncating table: {e}")

    async def process_data_dir(self, data_dir: str):
        path = Path(data_dir)
        year_pattern = re.compile(r"\d{4}-\d{4}")
        
        # Optional: Truncate at start to match old 'overwrite' behavior
        await self.truncate_table()
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".md", ".txt"]:
                relative_path = file_path.relative_to(path)
                parts = relative_path.parts
                
                metadata = {
                    "degree_level": "unknown",
                    "category": "unknown",
                    "department": "unknown",
                    "academic_year": "unknown",
                    "faculty": "generic",
                    "doc_title": file_path.name.lower().replace(" ", "_"),
                    "file_path": str(file_path)
                }
                
                # Inference logic
                if len(parts) > 0:
                    metadata["degree_level"] = parts[0].lower().replace(" ", "_")
                
                year_idx = -1
                for i, part in enumerate(parts):
                    if year_pattern.match(part):
                        metadata["academic_year"] = part.lower().replace(" ", "_")
                        year_idx = i
                        break
                
                if year_idx != -1:
                    if year_idx > 1:
                        metadata["category"] = parts[1].lower().replace(" ", "_")
                    if len(parts) > year_idx + 1:
                        metadata["faculty"] = parts[year_idx + 1].lower().replace(" ", "_")
                    if len(parts) > year_idx + 2:
                        dept = parts[year_idx + 2]
                        metadata["department"] = dept.lower().replace(" ", "_") if not dept.endswith(file_path.suffix) else "unknown"
                elif len(parts) > 2:
                    metadata["category"] = parts[1].lower().replace(" ", "_")

                await self.upload_document(file_path, metadata)

if __name__ == "__main__":
    async def main():
        ingestor = Ingestor()
        try:
            await ingestor.process_data_dir(INPUT_DIR)
        finally:
            await ingestor.close()
            
    asyncio.run(main())
