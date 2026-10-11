import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)
_initialized = False
_neatlogs = None
_init_status = "not_initialized"


def initialize_neatlogs() -> bool:
    """Initialize Neatlogs when configured; local runs still work without it."""
    global _initialized, _neatlogs, _init_status
    if _initialized and _neatlogs is not None:
        return True
    api_key = settings.neatlogs_api_key
    if not api_key:
        _init_status = "missing_api_key"
        logger.info("NEATLOGS_API_KEY is not set; remote trace export is disabled")
        return False
    try:
        import neatlogs

        neatlogs.init(
            api_key=api_key.get_secret_value(),
            endpoint=settings.neatlogs_endpoint,
            workflow_name="testgap-analysis",
        )
        _neatlogs = neatlogs
        _initialized = True
        _init_status = "enabled"
        logger.info("Neatlogs tracing initialized (endpoint=%s)", settings.neatlogs_endpoint)
        return True
    except ImportError:
        _init_status = "sdk_missing"
        logger.warning("neatlogs is not installed; agent runs will not be traced")
    except Exception:
        _init_status = "initialization_failed"
        logger.exception("neatlogs initialization failed; continuing without remote traces")
    return False


def neatlogs_status() -> dict[str, str | bool]:
    """Return safe, non-secret tracing diagnostics for health and run events."""
    return {
        "configured": bool(settings.neatlogs_api_key),
        "initialized": _initialized and _neatlogs is not None,
        "status": _init_status,
        "endpoint": settings.neatlogs_endpoint,
    }


def langgraph_callbacks() -> list:
    """Return the documented Neatlogs callback for a LangGraph invocation."""
    if not _initialized or _neatlogs is None:
        return []
    try:
        return [_neatlogs.langchain_handler()]
    except Exception:
        logger.exception("Could not create Neatlogs LangGraph callback")
        return []


def wrap_llm_client(client, **attributes):
    """Capture direct OpenAI-compatible model calls when Neatlogs is configured."""
    if not initialize_neatlogs() or _neatlogs is None:
        return client
    try:
        trace_attributes = {
            f"testgap_{key}": value
            for key, value in attributes.items()
            if value is not None
        }
        return _neatlogs.wrap(client, **trace_attributes)
    except Exception:
        logger.exception("Could not wrap the model client with Neatlogs")
        return client


def shutdown_neatlogs() -> None:
    """Flush and close the Neatlogs SDK once when the API process exits."""
    global _initialized, _neatlogs, _init_status
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
        _init_status = "not_initialized"
