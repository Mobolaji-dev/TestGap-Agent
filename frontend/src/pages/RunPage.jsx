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

const WORKFLOW_STEPS = [
  { id: "clone", label: "Clone repository" },
  { id: "inspection", label: "Inspect repository" },
  { id: "baseline", label: "Run baseline tests" },
  { id: "ranking", label: "Rank test gaps" },
  { id: "write_tests", label: "Draft tests" },
  { id: "verify_tests", label: "Verify generated tests" },
];

function getWorkflowSteps(run, events) {
  const hasCloneStep = run?.repository_url || events.some((event) => event.step === "clone");
  const steps = WORKFLOW_STEPS.filter((step) => step.id !== "clone" || hasCloneStep);
  const latestByStep = new Map();

  for (const event of events) {
    if (event.step && ["step.started", "step.progress", "step.completed", "step.failed"].includes(event.type)) {
      latestByStep.set(event.step, event);
    }
  }

  let activeStepId = run?.current_step || null;
  if (!activeStepId) {
    const activeEvent = [...events].reverse().find((event) =>
      event.type === "step.started" || event.type === "step.progress",
    );
    activeStepId = activeEvent?.step || null;
  }

  const activeEvent = activeStepId ? latestByStep.get(activeStepId) : null;
  const progressMessage = activeEvent?.message || run?.message || "Working on this step…";

  return steps.map((step) => {
    const event = latestByStep.get(step.id);
    let status = "waiting";
    if (event?.type === "step.failed") status = "failed";
    else if (event?.type === "step.completed") {
      status = event.status === "skipped" ? "skipped" : "complete";
    } else if (step.id === activeStepId && !isTerminalStatus(run?.status)) status = "active";
    else if (step.id === activeStepId && run?.status === "failed") status = "failed";
    else if (isTerminalStatus(run?.status)) status = "skipped";

    return {
      ...step,
      status,
      detail: status === "active" ? progressMessage : event?.message || null,
    };
  });
}

function RunProgress({ run, events, elapsedTime }) {
  const steps = getWorkflowSteps(run, events);
  const activeStep = steps.find((step) => step.status === "active");
  const isTerminal = isTerminalStatus(run?.status);
  const runLabel = run?.status === "queued"
    ? "Waiting to start"
    : activeStep?.label || (isTerminal ? "Run finished" : "Preparing run");

  return (
    <section className="run-progress" aria-label="Run progress">
      <div className="run-progress-heading">
        <div>
          <h2 className="text-heading-lg run-progress-title">What the agent is doing</h2>
          <p className="run-progress-current" role="status" aria-live="polite">
            {runLabel}{activeStep?.detail ? ` · ${activeStep.detail}` : ""}
          </p>
        </div>
        <div className="run-progress-clock" aria-label={`Elapsed time ${elapsedTime}`}>
          <span className="run-progress-clock-label">{isTerminal ? "Total time" : "Elapsed"}</span>
          <span className="run-progress-clock-value" aria-live="off">{elapsedTime}</span>
          {!isTerminal && <span className="run-progress-clock-caption">Live timer</span>}
        </div>
      </div>

      <ol className="run-step-list" aria-label="Agent workflow steps">
        {steps.map((step) => (
          <li key={step.id} className={`run-step run-step-${step.status}`}>
            <span className="run-step-marker" aria-hidden="true">
              {step.status === "complete" ? "✓" : step.status === "failed" ? "!" : step.status === "active" ? "●" : "○"}
            </span>
            <div className="run-step-copy">
              <span className="run-step-label">{step.label}</span>
              <span className="run-step-status">
                {step.status === "active" ? "In progress" : step.status === "complete" ? "Complete" : step.status === "failed" ? "Failed" : step.status === "skipped" ? "Skipped" : run?.status === "queued" ? "Waiting to start" : "Waiting"}
              </span>
              {step.status !== "active" && step.detail && (
                <span className="run-step-detail">{step.detail}</span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
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
  const runStatus = run?.status;
  const runCreatedAt = run?.created_at;

  // Active elapsed ticker
  useEffect(() => {
    if (!runStatus || isTerminalStatus(runStatus)) return;

    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [runStatus, runCreatedAt]);

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

        <RunProgress run={run} events={events} elapsedTime={elapsedTime} />

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
