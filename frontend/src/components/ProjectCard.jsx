import { HiCheck } from "react-icons/hi";
import clsx from "clsx";
import StatusBadge from "./StatusBadge";
import "./ProjectCard.css";

/**
 * Project card component for selecting a project on the Start screen
 * @param {Object} props
 * @param {Object} props.project - Project data
 * @param {string} props.project.id - Project ID
 * @param {string} props.project.name - Project name
 * @param {string} props.project.language - Programming language
 * @param {string} props.project.test_framework - Test framework
 * @param {string} props.project.path_label - Path label/description
 * @param {boolean} props.project.ready - Whether project is ready to scan
 * @param {string | null} props.project.warning - Warning message if any
 * @param {boolean} props.isSelected - Whether this project is selected
 * @param {Function} props.onSelect - Callback when card is clicked
 */
export default function ProjectCard({
  project,
  isSelected,
  onSelect,
}) {
  const handleClick = () => {
    if (project.ready) {
      onSelect(project.id);
    }
  };

  const handleKeyDown = (e) => {
    // Allow selection via Enter or Space keys
    if ((e.key === "Enter" || e.key === " ") && project.ready) {
      e.preventDefault();
      onSelect(project.id);
    }
  };

  const cardClass = clsx("project-card", {
    "project-card-selected": isSelected && project.ready,
    "project-card-disabled": !project.ready,
  });

  return (
    <div
      className={cardClass}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="radio"
      aria-checked={isSelected}
      aria-disabled={!project.ready}
      tabIndex={project.ready ? 0 : -1}
    >
      {/* Selected indicator */}
      {isSelected && project.ready && (
        <div className="project-card-check">
          <HiCheck size={20} />
        </div>
      )}

      {/* Project info */}
      <div className="project-card-content">
        <h3 className="text-body-md project-card-name">{project.name}</h3>

        <div className="project-card-meta">
          <span className="text-body-sm">{project.language}</span>
          <span className="text-body-sm">•</span>
          <span className="text-body-sm">
            {project.test_framework ?? "No test framework detected"}
          </span>
        </div>

        <div className="project-card-path text-code-md">
          {project.path_label}
        </div>

        {/* Status badge */}
        <div className="project-card-badge">
          <StatusBadge
            status={project.ready ? "ready" : "not-ready"}
          />
        </div>

        {/* Not ready explanation */}
        {!project.ready && (
          <div className="project-card-warning text-body-sm">
            pytest is required to scan this project.
          </div>
        )}

        {/* Warning message if present */}
        {project.warning && (
          <div className="project-card-warning text-body-sm">
            {project.warning}
          </div>
        )}
      </div>
    </div>
  );
}
