import { useState, useRef, useEffect } from "react";
import "./EventTimeline.css";

const KNOWN_EVENT_TYPES = new Set([
  "run.queued",
  "run.started",
  "step.started",
  "step.completed",
  "step.failed",
  "warning",
  "run.completed",
  "run.failed",
  "run.cancelled",
]);

function formatLocalTime(timestamp) {
  if (!timestamp) return "—";
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return "—";
    const h = String(d.getHours()).padStart(2, "0");
    const m = String(d.getMinutes()).padStart(2, "0");
    const s = String(d.getSeconds()).padStart(2, "0");
    return `${h}:${m}:${s}`;
  } catch {
    return "—";
  }
}

function getStatusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "success") return "event-status-success";
  if (s === "warning") return "event-status-warning";
  if (s === "failure" || s === "error") return "event-status-danger";
  return "event-status-default";
}

function EventDetails({ data }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
    return null;
  }

  return (
    <div className="event-details">
      <button
        type="button"
        className="event-details-button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        {isExpanded ? "Hide Details" : "Details"}
      </button>
      {isExpanded && (
        <pre className="event-details-content">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

/**
 * Event timeline component.
 * Displays real-time and stored run events with auto-scroll and detailed JSON inspector.
 */
export default function EventTimeline({ events = [] }) {
  const timelineRef = useRef(null);
  const isNearBottomRef = useRef(true);

  const handleScroll = () => {
    const el = timelineRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isNearBottomRef.current = distanceFromBottom < 50;
  };

  useEffect(() => {
    const el = timelineRef.current;
    if (!el) return;
    if (isNearBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [events]);

  if (!events || events.length === 0) {
    return (
      <div className="event-timeline-empty" aria-live="polite">
        <p className="text-body-sm empty-timeline-text">Waiting for the first event…</p>
      </div>
    );
  }

  return (
    <div
      className="event-timeline"
      ref={timelineRef}
      onScroll={handleScroll}
      role="log"
      aria-live="polite"
      aria-atomic="false"
      aria-label="Event timeline"
    >
      {events.map((event, index) => {
        const eventKey = event.event_id ?? event.id ?? index;
        const isKnownType = event.type ? KNOWN_EVENT_TYPES.has(event.type) : true;

        return (
          <div key={eventKey} className="event-row">
            <div className="event-row-main">
              <span className="event-time text-code-md">
                {formatLocalTime(event.timestamp)}
              </span>

              <div className="event-step-container">
                <span className="event-step text-code-md">
                  {event.step || (event.type && !isKnownType ? event.type : "—")}
                </span>
                {!isKnownType && event.type && event.step && (
                  <span className="event-unknown-type text-code-md">
                    ({event.type})
                  </span>
                )}
              </div>

              <span className={`event-status text-body-sm ${getStatusClass(event.status)}`}>
                {event.status || "—"}
              </span>

              <span className="event-message text-body-sm">
                {event.message || "—"}
              </span>
            </div>

            <EventDetails data={event.data} />
          </div>
        );
      })}
    </div>
  );
}
