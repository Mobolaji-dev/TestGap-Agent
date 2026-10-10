import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)
_initialized = False
_neatlogs = None


def initialize_neatlogs() -> bool:
    """Initialize Neatlogs when configured; local runs still work without it."""
    global _initialized, _neatlogs
    if _initialized and _neatlogs is not None:
        return True
    api_key = settings.neatlogs_api_key
    if not api_key:
        logger.info("NEATLOGS_API_KEY is not set; remote trace export is disabled")
        return False
    try:
        import neatlogs

        neatlogs.init(
            api_key=api_key.get_secret_value(),
            endpoint="https://ingest.neatlogs.com",
            workflow_name="testgap-analysis",
        )
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


def wrap_llm_client(client):
    """Capture direct OpenAI-compatible model calls when Neatlogs is configured."""
    if not initialize_neatlogs() or _neatlogs is None:
        return client
    try:
        return _neatlogs.wrap(client)
    except Exception:
        logger.exception("Could not wrap the model client with Neatlogs")
        return client


def shutdown_neatlogs() -> None:
    """Flush and close the Neatlogs SDK once when the API process exits."""
    global _initialized, _neatlogs
    if not _initialized or _neatlogs is None:
        return
    try:
        _neatlogs.flush()
    except Exception:
        logger.exception("Could not flush Neatlogs telemetry")
    try:
        _neatlogs.shutdown()
    except Exception:
        logger.exception("Could not shut down Neatlogs telemetry")
    finally:
        _neatlogs = None
        _initialized = False
