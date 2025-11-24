import httpx
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class TaskFetcher:
    async def fetch(self, url: str) -> str:
        logger.info(f"Fetching URL: {url}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Fetch failed: {e}")
                raise

task_fetcher = TaskFetcher()
