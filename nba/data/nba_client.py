import logging
import time

log = logging.getLogger(__name__)

REQUEST_DELAY = 0.6
MAX_TRIES = 4
TIMEOUT = 60

_last_call = 0.0


def call_nba(endpoint_class, **kwargs):
    """Call an nba_api endpoint politely and return its DataFrames."""
    global _last_call

    for attempt in range(1, MAX_TRIES + 1):
        wait = REQUEST_DELAY - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)

        try:
            _last_call = time.monotonic()
            response = endpoint_class(timeout=TIMEOUT, **kwargs)
            return response.get_data_frames()
        except Exception as exc:
            if attempt == MAX_TRIES:
                raise
            backoff = 2 ** attempt  # 2, 4, 8 seconds
            log.warning("%s failed (try %d of %d): %s. Retrying in %ds",
                        endpoint_class.__name__, attempt, MAX_TRIES, exc, backoff)
            time.sleep(backoff)