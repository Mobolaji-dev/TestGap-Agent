import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import useRunStream, { isTerminalStatus } from "../hooks/useRunStream";
import { cancelRun } from "../api/testgapApi";
import StatusBadge from "../components/StatusBadge";
import ConnectionIndicator from "../components/ConnectionIndicator";
import EventTimeline from "../components/EventTimeline";
import "./RunPage.css";

function formatElapsed(ms) {
  if (ms < 0 || isNaN(ms)) return "00:00:00";
  const totalSec = Math.floor(ms / 1000);
  const hours = Math.floor(totalSec / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function getTerminalElapsed(run) {
  if (!run || !run.created_at || !run.updated_at) return "00:00:00";
  const created = new Date(run.created_at).getTime();
  const updated = new Date(run.updated_at).getTime();
  return formatElapsed(Math.max(0, updated - created));
}

function formatDateTime(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleString();
  } catch {
    return "—";
  }
}

function getFailureMessage(run, events) {
  if (Array.isArray(events) && events.length > 0) {
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i];
      if (
        e.status === "failure" ||
        e.status === "error" ||
        e.type === "run.failed" ||
        e.type === "step.failed"
      ) {
        if (e.message) return e.message;
      }
    }
  }
  return run?.message || "Run encountered a failure.";
}

/**
 * Live Run screen at /run/:runId
 */
export default function RunPage() {
  const { runId } = useParams();
  const navigate = useNavigate();

  const { run, events, connection, error, errorStatus, refresh } = useRunStream(runId);

  const [now, setNow] = useState(() => Date.now());
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState(null);

  // Active elapsed ticker
  useEffect(() => {
    if (!run || isTerminalStatus(run.status)) return;

    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [run]);

  // Derived elapsed time: frozen when terminal, ticking when active
  const elapsedTime = !run
    ? "00:00:00"
    : isTerminalStatus(run.status)
      ? getTerminalElapsed(run)
      : formatElapsed(Math.max(0, now - new Date(run.created_at).getTime()));

  // Handle Cancel
  const handleCancel = async () => {
    setIsCancelling(true);
    setCancelError(null);
    try {
      await cancelRun(runId);
      await refresh();
    } catch (err) {
      setCancelError(err.message || "Failed to cancel run.");
    } finally {
      setIsCancelling(false);
    }
  };

  const isNotFound = errorStatus === 404 || (!run && error && (error.includes("404") || error.toLowerCase().includes("not found")));

  // 404 Not Found state
  if (isNotFound) {
    return (
      <main className="run-page" role="main">
        <div className="run-page-container">
          <div className="state-panel error-panel" role="alert">
            <h1 className="text-heading-lg panel-title">Run not found</h1>
            <p className="text-body-sm panel-text">
              The run ID <code className="text-code-md run-id-code">{runId}</code> does not exist or could not be found.
            </p>
            <Link to="/" className="action-button-link">
              Back to Start
            </Link>
          </div>
        </div>
      </main>
    );
  }

  // Loading skeleton state
  if (!run && !error) {
    return (
      <main className="run-page" role="main" aria-busy="true">
        <div className="run-page-container">
          <div className="header-skeleton" aria-label="Loading run details" />
          <div className="timeline-skeleton" aria-label="Loading events timeline" />
        </div>
      </main>
    );
  }

  // Error on initial load (other than 404)
  if (!run && error) {
    return (
      <main className="run-page" role="main">
        <div className="run-page-container">
          <div className="state-panel error-panel" role="alert">
            <h1 className="text-heading-lg panel-title">Error loading run</h1>
            <p className="text-body-sm panel-text">{error}</p>
            <button
              type="button"
              onClick={() => refresh()}
              className="action-button"
            >
              Retry
            </button>
          </div>
        </div>
      </main>
    );
  }

  const isTerminal = isTerminalStatus(run.status);
  const failureMessage = run.status === "failed" ? getFailureMessage(run, events) : null;

  return (
    <main className="run-page" role="main">
      <div className="run-page-container">
        {/* Header card */}
        <section className="header-card" aria-label="Run Information">
          <div className="header-left">
            <div className="header-field">
              <span className="header-label text-caption-md">Run ID</span>
              <span className="header-value text-code-md">{run.run_id}</span>
            </div>

            <div className="header-field">
              <span className="header-label text-caption-md">Project</span>
              <span className="header-value text-body-sm">{run.project_id}</span>
            </div>

            <div className="header-field">
              <span className="header-label text-caption-md">Status</span>
              <div className="status-badge-wrapper">
                <StatusBadge status={run.status} />
                {run.status === "running" && (
                  <span
                    className="pulsing-running-dot"
                    aria-hidden="true"
                    title="Active scan in progress"
                  />
                )}
              </div>
            </div>

            <div className="header-field">
              <span className="header-label text-caption-md">Current Step</span>
              <span className="header-value text-code-md">
                {run.current_step || "—"}
              </span>
            </div>

            <div className="header-field">
              <span className="header-label text-caption-md">Elapsed</span>
              <span className="header-value text-code-md">{elapsedTime}</span>
            </div>

            <div className="header-field">
              <span className="header-label text-caption-md">Created</span>
              <span className="header-value text-body-sm">
                {formatDateTime(run.created_at)}
              </span>
            </div>
          </div>

          <div className="header-right">
            <div className="connection-section">
              <ConnectionIndicator connection={connection} />

              {connection === "polling" && (
                <p className="polling-notice text-body-sm" role="status">
                  Live updates are unavailable. Refreshing every few seconds.
                </p>
              )}
            </div>

            {["queued", "running"].includes(run.status) && (
              <div className="cancel-section">
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={isCancelling}
                  className="cancel-button"
                  aria-label="Cancel current run"
                >
                  {isCancelling ? "Cancelling…" : "Cancel Run"}
                </button>
                {cancelError && (
                  <p className="cancel-error text-body-sm" role="alert">
                    {cancelError}
                  </p>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Warnings panel - shown only when run.warnings is non-empty */}
        {Array.isArray(run.warnings) && run.warnings.length > 0 && (
          <section className="warnings-panel" aria-label="Run Warnings">
            <h2 className="text-heading-lg warnings-title">Warnings</h2>
            <ul className="warnings-list">
              {run.warnings.map((warning, idx) => (
                <li key={idx} className="warning-item text-body-sm">
                  {warning}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Event timeline */}
        <section className="timeline-section" aria-label="Event Timeline">
          <h2 className="text-heading-lg timeline-title">Event Timeline</h2>
          <EventTimeline events={events} />
        </section>

        {/* Outcome panel - shown only when terminal */}
        {isTerminal && (
          <section className="outcome-panel" aria-label="Run Outcome">
            {(run.status === "completed" || run.status === "completed_with_warnings") && (
              <>
                <h2 className="text-heading-lg outcome-title">
                  {run.status === "completed"
                    ? "Run completed"
                    : "Run completed with warnings"}
                </h2>
                <button
                  type="button"
                  onClick={() => navigate(`/results/${run.run_id}`)}
                  className="action-button"
                >
                  VIEW RESULTS
                </button>
              </>
            )}

            {run.status === "failed" && (
              <>
                <h2 className="text-heading-lg outcome-title outcome-failed-title">
                  Run failed
                </h2>
                <p className="outcome-failure-message text-body-sm">
                  {failureMessage}
                </p>
                <button
                  type="button"
                  onClick={() => navigate("/")}
                  className="action-button"
                >
                  NEW SCAN
                </button>
              </>
            )}

            {run.status === "cancelled" && (
              <>
                <h2 className="text-heading-lg outcome-title">Run cancelled</h2>
                <p className="outcome-cancelled-message text-body-sm">
                  This run was cancelled.
                </p>
                <button
                  type="button"
                  onClick={() => navigate("/")}
                  className="action-button"
                >
                  NEW SCAN
                </button>
              </>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
