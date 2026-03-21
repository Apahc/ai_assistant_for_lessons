import httpx


class EmbedClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/embed", json={"texts": texts})
            response.raise_for_status()
            return response.json()["embeddings"]


class RerankerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def rerank(self, query: str, items: list[dict], top_k: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/rerank",
                json={"query": query, "items": items, "top_k": top_k},
            )
            response.raise_for_status()
            return response.json()["items"]
