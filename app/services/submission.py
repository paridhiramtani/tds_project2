import httpx
from typing import Dict, Any
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class SubmissionService:
    async def submit(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Submitting to {url} with payload keys: {list(payload.keys())}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                # We don't raise_for_status immediately because 400/401 might contain useful feedback
                return response.json()
            except Exception as e:
                logger.error(f"Submission failed: {e}")
                raise

submission_service = SubmissionService()
