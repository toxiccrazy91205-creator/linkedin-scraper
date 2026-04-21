import logging

def configure_logger(name: str) -> logging.Logger:
    """Creates a structured and uniform logger."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        # Use structured-like logging format containing timestamp, level, location, message
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [PID:%(process)d] %(name)s: %(message)s'
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger

# Global instance for quick component imports
app_logger = configure_logger("linkedin_scraper")
