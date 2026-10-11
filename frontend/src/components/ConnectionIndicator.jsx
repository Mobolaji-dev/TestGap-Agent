import "./ConnectionIndicator.css";

/**
 * Connection status indicator
 * Shows LIVE, CONNECTING, RECONNECTING, POLLING, or CLOSED
 */
export default function ConnectionIndicator({ connection }) {
  const statusLabel = {
    connecting: "CONNECTING",
    live: "LIVE",
    reconnecting: "RECONNECTING",
    polling: "POLLING",
    closed: "CLOSED",
  }[connection];

  return (
    <div className="connection-indicator">
      <div className={`connection-dot connection-dot-${connection}`} />
      <span className="text-body-sm">{statusLabel}</span>
    </div>
  );
}
