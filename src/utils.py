import asyncio
import functools
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

def async_retry_on_timeout(max_retries: int = 5, delay: float = 1.0):
    """
    Decorator that retries an async function on timeout up to max_retries times.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except asyncio.TimeoutError:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries")
                        raise
                    logger.warning(f"Timeout in {func.__name__}, retry {retries}/{max_retries}")
                    await asyncio.sleep(delay * retries)  # Exponential backoff
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def infinite_retry(func: Callable, *args, initial_delay: float = 1.0, max_delay: float = 60.0, **kwargs) -> Any:
    """
    Retries a function infinitely with exponential backoff until it succeeds.
    
    Args:
        func: Async function to retry
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
    """
    delay = initial_delay
    attempt = 1
    
    while True:
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Success after {attempt} attempts")
            return result
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {str(e)}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)  # Exponential backoff with cap
            attempt += 1 