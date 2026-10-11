import "./BaselineDetails.css";

/**
 * Baseline details component.
 * Renders free-form baseline properties honestly without assuming hardcoded keys.
 *
 * @param {Object} props
 * @param {Object} [props.baseline] - Free-form baseline object from backend
 */
export default function BaselineDetails({ baseline }) {
  const hasData =
    baseline &&
    typeof baseline === "object" &&
    !Array.isArray(baseline) &&
    Object.keys(baseline).length > 0;

  return (
    <section className="baseline-details-section" aria-label="Baseline Details">
      <h2 className="text-heading-lg baseline-title">Baseline Details</h2>

      {!hasData ? (
        <div className="baseline-empty-panel">
          <p className="text-body-sm baseline-empty-text">Not available</p>
        </div>
      ) : (
        <div className="baseline-kv-container">
          <dl className="baseline-kv-list">
            {Object.entries(baseline).map(([key, value]) => {
              const isComplex = typeof value === "object" && value !== null;

              return (
                <div key={key} className="baseline-kv-row">
                  <dt className="baseline-key text-code-md">{key}</dt>
                  <dd className="baseline-value">
                    {isComplex ? (
                      <pre className="baseline-nested-pre text-code-md">
                        {JSON.stringify(value, null, 2)}
                      </pre>
                    ) : (
                      <span className="text-body-sm baseline-primitive-value">
                        {value === null ? "null" : String(value)}
                      </span>
                    )}
                  </dd>
                </div>
              );
            })}
          </dl>
        </div>
      )}
    </section>
  );
}
