import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import useRun from "../hooks/useRun";
import StatusBadge from "../components/StatusBadge";
import MetricCards from "../components/results/MetricCards";
import BaselineDetails from "../components/results/BaselineDetails";
import RankedTargets from "../components/results/RankedTargets";
import CandidateTests from "../components/results/CandidateTests";
import DiffViewer from "../components/results/DiffViewer";
import EventTimeline from "../components/EventTimeline";
import "./ResultsPage.css";

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

function formatDuration(durationMs) {
  if (typeof durationMs !== "number" || durationMs <= 0 || isNaN(durationMs)) {
    return "—";
  }
  if (durationMs >= 1000) {
    return `${(durationMs / 1000).toFixed(1)}s`;
  }
  return `${durationMs}ms`;
}

function getFailureMessage(events, fallbackMessage) {
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
  return fallbackMessage || "Run encountered a failure.";
}

/**
 * Results screen at /results/:runId
 */
export default function ResultsPage() {
  const { runId } = useParams();
  const navigate = useNavigate();

  const { run, loading, error, errorStatus, refresh } = useRun(runId);
  const [isTimelineOpen, setIsTimelineOpen] = useState(false);

  const isNotFound =
    errorStatus === 404 ||
    (!run && error && (error.includes("404") || error.toLowerCase().includes("not found")));

  // 404 State
  if (isNotFound) {
    return (
      <main className="results-page" role="main">
        <div className="results-page-container">
          <div className="results-state-panel error-panel" role="alert">
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

  // Loading State
  if (loading && !run) {
    return (
      <main className="results-page" role="main" aria-busy="true">
        <div className="results-page-container">
          <div className="results-skeleton header-skeleton" aria-label="Loading results header" />
          <div className="results-skeleton cards-skeleton" aria-label="Loading metric cards" />
          <div className="results-skeleton rows-skeleton" aria-label="Loading results content" />
        </div>
      </main>
    );
  }

  // General Error State
  if (error && !run) {
    return (
      <main className="results-page" role="main">
        <div className="results-page-container">
          <div className="results-state-panel error-panel" role="alert">
            <h1 className="text-heading-lg panel-title">Error loading results</h1>
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

  const isInProgress = run.status === "queued" || run.status === "running";
  const isFailed = run.status === "failed";
  const isCancelled = run.status === "cancelled";
  const failureMessage = isFailed ? getFailureMessage(run.events, run.message) : null;
  const hasTraceUrl =
    typeof run.trace_url === "string" && run.trace_url.startsWith("https://");

  return (
    <main className="results-page" role="main">
      <div className="results-page-container">
        {/* 1. Header Card */}
        <section className="results-header-card" aria-label="Run Results Header">
          <div className="results-header-left">
            <div className="results-field">
              <span className="results-label text-caption-md">Run ID</span>
              <span className="results-value text-code-md">{run.run_id}</span>
            </div>

            <div className="results-field">
              <span className="results-label text-caption-md">Project</span>
              <span className="results-value text-body-sm">{run.project_id}</span>
            </div>

            <div className="results-field">
              <span className="results-label text-caption-md">Status</span>
              <div className="status-badge-container">
                <StatusBadge status={run.status} />
              </div>
            </div>

            <div className="results-field">
              <span className="results-label text-caption-md">Created</span>
              <span className="results-value text-body-sm">
                {formatDateTime(run.created_at)}
              </span>
            </div>

            <div className="results-field">
              <span className="results-label text-caption-md">Duration</span>
              <span className="results-value text-code-md">
                {formatDuration(run.metrics?.duration_ms)}
              </span>
            </div>
          </div>

          <div className="results-header-right">
            <div className="results-actions-group">
              <button
                type="button"
                onClick={() => navigate("/")}
                className="action-button"
              >
                NEW SCAN
              </button>

              <Link to={`/run/${runId}`} className="action-button-link">
                VIEW RUN
              </Link>

              {hasTraceUrl && (
                <a
                  href={run.trace_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="action-button-link external-trace-link"
                >
                  VIEW TRACE
                </a>
              )}
            </div>
          </div>
        </section>

        {/* In-progress run notice: do not render result sections */}
        {isInProgress && (
          <section className="in-progress-notice-panel" role="status">
            <h2 className="text-heading-lg in-progress-title">
              This run is still in progress.
            </h2>
            <p className="text-body-sm in-progress-text">
              Results will be generated once execution completes. You can monitor progress on the live Run screen.
            </p>
            <Link to={`/run/${runId}`} className="action-button-link in-progress-button">
              GO TO LIVE RUN
            </Link>
          </section>
        )}

        {/* Terminal Run sections */}
        {!isInProgress && (
          <>
            {/* 2. Warnings panel directly under header */}
            {Array.isArray(run.warnings) && run.warnings.length > 0 && (
              <section className="results-warnings-panel" aria-label="Run Warnings">
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

            {/* Failure notice for failed runs */}
            {isFailed && (
              <section className="results-failure-banner" role="alert">
                <h2 className="text-heading-lg failure-banner-title">Run failed</h2>
                <p className="text-body-sm failure-banner-text">{failureMessage}</p>
              </section>
            )}

            {/* Cancelled notice for cancelled runs */}
            {isCancelled && (
              <section className="results-cancelled-banner" role="status">
                <h2 className="text-heading-lg cancelled-banner-title">Run cancelled</h2>
                <p className="text-body-sm cancelled-banner-text">This run was cancelled.</p>
              </section>
            )}

            {/* 3. Metric cards in responsive grid */}
            <MetricCards
              metrics={run.metrics}
              candidateTests={run.candidate_tests}
            />

            {/* 4. Baseline details */}
            <BaselineDetails baseline={run.baseline} />

            {/* 5. Ranked targets */}
            <RankedTargets targets={run.targets} />

            {/* 6. Candidate tests (only when candidate_tests is non-empty) */}
            <CandidateTests candidateTests={run.candidate_tests} />

            {/* 7. Diff and patch (only when candidate_tests is non-empty) */}
            <DiffViewer
              runId={run.run_id}
              candidateTests={run.candidate_tests}
            />

            {/* 8. Run timeline collapsed section */}
            <section className="results-timeline-section" aria-label="Run Timeline">
              <button
                type="button"
                className="timeline-toggle-button"
                onClick={() => setIsTimelineOpen(!isTimelineOpen)}
                aria-expanded={isTimelineOpen}
                aria-controls="results-timeline-collapse"
              >
                <span className="text-heading-lg timeline-toggle-label">
                  RUN TIMELINE
                </span>
                <span className="text-caption-md timeline-toggle-indicator">
                  {isTimelineOpen ? "COLLAPSE" : "EXPAND"}
                </span>
              </button>

              {isTimelineOpen && (
                <div id="results-timeline-collapse" className="timeline-collapse-content">
                  <EventTimeline events={run.events || []} />
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
