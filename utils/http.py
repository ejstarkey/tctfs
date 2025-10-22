"""HTTP utilities for conditional GET and backoff."""
import time
import logging

logger = logging.getLogger(__name__)

def conditional_get(session, url, etag=None, last_modified=None, timeout=30):
    """
    Perform conditional GET request.
    
    Returns:
        Response or None if 304 Not Modified
    """
    headers = {}
    if etag:
        headers['If-None-Match'] = etag
    if last_modified:
        headers['If-Modified-Since'] = last_modified
    
    response = session.get(url, headers=headers, timeout=timeout)
    
    if response.status_code == 304:
        return None
    
    response.raise_for_status()
    return response


def exponential_backoff(func, max_retries=3, base_delay=1):
    """
    Retry function with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    
    return None
