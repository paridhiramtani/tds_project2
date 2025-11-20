import httpx
import logging

logger = logging.getLogger(__name__)

async def submit_result(submit_url: str, payload: dict) -> dict:
    """
    Submits the result to the given URL.
    """
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Submitting to {submit_url} with payload: {payload}")
            response = await client.post(submit_url, json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Submission failed: {e}")
            raise
