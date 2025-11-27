# app/services/task_fetcher.py
from playwright.async_api import async_playwright
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class TaskFetcher:
    async def fetch(self, url: str) -> str:
        logger.info(f"Fetching URL (Playwright): {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                # Return the visible text, or full content if text is empty
                text = await page.inner_text("body")
                if not text.strip():
                     text = await page.content()
                return text
            finally:
                await browser.close()

task_fetcher = TaskFetcher()
