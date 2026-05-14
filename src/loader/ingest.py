import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
import asyncio
import re

load_dotenv()

RAG_HOST = os.getenv("RAG_HOST_PATH", os.getenv("RAG_HOST", "localhost"))
RAG_PORT = os.getenv("RAG_PORT", "8000")
SERVER_URL = f"http://{RAG_HOST}:{RAG_PORT}"
INPUT_DIR = os.getenv("INPUT_DIR", "data")

class Ingestor:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.active_tasks = []

    async def close(self):
        await self.client.aclose()

    async def truncate_database(self):
        """Calls the server to truncate the database."""
        truncate_url = f"{SERVER_URL}/truncate"
        try:
            response = await self.client.post(truncate_url)
            if response.status_code == 200:
                print(f"Database truncated successfully: {response.json().get('message')}")
            else:
                print(f"Failed to truncate database: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error during truncation: {e}")

    async def wait_for_tasks(self):
        """Polls status of all active tasks until completion."""
        if not self.active_tasks:
            return
            
        print(f"Waiting for {len(self.active_tasks)} processing tasks to complete...")
        pending_tasks = self.active_tasks.copy()
        
        while pending_tasks:
            remaining = []
            for task_id in pending_tasks:
                try:
                    response = await self.client.get(f"{SERVER_URL}/process/status/{task_id}")
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status")
                        if status in ["COMPLETED", "FAILED"]:
                            if status == "FAILED":
                                print(f"Task {task_id} failed: {data.get('error')}")
                            else:
                                print(f"Task {task_id} completed successfully.")
                        else:
                            remaining.append(task_id)
                    else:
                        print(f"Failed to get status for {task_id}: {response.status_code}")
                        remaining.append(task_id)
                except Exception as e:
                    print(f"Error checking status for {task_id}: {e}")
                    remaining.append(task_id)
            
            pending_tasks = remaining
            if pending_tasks:
                await asyncio.sleep(2)
        
        print("All processing tasks finished.")
        self.active_tasks = []

    async def ingest_document(self, file_path: Path, metadata: dict):
        """Uploads a file and triggers processing."""
        upload_url = f"{SERVER_URL}/upload_file"
        try:
            # Step 1: Upload File
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                response = await self.client.post(upload_url, files=files)
            
            if response.status_code != 200:
                print(f"Upload failed for {file_path.name}: {response.status_code} - {response.text}")
                return

            file_id = response.json()["id"]
            
            # Step 2: Trigger Processing
            process_url = f"{SERVER_URL}/process"
            # Filter metadata to send as input_tags (excluding local file_path)
            input_tags = {k: v for k, v in metadata.items() if k not in ["file_path"]}
            payload = {
                "file_id": file_id,
                "input_tags": input_tags
            }
            response = await self.client.post(process_url, json=payload)
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                print(f"Successfully uploaded and started processing: {file_path.name} (Task: {task_id})")
                self.active_tasks.append(task_id)
            else:
                print(f"Failed to start processing for {file_path.name}: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error during ingestion of {file_path.name}: {e}")

    async def process_data_dir(self, data_dir: str):
        path = Path(data_dir)
        if not path.exists():
            print(f"Data directory {data_dir} does not exist.")
            return

        year_pattern = re.compile(r"\d{4}-\d{4}")
        ingest_tasks = []
        
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
                
                # Inference logic from directory structure
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

                ingest_tasks.append(self.ingest_document(file_path, metadata))

        if ingest_tasks:
            print(f"Starting ingestion of {len(ingest_tasks)} files...")
            await asyncio.gather(*ingest_tasks)
            await self.wait_for_tasks()
        else:
            print("No valid files found for ingestion.")

if __name__ == "__main__":
    async def main():
        ingestor = Ingestor()
        try:
            # Truncate database before starting fresh ingestion
            await ingestor.truncate_database()
            await ingestor.process_data_dir(INPUT_DIR)
        finally:
            await ingestor.close()
            
    asyncio.run(main())
