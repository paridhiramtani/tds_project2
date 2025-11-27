import asyncio
from playwright.async_api import async_playwright, Page
import logging

logger = logging.getLogger(__name__)

class QuizScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            # Launch headless for production, maybe headed for debugging if needed
            self.browser = await self.playwright.chromium.launch(headless=True)

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_task_from_url(self, url: str) -> str:
        if not self.browser:
            await self.start()
        
        page = await self.browser.new_page()
        try:
            logger.info(f"Navigating to {url}")
            await page.goto(url)
            
            # Wait for the content to load. The requirements mention #result or similar.
            # We'll wait for the body to be populated.
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                logger.warning("Timeout waiting for networkidle, proceeding anyway.")
            
            # Specific handling for the sample provided in requirements
            # The sample puts content in #result. Let's try to get that first, else body.
            try:
                content = await page.inner_text("body", timeout=5000)
            except Exception:
                content = await page.content()
            
            # Capture screenshot
            import base64
            screenshot_bytes = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                
            return {
                "text": content,
                "screenshot": screenshot_b64
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            raise
        finally:
            await page.close()

# Global instance
scraper = QuizScraper()
