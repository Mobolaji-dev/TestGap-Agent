import logging

logger = logging.getLogger(__name__)
_initialized = False


def initialize_neatlogs() -> bool:
    """Initialize neatlogs when configured; local development can run without credentials."""
    global _initialized
    if _initialized:
        return True
    try:
        import neatlogs

        neatlogs.init()
        _initialized = True
        logger.info("neatlogs instrumentation initialized")
        return True
    except ImportError:
        logger.warning("neatlogs is not installed; agent runs will not be traced")
    except Exception:
        logger.exception("neatlogs initialization failed; continuing without remote traces")
    return False
