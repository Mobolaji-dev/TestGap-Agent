import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  listProjects,
  createRunFromRepo,
  createRunFromProject,
} from "../api/testgapApi";
import ProjectCard from "../components/ProjectCard";
import SegmentedSwitch from "../components/SegmentedSwitch";
import RepoInput from "../components/RepoInput";
import { parseGithubUrl } from "../utils/githubUrl";
import "./StartPage.css";

const TARGET_LIMIT_MIN = 1;
const TARGET_LIMIT_MAX = 10;
const TARGET_LIMIT_DEFAULT = 3;

const REPAIR_LIMIT_MIN = 0;
const REPAIR_LIMIT_MAX = 2;
const REPAIR_LIMIT_DEFAULT = 2;

const MODE_OPTIONS = [
  { value: "repo", label: "GITHUB REPO" },
  { value: "demo", label: "DEMO PROJECTS" },
];

/**
 * Start screen - GitHub repo scanner and demo project selector with scan configuration.
 */
export default function StartPage() {
  const navigate = useNavigate();

  // Mode: "repo" (default) or "demo"
  const [mode, setMode] = useState("repo");

  // GitHub repo mode state
  const [repoUrl, setRepoUrl] = useState("");
  const [repoParsed, setRepoParsed] = useState(null);

  // Demo projects mode state (lazy-loaded when tab opened, then cached)
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectsLoaded, setProjectsLoaded] = useState(false);
  const [projectsError, setProjectsError] = useState(null);
  const [slowBackend, setSlowBackend] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState(null);

  // Shared scan configuration state (preserved across mode switches)
  const [targetLimit, setTargetLimit] = useState(TARGET_LIMIT_DEFAULT);
  const [repairLimit, setRepairLimit] = useState(REPAIR_LIMIT_DEFAULT);
  const [verifyMutations, setVerifyMutations] = useState(true);

  // Validation errors
  const [targetError, setTargetError] = useState(null);
  const [repairError, setRepairError] = useState(null);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // For slow backend timeout
  const slowBackendTimeout = useRef(null);

  // Fetch demo projects only on demand
  const fetchProjects = useCallback(async () => {
    try {
      setProjectsLoading(true);
      setProjectsError(null);
      setSlowBackend(false);

      slowBackendTimeout.current = setTimeout(() => {
        setSlowBackend(true);
      }, 6000);

      const data = await listProjects();

      if (!Array.isArray(data)) {
        setProjectsError("Invalid projects response from backend");
        return;
      }

      setProjects(data);
      setProjectsLoaded(true);

      // Try to preselect "demo-flask-shop" if it exists and is ready
      const demoProject = data.find(
        (p) => p.name === "demo-flask-shop" && p.ready,
      );
      if (demoProject) {
        setSelectedProjectId(demoProject.id);
      } else {
        const firstReady = data.find((p) => p.ready);
        if (firstReady) {
          setSelectedProjectId(firstReady.id);
        }
      }
    } catch (err) {
      setProjectsError(err.message || "Failed to load projects.");
    } finally {
      if (slowBackendTimeout.current) {
        clearTimeout(slowBackendTimeout.current);
      }
      setProjectsLoading(false);
      setSlowBackend(false);
    }
  }, []);

  // Handle switching tabs
  const handleModeChange = useCallback(
    (newMode) => {
      setMode(newMode);
      setSubmitError(null);

      // Lazy load demo projects on first switch to DEMO PROJECTS tab
      if (newMode === "demo" && !projectsLoaded && !projectsLoading) {
        fetchProjects();
      }
    },
    [projectsLoaded, projectsLoading, fetchProjects],
  );

  // Validate target limit
  const validateTargetLimit = (value) => {
    const num = Number(value);
    if (isNaN(num)) {
      setTargetError("Must be a number");
      return false;
    }
    if (num < TARGET_LIMIT_MIN || num > TARGET_LIMIT_MAX) {
      setTargetError(
        `Must be between ${TARGET_LIMIT_MIN} and ${TARGET_LIMIT_MAX}`,
      );
      return false;
    }
    setTargetError(null);
    return true;
  };

  // Validate repair limit
  const validateRepairLimit = (value) => {
    const num = Number(value);
    if (isNaN(num)) {
      setRepairError("Must be a number");
      return false;
    }
    if (num < REPAIR_LIMIT_MIN || num > REPAIR_LIMIT_MAX) {
      setRepairError(
        `Must be between ${REPAIR_LIMIT_MIN} and ${REPAIR_LIMIT_MAX}`,
      );
      return false;
    }
    setRepairError(null);
    return true;
  };

  const handleTargetLimitChange = (e) => {
    const value = e.target.value;
    setTargetLimit(value);
    validateTargetLimit(value);
  };

  const handleRepairLimitChange = (e) => {
    const value = e.target.value;
    setRepairLimit(value);
    validateRepairLimit(value);
  };

  // Form submission handler
  const handleSubmit = async (e) => {
    if (e && e.preventDefault) {
      e.preventDefault();
    }
    if (isSubmitting) return;
    setSubmitError(null);

    // Validate limit fields
    if (!validateTargetLimit(targetLimit)) return;
    if (!validateRepairLimit(repairLimit)) return;

    try {
      setIsSubmitting(true);

      let response;
      if (mode === "repo") {
        const validation = parseGithubUrl(repoUrl);
        if (!validation.ok) {
          setRepoParsed(null);
          return;
        }
        response = await createRunFromRepo(
          validation.url,
          Number(targetLimit),
          Number(repairLimit),
          Boolean(verifyMutations),
        );
      } else {
        const selectedProject = Array.isArray(projects)
          ? projects.find((p) => p.id === selectedProjectId)
          : null;
        if (!selectedProject || !selectedProject.ready) {
          setSubmitError("Please select a ready project");
          return;
        }
        response = await createRunFromProject(
          selectedProjectId,
          Number(targetLimit),
          Number(repairLimit),
          Boolean(verifyMutations),
        );
      }

      if (!response || !response.run_id) {
        setSubmitError("The backend did not return a run id.");
        return;
      }

      navigate(`/run/${response.run_id}`);
    } catch (err) {
      if (err.status) {
        if (err.status === 404) {
          setSubmitError("The backend could not find that repository.");
        } else if (err.status >= 500 && err.status <= 599) {
          setSubmitError(
            "The backend had a problem starting this scan. Try again in a moment.",
          );
        } else if (
          err.status === 400 ||
          err.status === 422 ||
          err.status === 409
        ) {
          setSubmitError(err.message);
        } else {
          setSubmitError(err.message || `Error (${err.status})`);
        }
      } else {
        setSubmitError(
          "Could not reach the backend. The run may or may not have started, so check before trying again.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedProject = Array.isArray(projects)
    ? projects.find((p) => p.id === selectedProjectId)
    : null;

  const canStartScan =
    !isSubmitting &&
    !targetError &&
    !repairError &&
    (mode === "repo" ? Boolean(repoParsed?.ok) : Boolean(selectedProject?.ready));

  return (
    <div className="start-page">
      <div className="start-page-container">
        {/* Header */}
        <section className="start-page-header">
          <h1 className="text-display-xl">TestGap Finder</h1>
          <p className="text-body-lg start-page-description">
            Discover gaps in the test coverage of your repository. Select a project and
            configure your scan.
          </p>
        </section>

        {/* Notice panel */}
        <div className="notice-panel">
          <h2 className="text-body-md notice-panel-heading">Current Capabilities</h2>
          <ul className="text-body-sm">
            <li>Baseline coverage scanning</li>
            <li>Target ranking</li>
            <li>Draft test generation</li>
            <li>
              <em>Test execution, repair, and mutation verification coming soon.</em>
            </li>
          </ul>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="start-page-form">
          {/* Two-option segmented switch */}
          <div className="form-group mode-switch-group">
            <SegmentedSwitch
              id="start-mode-switch"
              options={MODE_OPTIONS}
              value={mode}
              onChange={handleModeChange}
            />
          </div>

          {/* Mode 1: GITHUB REPO panel */}
          <div
            role="tabpanel"
            id="start-mode-switch-panel-repo"
            aria-labelledby="start-mode-switch-tab-repo"
            hidden={mode !== "repo"}
            className="tabpanel-content"
          >
            {mode === "repo" && (
              <RepoInput
                value={repoUrl}
                onChange={setRepoUrl}
                parsed={repoParsed}
                onParsedChange={setRepoParsed}
                onSubmit={handleSubmit}
                disabled={isSubmitting}
              />
            )}
          </div>

          {/* Mode 2: DEMO PROJECTS panel */}
          <div
            role="tabpanel"
            id="start-mode-switch-panel-demo"
            aria-labelledby="start-mode-switch-tab-demo"
            hidden={mode !== "demo"}
            className="tabpanel-content"
          >
            {mode === "demo" && (
              <div className="demo-projects-wrapper">
                {/* Loading state */}
                {projectsLoading && (
                  <div className="projects-section">
                    <h2 className="text-heading-lg projects-heading">Projects</h2>
                    <div className="projects-grid">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="project-card-skeleton" />
                      ))}
                    </div>
                  </div>
                )}

                {/* Slow backend message */}
                {slowBackend && projectsLoading && (
                  <div className="slow-backend-message text-body-sm">
                    The backend may be waking up. This can take up to a minute.
                  </div>
                )}

                {/* Error state */}
                {projectsError && !projectsLoading && (
                  <div className="error-section">
                    <p className="text-body-sm error-message">{projectsError}</p>
                    <button
                      type="button"
                      onClick={fetchProjects}
                      className="retry-button"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {/* Empty state */}
                {!projectsLoading && !projectsError && projects.length === 0 && (
                  <div className="empty-section">
                    <p className="text-body-sm">
                      No projects are configured. The backend needs a local or demo repository.
                    </p>
                  </div>
                )}

                {/* Success state - projects list */}
                {!projectsLoading && !projectsError && projects.length > 0 && (
                  <div className="projects-section">
                    <h2 className="text-heading-lg projects-heading">Projects</h2>
                    <div className="projects-grid">
                      {projects.map((project) => (
                        <ProjectCard
                          key={project.id}
                          project={project}
                          isSelected={selectedProjectId === project.id}
                          onSelect={setSelectedProjectId}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Shared scan configuration: Target Limit */}
          <div className="form-group">
            <label htmlFor="target-limit" className="text-body-md form-label">
              Target Limit
            </label>
            <input
              id="target-limit"
              type="number"
              min={TARGET_LIMIT_MIN}
              max={TARGET_LIMIT_MAX}
              value={targetLimit}
              onChange={handleTargetLimitChange}
              className="form-input"
              aria-describedby={targetError ? "target-error" : undefined}
            />
            {targetError && (
              <p id="target-error" className="text-body-sm form-error">
                {targetError}
              </p>
            )}
          </div>

          {/* Shared scan configuration: Repair Limit */}
          <div className="form-group">
            <label htmlFor="repair-limit" className="text-body-md form-label">
              Repair Limit
            </label>
            <input
              id="repair-limit"
              type="number"
              min={REPAIR_LIMIT_MIN}
              max={REPAIR_LIMIT_MAX}
              value={repairLimit}
              onChange={handleRepairLimitChange}
              className="form-input"
              aria-describedby={repairError ? "repair-error" : undefined}
            />
            {repairError && (
              <p id="repair-error" className="text-body-sm form-error">
                {repairError}
              </p>
            )}
          </div>

          {/* Shared scan configuration: Verify Mutations toggle */}
          <div className="form-group form-group-toggle">
            <label htmlFor="verify-mutations" className="text-body-md form-label">
              <input
                id="verify-mutations"
                type="checkbox"
                checked={verifyMutations}
                onChange={(e) => setVerifyMutations(e.target.checked)}
                className="form-checkbox"
              />
              <span>Verify Mutations</span>
            </label>
            <p className="text-body-sm form-helper-text">
              The backend does not run mutation verification yet.
            </p>
          </div>

          {/* Submit error */}
          {submitError && (
            <div className="submit-error">
              <p className="text-body-sm error-message">{submitError}</p>
              <button
                type="button"
                onClick={handleSubmit}
                className="try-again-button"
              >
                Try again
              </button>
            </div>
          )}

          {/* Submit button */}
          <div className="form-actions">
            <button
              type="submit"
              disabled={!canStartScan}
              className="start-scan-button"
              aria-live="polite"
            >
              Start Scan
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
