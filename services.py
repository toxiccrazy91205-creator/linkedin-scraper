import threading
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed
from scraper import LinkedInScraper
from stealth_browser import StealthBrowser
from config import Config
from logger import app_logger

# ---------------------------------------------------------------------------
# Async bridge — Single event loop for Playwright in a background thread
# ---------------------------------------------------------------------------

_background_loop = None
_loop_thread = None
_scraper_instance = None


def _start_background_loop(loop):
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    finally:
        loop.close()


def get_scraper() -> LinkedInScraper:
    """Get or initialize the global scraper instance running in a background thread."""
    global _background_loop, _loop_thread, _scraper_instance
    if _background_loop is None:
        _background_loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_start_background_loop, args=(_background_loop,), daemon=True)
        _loop_thread.start()
        
        browser = StealthBrowser()
        _scraper_instance = LinkedInScraper(browser=browser)
    return _scraper_instance


@retry(stop=stop_after_attempt(Config.MAX_RETRIES), wait=wait_fixed(2), reraise=True)
def run_async_with_retry(coro_name: str, *args, **kwargs):
    """
    Submits a coroutine to the background loop, waiting with a strict timeout,
    and automatically retries on transient errors.
    """
    scraper = get_scraper()
    coro_func = getattr(scraper, coro_name)
    coro = coro_func(*args, **kwargs)
    
    app_logger.info(f"Submitting {coro_name} to background Playwright loop (Timeout: {Config.SCRAPER_TIMEOUT}s)")
    future = asyncio.run_coroutine_threadsafe(coro, _background_loop)
    
    try:
        # Strictly enforce timeout limits
        return future.result(timeout=Config.SCRAPER_TIMEOUT)
    except TimeoutError:
        future.cancel()
        app_logger.error(f"Task {coro_name} timed out after {Config.SCRAPER_TIMEOUT} seconds.")
        raise TimeoutError(f"Scraper operation timed out. (Max {Config.SCRAPER_TIMEOUT} seconds)")
    except Exception as e:
        app_logger.error(f"Background task failed: {e}")
        raise


def shutdown_scraper():
    """Graceful shutdown of Playwright instance."""
    global _background_loop, _scraper_instance
    if _background_loop and _scraper_instance:
        app_logger.info("Cleaning up scraper and Playwright instances...")
        try:
            future = asyncio.run_coroutine_threadsafe(_scraper_instance._browser.cleanup(), _background_loop)
            future.result(timeout=10)
        except Exception as e:
            app_logger.error(f"Error during cleanup: {e}")
        finally:
            _background_loop.call_soon_threadsafe(_background_loop.stop)
