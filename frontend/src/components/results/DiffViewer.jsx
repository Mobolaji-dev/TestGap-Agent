import { useState } from "react";
import { getDiff, getPatch } from "../../api/testgapApi";
import "./DiffViewer.css";

/**
 * Format and highlight unified diff lines safely without innerHTML.
 */
function renderDiffLines(diffText) {
  if (!diffText) return null;
  const lines = diffText.split("\n");

  return lines.map((line, idx) => {
    let lineType = "diff-line-normal";

    if (line.startsWith("@@")) {
      lineType = "diff-line-hunk";
    } else if (line.startsWith("+") && !line.startsWith("+++")) {
      lineType = "diff-line-added";
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      lineType = "diff-line-removed";
    } else if (
      line.startsWith("diff ") ||
      line.startsWith("index ") ||
      line.startsWith("--- ") ||
      line.startsWith("+++ ")
    ) {
      lineType = "diff-line-meta";
    }

    return (
      <div key={idx} className={`diff-line ${lineType}`}>
        {line}
      </div>
    );
  });
}

/**
 * Diff preview and patch download component.
 * Allows safe inspection and file export without writing to disk.
 *
 * @param {Object} props
 * @param {string} props.runId - Run ID
 * @param {Array} props.candidateTests - Array of candidate tests
 */
export default function DiffViewer({ runId, candidateTests = [] }) {
  const [diffContent, setDiffContent] = useState(null);
  const [isDiffOpen, setIsDiffOpen] = useState(false);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [downloadingPatch, setDownloadingPatch] = useState(false);
  const [error, setError] = useState(null);

  if (!Array.isArray(candidateTests) || candidateTests.length === 0) {
    return null;
  }

  const handlePreviewDiff = async () => {
    if (isDiffOpen && diffContent !== null) {
      setIsDiffOpen(false);
      return;
    }

    if (diffContent !== null) {
      setIsDiffOpen(true);
      return;
    }

    try {
      setLoadingDiff(true);
      setError(null);
      const res = await getDiff(runId);
      setDiffContent(res.diff || "");
      setIsDiffOpen(true);
    } catch (err) {
      if (err.status === 409) {
        setError("No generated test is available for this run.");
      } else {
        setError(err.message || "Failed to load diff preview.");
      }
    } finally {
      setLoadingDiff(false);
    }
  };

  const handleDownloadPatch = async () => {
    try {
      setDownloadingPatch(true);
      setError(null);
      const blob = await getPatch(runId);
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${runId}.patch`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      if (err.status === 409) {
        setError("No generated test is available for this run.");
      } else {
        setError(err.message || "Failed to download patch.");
      }
    } finally {
      setDownloadingPatch(false);
    }
  };

  return (
    <section className="diff-viewer-section" aria-label="Diff and Patch Actions">
      <div className="diff-actions-header">
        <div className="diff-buttons-group">
          <button
            type="button"
            className="diff-action-button"
            onClick={handlePreviewDiff}
            disabled={loadingDiff || downloadingPatch}
            aria-expanded={isDiffOpen}
          >
            {loadingDiff
              ? "LOADING DIFF…"
              : isDiffOpen
              ? "HIDE DIFF"
              : "PREVIEW DIFF"}
          </button>

          <button
            type="button"
            className="diff-action-button"
            onClick={handleDownloadPatch}
            disabled={loadingDiff || downloadingPatch}
          >
            {downloadingPatch ? "DOWNLOADING…" : "DOWNLOAD PATCH"}
          </button>
        </div>

        <p className="diff-disclaimer-note text-caption-sm">
          Neither action applies changes to the source project.
        </p>
      </div>

      {error && (
        <div className="diff-error-panel" role="alert">
          <p className="text-body-sm diff-error-text">{error}</p>
        </div>
      )}

      {isDiffOpen && diffContent !== null && (
        <div className="diff-preview-container">
          <div className="diff-preview-header">
            <span className="text-caption-md diff-preview-label">Unified Diff</span>
          </div>
          <pre className="diff-pre text-code-md">
            {diffContent.trim() === "" ? (
              <span className="diff-empty-text">No diff content returned.</span>
            ) : (
              renderDiffLines(diffContent)
            )}
          </pre>
        </div>
      )}
    </section>
  );
}
