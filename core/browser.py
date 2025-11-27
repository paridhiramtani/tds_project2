import asyncio
from playwright.async_api import async_playwright
import logging
import base64

logger = logging.getLogger(__name__)

class QuizScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            # Launch with arguments to prevent crashes in Docker/Render environment
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage", # Critical for Render memory limits
                    "--disable-gpu"
                ]
            )

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_task_from_url(self, url: str) -> dict:
        if not self.browser:
            await self.start()
        
        # Create context with a standard viewport
        context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        try:
            logger.info(f"Navigating to {url}")
            # Increased timeout for slow sites
            await page.goto(url, timeout=60000)
            
            # --- WAITING STRATEGY ---
            
            # 1. Wait for the page body to be physically visible
            try:
                await page.wait_for_selector("body", state="visible", timeout=10000)
            except Exception:
                logger.warning("Timeout waiting for body visibility.")

            # 2. Critical: Wait for JavaScript execution.
            # Many tasks use 'atob()' or React, which takes a moment to render the text.
            # The 'networkidle' state is often unreliable for SPAs, so we force a sleep.
            await page.wait_for_timeout(5000) 

            # --- EXTRACTION STRATEGY ---

            # 3. Get Human-Readable Text (innerText)
            # This skips the <script> tags and gets what the user actually sees.
            content = await page.evaluate("document.body.innerText")
            
            # Fallback: If innerText is empty (some sites hide body), get raw HTML
            if not content or len(content.strip()) < 20:
                logger.info("innerText empty, falling back to raw HTML content")
                content = await page.content()

            # 4. Capture Screenshot
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
            await context.close()

# Global instance
scraper = QuizScraper()
