import { useState, useEffect, useCallback, useRef } from "react";
import { getRun } from "../api/testgapApi";

/**
 * Hook to fetch run details for the Results view.
 *
 * @param {string} runId - The run ID to fetch
 * @returns {{
 *   run: Object | null,
 *   loading: boolean,
 *   error: string | null,
 *   errorStatus: number | null,
 *   refresh: () => Promise<Object | null>
 * }}
 */
export default function useRun(runId) {
  const [prevRunId, setPrevRunId] = useState(runId);
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [errorStatus, setErrorStatus] = useState(null);

  // Reset state during render if runId changes (standard React pattern)
  if (prevRunId !== runId) {
    setPrevRunId(runId);
    setRun(null);
    setLoading(true);
    setError(null);
    setErrorStatus(null);
  }

  const isMountedRef = useRef(true);

  // Initial fetch inside the effect using a local async function
  // so the linter doesn't flag setState-in-effect.
  useEffect(() => {
    isMountedRef.current = true;
    const abortController = new AbortController();

    const hydrate = async () => {
      try {
        const data = await getRun(runId, abortController.signal);
        if (!isMountedRef.current) return;
        setRun(data);
        setError(null);
        setErrorStatus(null);
      } catch (err) {
        if (!isMountedRef.current || err.name === "AbortError") return;
        const msg = err.message || "";
        setError(msg);
        setErrorStatus(
          err.status ??
            (msg.toLowerCase().includes("not found") ? 404 : null)
        );
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    };

    hydrate();

    return () => {
      isMountedRef.current = false;
      abortController.abort();
    };
  }, [runId]);

  // Manual refresh (e.g. Retry button)
  const refresh = useCallback(async () => {
    isMountedRef.current = true;
    setLoading(true);
    setError(null);
    setErrorStatus(null);
    try {
      const data = await getRun(runId);
      if (!isMountedRef.current) return null;
      setRun(data);
      setLoading(false);
      return data;
    } catch (err) {
      if (!isMountedRef.current || err.name === "AbortError") return null;
      const msg = err.message || "";
      setError(msg);
      setErrorStatus(
        err.status ??
          (msg.toLowerCase().includes("not found") ? 404 : null)
      );
      setLoading(false);
      return null;
    }
  }, [runId]);

  return {
    run,
    loading,
    error,
    errorStatus,
    refresh,
  };
}
