import asyncio

import httpx


async def run() -> None:
    """Run the FastAPI agent test."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8001/agent",
            json={
                "messages": [{"role": "user", "text": "hi"}],
                "user_id": "test@example.com",
            },
            # We don't send auth header, so wait, it will try DEV bypass mode!
            timeout=30.0,
        )
        print(resp.status_code)
        async for line in resp.aiter_lines():
            print("LINE:", line)


if __name__ == "__main__":
    asyncio.run(run())
