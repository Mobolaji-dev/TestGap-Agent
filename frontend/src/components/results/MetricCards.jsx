import "./MetricCards.css";

/**
 * Metric cards grid displaying run coverage and candidate test metrics.
 * Adheres strictly to the honesty rule: never shows uncomputed backend metrics as 0 or 0%.
 *
 * @param {Object} props
 * @param {Object} [props.metrics] - Run metrics object
 * @param {Array} [props.candidateTests] - Array of candidate tests
 */
export default function MetricCards({ metrics, candidateTests = [] }) {
  const hasBaselinePct = typeof metrics?.coverage_before_pct === "number";
  const baselineCoverage = hasBaselinePct
    ? `${metrics.coverage_before_pct.toFixed(1)}%`
    : "Not available";

  const hasCoverageAfter = typeof metrics?.coverage_after_pct === "number";
  const coverageAfter = hasCoverageAfter
    ? `${metrics.coverage_after_pct.toFixed(1)}%`
    : "Not available";

  const attempted = typeof metrics?.mutations_attempted === "number" ? metrics.mutations_attempted : 0;
  const killed = typeof metrics?.mutations_killed === "number" ? metrics.mutations_killed : 0;
  const hasMutationScore = attempted > 0;
  const mutationScore = hasMutationScore
    ? `${killed} / ${attempted} killed`
    : "Not available";

  const testDraftsGenerated = Array.isArray(candidateTests)
    ? candidateTests.length
    : 0;

  const cards = [
    {
      title: "Baseline coverage",
      value: baselineCoverage,
      isAvailable: hasBaselinePct,
    },
    {
      title: "Coverage after",
      value: coverageAfter,
      isAvailable: hasCoverageAfter,
    },
    {
      title: "Mutation score",
      value: mutationScore,
      isAvailable: hasMutationScore,
    },
    {
      title: "Test drafts generated",
      value: testDraftsGenerated,
      isAvailable: true,
    },
  ];

  return (
    <section className="metric-cards-section" aria-label="Run Metrics">
      <div className="metric-cards-grid">
        {cards.map((card, idx) => (
          <div key={idx} className="metric-card">
            <span className="metric-card-title text-caption-md">{card.title}</span>
            <span
              className={`metric-card-value ${
                card.isAvailable ? "text-display-metric" : "text-unavailable"
              }`}
            >
              {card.value}
            </span>
          </div>
        ))}
      </div>
      <p className="metric-cards-caption text-caption-sm">
        Not available means the backend has not computed this yet.
      </p>
    </section>
  );
}
