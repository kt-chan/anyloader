import httpx
import asyncio

async def test_loaddoc():
    url = "http://localhost:8000/loaddoc"
    payload = {
        "content": "This is a test document about computer science prerequisites. ELEC2843 requires MATH1013.",
        "metadata": {
            "degree_level": "undergraduate",
            "category": "course",
            "department": "eee",
            "academic_year": "2024-2025",
            "faculty": "engineering",
            "doc_title": "test_doc",
            "file_path": "data/test_doc.txt"
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

async def test_query():
    url = "http://localhost:8000/query"
    payload = {
        "query": "What are the prerequisites for ELEC2843?",
        "tag_filters": {
            "exact": {"faculty": "engineering"},
            "range": {"academic_year": [2023, 2025]}
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

async def main():
    print("Testing /loaddoc...")
    await test_loaddoc()
    print("\nTesting /query...")
    await test_query()

if __name__ == "__main__":
    asyncio.run(main())
