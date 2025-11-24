import asyncio
from typing import Dict, Any, Optional
from app.services.task_fetcher import task_fetcher
from app.services.submission import submission_service
from app.services.llm_service import llm_client
from app.services.state_manager import state_manager
from app.handlers.browser_handler import BrowserHandler
from app.handlers.data_handler import DataHandler
from app.handlers.audio_handler import AudioHandler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class Orchestrator:
    def __init__(self):
        self.browser_handler = BrowserHandler()
        self.data_handler = DataHandler()
        self.audio_handler = AudioHandler()
        
    async def run(self, initial_url: str, email: str, secret: str):
        task_id = state_manager.create_task(email, initial_url)
        state_manager.update_status(task_id, "processing")
        logger.info(f"Starting Task {task_id}")
        
        current_url = initial_url
        
        for step in range(10): # Safety limit
            logger.info(f"--- Step {step + 1} ---")
            state_manager.log(task_id, f"Step {step+1}: Processing {current_url}")
            
            try:
                # 1. Fetch & Classify
                content = await task_fetcher.fetch(current_url)
                task_type = self._classify_task(content)
                logger.info(f"Task Type: {task_type}")
                state_manager.log(task_id, f"Classified as {task_type}")
                
                # 2. Solve
                answer_data = {}
                if task_type == "browser":
                    answer_data = await self.browser_handler.handle({"url": current_url})
                elif task_type == "audio":
                    # Extract audio URL from content (simplified)
                    # In reality, we'd parse the HTML to find the <audio> tag or link
                    audio_url = self._extract_audio_url(content)
                    answer_data = await self.audio_handler.handle({"audio_url": audio_url, "question": "Transcribe and solve"})
                else:
                    # Default/Text/Data
                    answer_data = await self.data_handler.handle({"question": "Solve this", "context": content})
                
                if not answer_data or "answer" not in answer_data:
                    logger.error("No answer generated")
                    state_manager.update_status(task_id, "failed", "No answer generated")
                    break
                    
                # 3. Submit
                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer_data["answer"]
                }
                
                submit_url = answer_data.get("submit_url") or current_url
                
                result = await submission_service.submit(submit_url, payload)
                state_manager.add_history(task_id, current_url, "submit", str(result))
                
                if result.get("correct"):
                    next_url = result.get("next_url")
                    if not next_url:
                        logger.info("Chain completed!")
                        state_manager.update_status(task_id, "completed")
                        return "Success"
                    current_url = next_url
                else:
                    logger.warning(f"Incorrect: {result.get('message')}")
                    state_manager.log(task_id, f"Incorrect answer: {result.get('message')}")
                    # Retry logic would go here
                    break
                    
            except Exception as e:
                logger.error(f"Orchestrator error: {e}")
                state_manager.update_status(task_id, "error", str(e))
                break

    def _classify_task(self, content: str) -> str:
        if "html" in content.lower() and "<script" in content.lower():
            return "browser"
        if ".mp3" in content.lower() or ".wav" in content.lower() or "<audio" in content.lower():
            return "audio"
        if "csv" in content.lower() or "json" in content.lower():
            return "data"
        
        prompt = f"Classify this task content into 'browser', 'audio', 'data', or 'text'. Content: {content[:500]}"
        return llm_client.call([{"role": "user", "content": prompt}]).lower().strip()

    def _extract_audio_url(self, content: str) -> str:
        # Quick hack extraction. Should use BeautifulSoup.
        import re
        match = re.search(r'href=[\'"]?(http[^\'" >]+\.(?:mp3|wav))[\'"]?', content)
        if match:
            return match.group(1)
        return ""

orchestrator = Orchestrator()
