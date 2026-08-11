"""Sample coder agent — generates Python snippets for common tasks."""
import asyncio
from typing import Any


SNIPPETS: dict[str, str] = {
    "fibonacci": """\
def fibonacci(n: int) -> list[int]:
    \"\"\"Return the first n Fibonacci numbers.\"\"\"
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]

print(fibonacci(10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
""",
    "sort dict by value": """\
def sort_dict_by_value(d: dict, reverse: bool = False) -> dict:
    \"\"\"Sort a dictionary by its values.\"\"\"
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=reverse))

print(sort_dict_by_value({"a": 3, "b": 1, "c": 2}))
""",
    "read file": """\
from pathlib import Path

def read_file(path: str) -> str:
    \"\"\"Safely read a file as text.\"\"\"
    return Path(path).read_text(encoding="utf-8")

content = read_file("example.txt")
""",
    "http get": """\
import httpx

async def fetch_json(url: str) -> dict:
    \"\"\"Fetch JSON from a URL using httpx.\"\"\"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
""",
    "a2a client": """\
import httpx, uuid

async def call_a2a_agent(base_url: str, message: str) -> dict:
    \"\"\"Call an A2A agent using the JSON-RPC tasks/send method.\"\"\"
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/send",
        "params": {
            "id": str(uuid.uuid4()),
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}],
            },
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(base_url, json=payload)
        return resp.json()
""",
}


async def handle(input_text: str) -> str:
    """Return a Python snippet matching the request."""
    await asyncio.sleep(0.05)

    q = input_text.lower()
    for key, snippet in SNIPPETS.items():
        if key in q:
            return f"[Coder] Here's a snippet for '{key}':\n\n```python\n{snippet}\n```"

    return (
        "[Coder] I have snippets for: " + ", ".join(SNIPPETS.keys()) +
        ". Ask me about any of these."
    )
