import httpx
import asyncio
import pytest
import os

SERVER_URL = "http://localhost:8000"

# Check if server is running
def is_server_running():
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', 8000)) == 0
    except:
        return False

@pytest.mark.asyncio
@pytest.mark.skipif(not is_server_running(), reason="Server not running on localhost:8000")
async def test_flow():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        print("Checking health...")
        res = await client.get(f"{SERVER_URL}/health")
        assert res.status_code == 200
        print(f"Health: {res.json()}")

        # 2. Upload
        print("\nUploading file...")
        files = {"file": ("api_test.txt", b"Artificial Intelligence is the future of computing.", "text/plain")}
        res = await client.post(f"{SERVER_URL}/upload_file", files=files)
        assert res.status_code == 200
        file_id = res.json()["id"]
        print(f"Uploaded file ID: {file_id}")

        # 3. Process
        print("\nStarting process...")
        payload = {
            "file_id": file_id,
            "input_tags": {
                "academic_year": 2026,
                "department": "AI Lab"
            }
        }
        res = await client.post(f"{SERVER_URL}/process", json=payload)
        assert res.status_code == 200
        task_id = res.json()["task_id"]
        print(f"Task ID: {task_id}")

        # 4. Wait for completion
        print("\nWaiting for task completion...")
        for _ in range(10):
            res = await client.get(f"{SERVER_URL}/process/status/{task_id}")
            assert res.status_code == 200
            status = res.json()["status"]
            print(f"Status: {status}")
            if status in ["COMPLETED", "FAILED"]:
                break
            await asyncio.sleep(1)

        # 5. Search
        print("\nSearching chunks...")
        search_payload = {
            "query": "intelligence",
            "tag_filters": {
                "exact": {"department": "AI Lab"}
            },
            "top_k": 3
        }
        res = await client.post(f"{SERVER_URL}/search_chunks", json=search_payload)
        assert res.status_code == 200
        print(f"Search Results: {res.json()}")

if __name__ == "__main__":
    if is_server_running():
        asyncio.run(test_flow())
    else:
        print("Server not running. Skipping.")
