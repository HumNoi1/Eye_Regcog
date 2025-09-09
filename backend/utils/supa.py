import os, httpx
BASE = f'{os.getenv("SUPABASE_PROJECT_URL")}/rest/v1'

async def insert_embeddings(user_token: str, user_id: str, embs: list[list[float]], quality: float):
    rows = [{"user_id": user_id, "embedding": e, "quality_score": quality} for e in embs]
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"{BASE}/face_templates",
            headers={
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=rows
        )
        r.raise_for_status()

async def get_user_embeddings(user_token: str, user_id: str) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{BASE}/face_templates?user_id=eq.{user_id}&select=embedding",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        r.raise_for_status()
        return [row["embedding"] for row in r.json()]
