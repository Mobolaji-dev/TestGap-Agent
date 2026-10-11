import { useState } from "react";
import "./RankedTargets.css";

function TargetRow({ target, rank }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const uncoveredCount = Array.isArray(target.uncovered_lines)
    ? target.uncovered_lines.length
    : 0;

  return (
    <article className="ranked-target-card" aria-label={`Target ${rank}: ${target.symbol}`}>
      <div className="target-header-row">
        <div className="target-title-group">
          <span className="target-rank-badge text-caption-md">#{rank}</span>
          <span className="target-path text-code-md">{target.path}</span>
          <span className="target-symbol text-body-sm">{target.symbol}</span>
        </div>

        <div className="target-meta-group">
          <span className="target-line-range text-code-md">
            L{target.line_start}–L{target.line_end}
          </span>
          <span className="target-priority text-body-sm">
            Heuristic priority: <strong>{target.priority_score}</strong>
          </span>
          <span className="target-uncovered-count text-body-sm">
            {uncoveredCount} uncovered {uncoveredCount === 1 ? "line" : "lines"}
          </span>
        </div>
      </div>

      {Array.isArray(target.rationale) && target.rationale.length > 0 && (
        <div className="target-rationales">
          <span className="target-rationales-label text-caption-sm">Rationale:</span>
          <ul className="target-rationales-list">
            {target.rationale.map((reason, idx) => (
              <li key={idx} className="target-rationale-item text-body-sm">
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {uncoveredCount > 0 && (
        <div className="target-expand-container">
          <button
            type="button"
            className="target-expand-button"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            aria-controls={`target-uncovered-${rank}`}
          >
            {isExpanded ? "Hide uncovered lines" : "Show uncovered lines"}
          </button>

          {isExpanded && (
            <div
              id={`target-uncovered-${rank}`}
              className="target-uncovered-lines text-code-md"
            >
              <span className="text-caption-sm">Uncovered line numbers: </span>
              {target.uncovered_lines.join(", ")}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

/**
 * Ranked targets list component.
 * Displays risks ranked by the backend in API order with heuristic priority label.
 *
 * @param {Object} props
 * @param {Array} [props.targets] - Array of RiskTarget objects
 */
export default function RankedTargets({ targets = [] }) {
  const hasTargets = Array.isArray(targets) && targets.length > 0;

  return (
    <section className="ranked-targets-section" aria-label="Ranked Targets">
      <h2 className="text-heading-lg targets-section-title">Ranked Targets</h2>

      {!hasTargets ? (
        <div className="targets-empty-panel">
          <p className="text-body-sm targets-empty-text">No targets were ranked.</p>
        </div>
      ) : (
        <div className="targets-list">
          {targets.map((target, idx) => (
            <TargetRow key={`${target.path}-${target.symbol}-${idx}`} target={target} rank={idx + 1} />
          ))}
        </div>
      )}
    </section>
  );
}
