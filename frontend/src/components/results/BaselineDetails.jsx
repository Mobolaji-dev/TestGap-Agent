import { useState } from "react";
import "./BaselineDetails.css";

/**
 * Format a list of line numbers into compact ranges, e.g. [1, 2, 3, 5, 8] -> "L1–3, L5, L8"
 */
function formatLineRanges(lines) {
  if (!Array.isArray(lines) || lines.length === 0) return "All covered";
  const sorted = [...new Set(lines)].filter((n) => typeof n === "number").sort((a, b) => a - b);
  if (sorted.length === 0) return "All covered";

  const ranges = [];
  let start = sorted[0];
  let end = start;

  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === end + 1) {
      end = sorted[i];
    } else {
      ranges.push(start === end ? `L${start}` : `L${start}–${end}`);
      start = sorted[i];
      end = start;
    }
  }
  ranges.push(start === end ? `L${start}` : `L${start}–${end}`);
  return ranges.join(", ");
}

/**
 * Strip giant line arrays from raw debug view so it never blows out the UI.
 */
function sanitizeForRawView(obj) {
  if (!obj || typeof obj !== "object") return obj;
  if (Array.isArray(obj)) {
    if (obj.length > 8 && obj.every((item) => typeof item === "number")) {
      return `[${obj.length} lines: ${formatLineRanges(obj)}]`;
    }
    return obj.map(sanitizeForRawView);
  }

  const clean = {};
  for (const [k, v] of Object.entries(obj)) {
    if (k === "executed_lines" && Array.isArray(v)) {
      clean[k] = `[${v.length} executed lines]`;
    } else if (k === "functions" || k === "classes") {
      continue;
    } else if (typeof v === "object" && v !== null) {
      clean[k] = sanitizeForRawView(v);
    } else {
      clean[k] = v;
    }
  }
  return clean;
}

/**
 * Baseline details component.
 * Renders structured baseline summary, clean file coverage breakdown,
 * and collapsible output while avoiding horizontal layout stretching.
 *
 * @param {Object} props
 * @param {Object} [props.baseline] - Baseline object from backend
 */
export default function BaselineDetails({ baseline }) {
  const [showAllFiles, setShowAllFiles] = useState(false);

  const hasData =
    baseline &&
    typeof baseline === "object" &&
    !Array.isArray(baseline) &&
    Object.keys(baseline).length > 0;

  if (!hasData) {
    return (
      <section className="baseline-details-section" aria-label="Baseline Details">
        <h2 className="text-heading-lg baseline-title">Baseline Details</h2>
        <div className="baseline-empty-panel">
          <p className="text-body-sm baseline-empty-text">Not available</p>
        </div>
      </section>
    );
  }

  const {
    command,
    exit_code,
    baseline_status,
    coverage_totals,
    test_environment,
    stdout,
    stderr,
    files,
  } = baseline;

  const fileEntries = files && typeof files === "object" ? Object.entries(files) : [];
  // Sort files: files with missing lines / lower percent first
  const sortedFiles = [...fileEntries].sort((a, b) => {
    const aMissing = a[1]?.missing_lines?.length || 0;
    const bMissing = b[1]?.missing_lines?.length || 0;
    if (bMissing !== aMissing) return bMissing - aMissing;
    const aPct = a[1]?.summary?.percent_covered ?? 100;
    const bPct = b[1]?.summary?.percent_covered ?? 100;
    return aPct - bPct;
  });

  const visibleFiles = showAllFiles ? sortedFiles : sortedFiles.slice(0, 5);

  return (
    <section className="baseline-details-section" aria-label="Baseline Details">
      <div className="baseline-section-header">
        <h2 className="text-heading-lg baseline-title">Baseline Details</h2>
        {baseline_status && (
          <span className={`baseline-status-badge baseline-status-${baseline_status}`}>
            {baseline_status}
          </span>
        )}
      </div>

      <div className="baseline-card">
        {/* Top Summary Grid */}
        <div className="baseline-summary-grid">
          {command && (
            <div className="baseline-summary-item baseline-col-full">
              <span className="baseline-summary-label text-caption-sm">Command</span>
              <div className="baseline-cmd-wrapper">
                <code className="baseline-cmd text-code-md">{command}</code>
              </div>
            </div>
          )}

          <div className="baseline-summary-item">
            <span className="baseline-summary-label text-caption-sm">Exit Code</span>
            <span
              className={`baseline-summary-value text-body-sm font-semibold ${
                exit_code === 0 ? "text-success" : "text-danger"
              }`}
            >
              {exit_code ?? "—"}
            </span>
          </div>

          {coverage_totals && (
            <div className="baseline-summary-item">
              <span className="baseline-summary-label text-caption-sm">Baseline Coverage</span>
              <span className="baseline-summary-value text-body-sm font-semibold">
                {coverage_totals.percent_covered != null
                  ? `${Number(coverage_totals.percent_covered).toFixed(1)}%`
                  : "Unavailable"}
                {coverage_totals.covered_lines != null &&
                  coverage_totals.num_statements != null && (
                    <span className="baseline-summary-sub text-caption-sm">
                      {" "}({coverage_totals.covered_lines}/{coverage_totals.num_statements} stmts)
                    </span>
                  )}
              </span>
            </div>
          )}

          {test_environment && (
            <div className="baseline-summary-item">
              <span className="baseline-summary-label text-caption-sm">Test Environment</span>
              <span className="baseline-summary-value text-body-sm">
                {test_environment.status || "ready"}
                {test_environment.dependency_manifest && (
                  <span className="baseline-summary-sub text-caption-sm">
                    {" "}({test_environment.dependency_manifest})
                  </span>
                )}
              </span>
            </div>
          )}
        </div>

        {/* Files Coverage Breakdown (replaces raw number dumps) */}
        {sortedFiles.length > 0 && (
          <div className="baseline-files-section">
            <div className="baseline-files-header">
              <span className="text-body-sm font-semibold baseline-files-title">
                File Coverage ({sortedFiles.length} {sortedFiles.length === 1 ? "file" : "files"} analyzed)
              </span>
              {sortedFiles.length > 5 && (
                <button
                  type="button"
                  className="baseline-files-toggle-btn text-caption-sm"
                  onClick={() => setShowAllFiles(!showAllFiles)}
                >
                  {showAllFiles ? "Show fewer files" : `Show all ${sortedFiles.length} files`}
                </button>
              )}
            </div>

            <div className="baseline-files-table-wrapper">
              <table className="baseline-files-table">
                <thead>
                  <tr>
                    <th className="text-caption-sm">File</th>
                    <th className="text-caption-sm">Coverage</th>
                    <th className="text-caption-sm">Uncovered Lines</th>
                    <th className="text-caption-sm">Statements</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleFiles.map(([filePath, fileData]) => {
                    const summary = fileData?.summary || {};
                    const pct =
                      summary.percent_covered != null
                        ? Number(summary.percent_covered).toFixed(0)
                        : "—";
                    const missing = fileData?.missing_lines || [];
                    const hasMissing = missing.length > 0;

                    return (
                      <tr key={filePath} className="baseline-file-row">
                        <td className="baseline-file-path text-code-md" title={filePath}>
                          {filePath}
                        </td>
                        <td className="baseline-file-pct">
                          <span
                            className={`baseline-pct-chip ${
                              hasMissing ? "pct-has-gaps" : "pct-clean"
                            }`}
                          >
                            {pct}%
                          </span>
                        </td>
                        <td className="baseline-file-missing text-code-md">
                          <span className={hasMissing ? "text-missing" : "text-all-covered"}>
                            {formatLineRanges(missing)}
                          </span>
                        </td>
                        <td className="baseline-file-stmts text-caption-sm">
                          {summary.covered_lines ?? "—"} / {summary.num_statements ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pytest Output */}
        {stdout && stdout.trim().length > 0 && (
          <details className="baseline-collapsible">
            <summary className="baseline-collapsible-summary text-body-sm">
              <span>Pytest Output ({stdout.trim().split("\n").length} lines)</span>
              <span className="baseline-collapsible-tag text-caption-sm">terminal</span>
            </summary>
            <pre className="baseline-terminal-pre text-code-md">{stdout}</pre>
          </details>
        )}

        {/* Stderr if present */}
        {stderr && stderr.trim().length > 0 && (
          <details className="baseline-collapsible">
            <summary className="baseline-collapsible-summary text-body-sm baseline-stderr-summary">
              <span>Standard Error</span>
              <span className="baseline-collapsible-tag text-caption-sm">view</span>
            </summary>
            <pre className="baseline-terminal-pre baseline-stderr-pre text-code-md">{stderr}</pre>
          </details>
        )}

        {/* Raw Baseline JSON (compact, clean, collapsible) */}
        <details className="baseline-collapsible">
          <summary className="baseline-collapsible-summary text-caption-sm">
            <span>Raw Baseline Data (collapsed)</span>
            <span className="baseline-collapsible-tag text-caption-sm">json</span>
          </summary>
          <pre className="baseline-raw-pre text-code-md">
            {JSON.stringify(sanitizeForRawView(baseline), null, 2)}
          </pre>
        </details>
      </div>
    </section>
  );
}
