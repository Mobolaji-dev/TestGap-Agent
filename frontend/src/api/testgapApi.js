const BACKEND_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Start a test scan run from a GitHub repository URL.
 * Response fields:
 * - run_id: string
 * - status: string
 * - (plus full RunResponse fields: project_id, current_step, targets, etc.)
 */
export async function createRunFromRepo(
  repositoryUrl,
  targetLimit,
  repairLimit,
  verifyMutations
) {
  // POST to /api/runs with repository_url and options
  const response = await fetch(`${BACKEND_URL}/api/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      repository_url: repositoryUrl,
      target_limit: targetLimit,
      repair_limit: repairLimit,
      verify_mutations: verifyMutations,
    }),
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

/**
 * Start a test scan run from a demo project ID.
 * Response fields:
 * - run_id: string
 * - status: string
 * - (plus full RunResponse fields: project_id, current_step, targets, etc.)
 */
export async function createRunFromProject(
  projectId,
  targetLimit,
  repairLimit,
  verifyMutations
) {
  // POST to /api/runs with project_id and options
  const response = await fetch(`${BACKEND_URL}/api/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      project_id: projectId,
      target_limit: targetLimit,
      repair_limit: repairLimit,
      verify_mutations: verifyMutations,
    }),
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

/**
 * Fetch list of configured local/demo projects.
 * Response fields for each project item in data.projects array:
 * - id: string, name: string, language: string, test_framework: string | null
 * - path_label: string, ready: boolean, warning: string | null
 */
export async function listProjects(signal) {
  // GET /api/projects
  const response = await fetch(`${BACKEND_URL}/api/projects`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  const data = await response.json();
  return data.projects;
}

/**
 * Fetch canonical state and results for a specific run.
 * Response fields:
 * - run_id, project_id, status, current_step, created_at, updated_at
 * - events, targets, baseline, candidate_tests, metrics, trace_url, warnings
 */
export async function getRun(runId, signal) {
  // GET /api/runs/{run_id}
  const response = await fetch(`${BACKEND_URL}/api/runs/${runId}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

/**
 * Request cancellation of a queued or running scan.
 * Response fields:
 * - run_id: string, status: string ("cancelled")
 * - (plus full RunResponse fields)
 */
export async function cancelRun(runId) {
  // POST /api/runs/{run_id}/cancel
  const response = await fetch(`${BACKEND_URL}/api/runs/${runId}/cancel`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

/**
 * Fetch generated test-only unified diff for a run.
 * Response fields:
 * - run_id: string
 * - diff: string
 */
export async function getDiff(runId, signal) {
  // GET /api/runs/{run_id}/diff
  const response = await fetch(`${BACKEND_URL}/api/runs/${runId}/diff`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

/**
 * Download generated test-only patch as a binary Blob.
 * Response fields:
 * - Binary Blob of text/x-diff patch content
 */
export async function getPatch(runId) {
  // GET /api/runs/{run_id}/patch
  const response = await fetch(`${BACKEND_URL}/api/runs/${runId}/patch`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.blob();
}

/**
 * Liveness check for backend service health.
 * Response fields:
 * - status: string (e.g. "ok")
 */
export async function getHealth(signal) {
  // GET /health
  const response = await fetch(`${BACKEND_URL}/health`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((item) => item.msg).join(", ");
      }
    } catch (parseError) {
      // no JSON body, keep the default message
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

/**
 * Build the Server-Sent Events (SSE) streaming URL for run events.
 * Returns the SSE URL string:
 * - URL string: ${BACKEND_URL}/api/runs/${runId}/events?after=${afterId || 0}
 */
export function getRunEventsUrl(runId, afterId) {
  return `${BACKEND_URL}/api/runs/${runId}/events?after=${afterId || 0}`;
}
