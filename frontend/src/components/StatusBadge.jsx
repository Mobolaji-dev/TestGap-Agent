import clsx from "clsx";
import "./StatusBadge.css";

/**
 * Status badge component for displaying status labels
 * @param {Object} props
 * @param {string} props.status - Status value: "ready", "not-ready", "queued", "running", "completed", "completed_with_warnings", "failed", "cancelled"
 * @param {string} [props.className] - Additional CSS classes
 */
export default function StatusBadge({ status, className }) {
  const badgeClass = clsx("status-badge", `status-${status}`, className);

  const statusLabels = {
    ready: "Ready",
    "not-ready": "Not Ready",
    queued: "Queued",
    running: "Running",
    completed: "Completed",
    completed_with_warnings: "Completed with Warnings",
    failed: "Failed",
    cancelled: "Cancelled",
  };

  const label = statusLabels[status] || status;

  return <span className={badgeClass}>{label}</span>;
}
