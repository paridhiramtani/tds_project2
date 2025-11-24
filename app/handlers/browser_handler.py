import asyncio
import base64
import json
from typing import Dict, Any, List
from playwright.async_api import async_playwright
from app.handlers.base_handler import BaseHandler
from app.utils.logger import setup_logger
from app.services.llm_service import llm_client

logger = setup_logger(__name__)

class BrowserHandler(BaseHandler):
    async def handle(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        url = task_data.get("url")
        question = task_data.get("question", "Solve the task on this page.")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                
                # Agentic Loop
                max_steps = 5
                for step in range(max_steps):
                    logger.info(f"Browser Step {step+1}/{max_steps}")
                    
                    # 1. Observe
                    title = await page.title()
                    screenshot_bytes = await page.screenshot()
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    # 2. Decide
                    action = self._decide_action(question, title, screenshot_b64)
                    logger.info(f"Decided Action: {action}")
                    
                    if action["type"] == "done":
                        return {"answer": action["answer"], "submit_url": url}
                    
                    # 3. Act
                    await self._execute_action(page, action)
                    await page.wait_for_timeout(1000) # Wait for UI update
                    
                # If loop finishes without "done", try to extract anyway
                return {"error": "Max steps reached without solution"}
                
            except Exception as e:
                logger.error(f"Browser error: {e}")
                raise
            finally:
                await browser.close()

    def _decide_action(self, question: str, title: str, screenshot_b64: str) -> Dict[str, Any]:
        system_prompt = """
        You are a web automation agent. 
        Goal: Solve the user's question.
        Input: Page title and screenshot.
        Output JSON:
        - If solved: {"type": "done", "answer": "..."}
        - If interaction needed: {"type": "click" | "type", "selector": "...", "value": "..." (if type)}
        """
        user_content = [
            {"type": "text", "text": f"Question: {question}\nTitle: {title}"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
        ]
        
        response = llm_client.call(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            model="gpt-4o",
            response_format={"type": "json_object"}
        )
        return llm_client.parse_json(response)

    async def _execute_action(self, page, action: Dict[str, Any]):
        try:
            if action["type"] == "click":
                await page.click(action["selector"])
            elif action["type"] == "type":
                await page.fill(action["selector"], action["value"])
        except Exception as e:
            logger.warning(f"Action failed: {e}")
