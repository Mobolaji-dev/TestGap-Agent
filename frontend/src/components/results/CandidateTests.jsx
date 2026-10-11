import { useState } from "react";
import "./CandidateTests.css";

function CandidateCard({ candidate, index }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(candidate.content || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is restricted
      const textarea = document.createElement("textarea");
      textarea.value = candidate.content || "";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <article className="candidate-card" aria-label={`Candidate test ${index + 1}: ${candidate.test_path}`}>
      <div className="candidate-header">
        <div className="candidate-paths">
          <div className="candidate-path-row">
            <span className="candidate-path-label text-caption-md">Test path</span>
            <span className="candidate-path-value text-code-md">{candidate.test_path}</span>
          </div>
          <div className="candidate-path-row">
            <span className="candidate-path-label text-caption-md">Target path</span>
            <span className="candidate-path-value text-code-md">{candidate.target_path}</span>
          </div>
        </div>

        <div className="candidate-meta">
          <span className="draft-badge text-caption-md">GENERATED · UNVERIFIED</span>
          {candidate.model && (
            <span className="candidate-model text-body-sm">
              Model: <span className="text-code-md">{candidate.model}</span>
            </span>
          )}
          <button
            type="button"
            className="copy-button"
            onClick={handleCopy}
            aria-label={`Copy candidate test code for ${candidate.test_path}`}
          >
            {copied ? "COPIED!" : "COPY"}
          </button>
        </div>
      </div>

      <div className="candidate-code-container">
        <pre className="candidate-code-pre text-code-md">
          <code>{candidate.content || ""}</code>
        </pre>
      </div>
    </article>
  );
}

/**
 * Candidate tests panel.
 * Displays generated draft tests with honest unverified labels and copy control.
 *
 * @param {Object} props
 * @param {Array} props.candidateTests - Array of TestCandidate objects
 */
export default function CandidateTests({ candidateTests = [] }) {
  if (!Array.isArray(candidateTests) || candidateTests.length === 0) {
    return null;
  }

  return (
    <section className="candidate-tests-section" aria-label="Candidate Tests">
      <div className="candidate-tests-header">
        <h2 className="text-heading-lg candidate-title">Test drafts</h2>
        <p className="candidate-disclaimer text-body-sm">
          These are drafts. They have not been run, repaired, mutation-verified, or applied to your project.
        </p>
      </div>

      <div className="candidate-tests-list">
        {candidateTests.map((candidate, idx) => (
          <CandidateCard
            key={`${candidate.test_path}-${idx}`}
            candidate={candidate}
            index={idx}
          />
        ))}
      </div>
    </section>
  );
}
