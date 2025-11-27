# app/services/task_fetcher.py
from playwright.async_api import async_playwright
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class TaskFetcher:
    async def fetch(self, url: str) -> str:
        logger.info(f"Fetching URL with Playwright: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Create a new context to ensure a clean slate
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto(url)
                # Wait for the network to be idle (scripts loaded)
                await page.wait_for_load_state("networkidle")
                
                # OPTIONAL: Wait for a specific element if known, else wait a moment for JS execution
                # await page.wait_for_timeout(1000) 

                # Get the readable text from the body
                content = await page.inner_text("body")
                
                # If body text is empty/sparse, fallback to full HTML content
                if len(content.strip()) < 50:
                    content = await page.content()
                    
                return content
            except Exception as e:
                logger.error(f"Fetch failed: {e}")
                raise
            finally:
                await browser.close()

task_fetcher = TaskFetcher()
