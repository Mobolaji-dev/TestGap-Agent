import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from pydantic import SecretStr

import agent.telemetry as telemetry


def _reset_telemetry(monkeypatch):
    monkeypatch.setattr(telemetry, "_initialized", False)
    monkeypatch.setattr(telemetry, "_neatlogs", None)
    monkeypatch.setattr(telemetry, "_init_status", "not_initialized")


def test_neatlogs_initialization_and_model_trace_tags(monkeypatch):
    _reset_telemetry(monkeypatch)
    fake_sdk = ModuleType("neatlogs")
    fake_sdk.init = Mock()
    fake_sdk.wrap = Mock(return_value="wrapped-client")
    fake_sdk.langchain_handler = Mock(return_value="handler")
    monkeypatch.setitem(sys.modules, "neatlogs", fake_sdk)
    monkeypatch.setattr(
        telemetry,
        "settings",
        SimpleNamespace(
            neatlogs_api_key=SecretStr("test-key"),
            neatlogs_endpoint="https://eu.ingest.neatlogs.com",
        ),
    )

    assert telemetry.initialize_neatlogs() is True
    fake_sdk.init.assert_called_once_with(
        api_key="test-key",
        endpoint="https://eu.ingest.neatlogs.com",
        workflow_name="testgap-analysis",
    )
    assert telemetry.langgraph_callbacks() == ["handler"]
    assert telemetry.wrap_llm_client(
        "client", run_id="run-123", project_id="project-456", target="app/auth.py"
    ) == "wrapped-client"
    fake_sdk.wrap.assert_called_once_with(
        "client",
        testgap_run_id="run-123",
        testgap_project_id="project-456",
        testgap_target="app/auth.py",
    )
    assert telemetry.neatlogs_status() == {
        "configured": True,
        "initialized": True,
        "status": "enabled",
        "endpoint": "https://eu.ingest.neatlogs.com",
    }


def test_neatlogs_status_explains_missing_key(monkeypatch):
    _reset_telemetry(monkeypatch)
    monkeypatch.setattr(
        telemetry,
        "settings",
        SimpleNamespace(neatlogs_api_key=None, neatlogs_endpoint="https://ingest.neatlogs.com"),
    )

    assert telemetry.initialize_neatlogs() is False
    assert telemetry.neatlogs_status() == {
        "configured": False,
        "initialized": False,
        "status": "missing_api_key",
        "endpoint": "https://ingest.neatlogs.com",
    }
