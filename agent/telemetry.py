import logging
import os

logger = logging.getLogger(__name__)
_initialized = False
_neatlogs = None


def initialize_neatlogs() -> bool:
    """Initialize Neatlogs when configured; local runs still work without it."""
    global _initialized, _neatlogs
    if _initialized:
        return True
    api_key = os.environ.get("NEATLOGS_API_KEY")
    if not api_key:
        logger.info("NEATLOGS_API_KEY is not set; remote trace export is disabled")
        return False
    try:
        import neatlogs

        neatlogs.init(api_key=api_key, workflow_name="testgap-agent")
        _neatlogs = neatlogs
        _initialized = True
        logger.info("neatlogs instrumentation initialized")
        return True
    except ImportError:
        logger.warning("neatlogs is not installed; agent runs will not be traced")
    except Exception:
        logger.exception("neatlogs initialization failed; continuing without remote traces")
    return False


def langgraph_callbacks() -> list:
    """Return the documented Neatlogs callback for a LangGraph invocation."""
    if not _initialized or _neatlogs is None:
        return []
    try:
        return [_neatlogs.langchain_handler()]
    except Exception:
        logger.exception("Could not create Neatlogs LangGraph callback")
        return []
