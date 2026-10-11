import { useState, useEffect, useRef, useCallback } from "react";
import { getRun, getRunEventsUrl } from "../api/testgapApi";

const TERMINAL_STATUSES = new Set([
  "completed",
  "completed_with_warnings",
  "failed",
  "cancelled",
]);

const TERMINAL_EVENT_TYPES = new Set([
  "run.completed",
  "run.failed",
  "run.cancelled",
]);

const SSE_EVENT_TYPES = [
  "run.queued",
  "run.started",
  "step.started",
  "step.completed",
  "step.failed",
  "warning",
  "run.completed",
  "run.failed",
  "run.cancelled",
];

export function isTerminalStatus(status) {
  return TERMINAL_STATUSES.has(status);
}

export function isTerminalEvent(type) {
  return TERMINAL_EVENT_TYPES.has(type);
}

function getEventId(evt) {
  if (!evt) return null;
  if (evt.event_id != null) return Number(evt.event_id);
  if (evt.id != null) return Number(evt.id);
  return null;
}

function parseEvent(data) {
  if (typeof data !== "string") return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

/**
 * Custom hook for managing a run's real-time event stream.
 *
 * @param {string} runId - The run ID to stream events for
 * @returns {{
 *   run: Object | null,
 *   events: Array,
 *   connection: "connecting" | "live" | "reconnecting" | "polling" | "closed",
 *   error: string | null,
 *   errorStatus: number | null,
 *   refresh: () => Promise<Object | null>
 * }}
 */
export default function useRunStream(runId) {
  const [prevRunId, setPrevRunId] = useState(runId);
  const [run, setRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState(null);
  const [errorStatus, setErrorStatus] = useState(null);

  // If runId changes, reset state during render (standard React pattern)
  if (prevRunId !== runId) {
    setPrevRunId(runId);
    setRun(null);
    setEvents([]);
    setConnection("connecting");
    setError(null);
    setErrorStatus(null);
  }

  const eventSourceRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const reconcileIntervalRef = useRef(null);
  const eventIdsRef = useRef(new Set());
  const lastEventIdRef = useRef(null);
  const isMountedRef = useRef(true);
  const runRef = useRef(null);
  const connectionRef = useRef("connecting");
  const openStreamRef = useRef(null);

  // Keep connectionRef in sync with state
  useEffect(() => {
    connectionRef.current = connection;
  }, [connection]);

  // Keep runRef in sync with state
  useEffect(() => {
    runRef.current = run;
  }, [run]);

  /**
   * Merge and deduplicate incoming events by event_id, keeping them sorted.
   */
  const mergeEvents = useCallback((incomingEvents) => {
    if (!Array.isArray(incomingEvents) || incomingEvents.length === 0) return;

    setEvents((prev) => {
      let hasNew = false;
      const next = [...prev];

      for (const evt of incomingEvents) {
        if (!evt) continue;
        const id = getEventId(evt);
        if (id != null) {
          if (!eventIdsRef.current.has(id)) {
            eventIdsRef.current.add(id);
            if (lastEventIdRef.current == null || id > lastEventIdRef.current) {
              lastEventIdRef.current = id;
            }
            next.push(evt);
            hasNew = true;
          }
        } else {
          next.push(evt);
          hasNew = true;
        }
      }

      if (!hasNew) return prev;

      next.sort((a, b) => {
        const idA = getEventId(a) ?? 0;
        const idB = getEventId(b) ?? 0;
        return idA - idB;
      });

      return next;
    });
  }, []);

  const closeStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const stopReconcile = useCallback(() => {
    if (reconcileIntervalRef.current) {
      clearInterval(reconcileIntervalRef.current);
      reconcileIntervalRef.current = null;
    }
  }, []);

  /**
   * Fetch canonical final state from the API when terminal.
   */
  const fetchCanonical = useCallback(async () => {
    try {
      const data = await getRun(runId);
      if (!isMountedRef.current) return;
      setRun(data);
      runRef.current = data;
      if (Array.isArray(data.events)) {
        mergeEvents(data.events);
      }
      if (isTerminalStatus(data.status)) {
        closeStream();
        stopPolling();
        stopReconcile();
        setConnection("closed");
      }
    } catch {
      // Keep existing data on screen
    }
  }, [runId, closeStream, stopPolling, stopReconcile, mergeEvents]);

  /**
   * Start polling every 3 seconds after 3 failed SSE attempts.
   */
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return;

    const poll = async () => {
      if (!isMountedRef.current) return;
      try {
        const data = await getRun(runId);
        if (!isMountedRef.current) return;
        setRun(data);
        runRef.current = data;
        if (Array.isArray(data.events)) {
          mergeEvents(data.events);
        }

        if (isTerminalStatus(data.status)) {
          stopPolling();
          closeStream();
          stopReconcile();
          setConnection("closed");
        } else {
          // If network returned and polling succeeded while run is still active,
          // recover back to the live stream
          reconnectAttemptsRef.current = 0;
          stopPolling();
          openStreamRef.current?.();
        }
      } catch {
        // Network still down; stay in polling mode and keep run data on screen
      }
    };

    pollingIntervalRef.current = setInterval(poll, 3000);
  }, [runId, mergeEvents, stopPolling, closeStream, stopReconcile]);

  /**
   * Open the EventSource connection and wire all event handlers.
   */
  const openStream = useCallback(() => {
    if (!isMountedRef.current) return;

    // Terminal check
    if (runRef.current && isTerminalStatus(runRef.current.status)) {
      closeStream();
      stopPolling();
      stopReconcile();
      setConnection("closed");
      return;
    }

    closeStream();
    clearReconnectTimer();
    stopPolling();

    const nextConn = reconnectAttemptsRef.current > 0 ? "reconnecting" : "connecting";
    setConnection(nextConn);

    const url = getRunEventsUrl(runId, lastEventIdRef.current);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      if (!isMountedRef.current || eventSourceRef.current !== es) return;
      setConnection("live");
      reconnectAttemptsRef.current = 0;
    };

    const handleEventMessage = (e) => {
      if (!isMountedRef.current || eventSourceRef.current !== es) return;
      const evt = parseEvent(e.data);
      if (!evt) return;

      mergeEvents([evt]);

      if (isTerminalEvent(evt.type) || isTerminalStatus(evt.status)) {
        closeStream();
        stopPolling();
        stopReconcile();
        setConnection("closed");
        fetchCanonical();
      }
    };

    // Backend emits named SSE events: register addEventListener for each known type
    SSE_EVENT_TYPES.forEach((type) => {
      es.addEventListener(type, handleEventMessage);
    });

    // Also handle unnamed events
    es.onmessage = handleEventMessage;

    es.onerror = () => {
      if (!isMountedRef.current || eventSourceRef.current !== es) return;
      closeStream();

      reconnectAttemptsRef.current += 1;
      if (reconnectAttemptsRef.current <= 3) {
        // Backoff: 1s, 2s, 4s
        const backoffMs = Math.pow(2, reconnectAttemptsRef.current - 1) * 1000;
        setConnection("reconnecting");
        reconnectTimeoutRef.current = setTimeout(() => {
          if (!isMountedRef.current) return;
          openStreamRef.current?.();
        }, backoffMs);
      } else {
        // Fall back to polling every 3 seconds
        setConnection("polling");
        startPolling();
      }
    };
  }, [
    runId,
    closeStream,
    clearReconnectTimer,
    stopPolling,
    stopReconcile,
    mergeEvents,
    fetchCanonical,
    startPolling,
  ]);

  useEffect(() => {
    openStreamRef.current = openStream;
  }, [openStream]);

  /**
   * Reconcile safety net: fetch getRun every 5s while active to catch any events.
   */
  const startReconcile = useCallback(() => {
    if (reconcileIntervalRef.current) return;

    reconcileIntervalRef.current = setInterval(async () => {
      if (!isMountedRef.current) return;
      if (connectionRef.current === "polling" || connectionRef.current === "closed") {
        return;
      }
      try {
        const data = await getRun(runId);
        if (!isMountedRef.current) return;
        setRun(data);
        runRef.current = data;
        if (Array.isArray(data.events)) {
          mergeEvents(data.events);
        }
        if (isTerminalStatus(data.status)) {
          closeStream();
          stopPolling();
          stopReconcile();
          setConnection("closed");
        }
      } catch {
        // Reconcile is non-blocking safety net
      }
    }, 5000);
  }, [runId, mergeEvents, closeStream, stopPolling, stopReconcile]);

  /**
   * Manual refresh function.
   */
  const refresh = useCallback(async () => {
    try {
      const data = await getRun(runId);
      if (!isMountedRef.current) return data;
      setRun(data);
      runRef.current = data;
      setError(null);
      setErrorStatus(null);
      if (Array.isArray(data.events)) {
        mergeEvents(data.events);
      }
      if (isTerminalStatus(data.status)) {
        closeStream();
        stopPolling();
        stopReconcile();
        setConnection("closed");
      }
      return data;
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message);
        setErrorStatus(err.status ?? null);
      }
      return null;
    }
  }, [runId, mergeEvents, closeStream, stopPolling, stopReconcile]);

  /**
   * Main lifecycle effect on mount or runId change.
   */
  useEffect(() => {
    isMountedRef.current = true;
    const abortController = new AbortController();

    eventIdsRef.current = new Set();
    lastEventIdRef.current = null;
    reconnectAttemptsRef.current = 0;

    const hydrate = async () => {
      try {
        const data = await getRun(runId, abortController.signal);
        if (!isMountedRef.current) return;
        setRun(data);
        runRef.current = data;
        setError(null);
        setErrorStatus(null);

        // Seed events from the initial run state
        if (Array.isArray(data.events)) {
          mergeEvents(data.events);
        }

        // If hydrated status is already terminal, do NOT open a stream.
        // Show the stored events and outcome only.
        if (isTerminalStatus(data.status)) {
          setConnection("closed");
          return;
        }

        // If queued or running, open stream and start 5s safety net reconciliation
        openStreamRef.current?.();
        startReconcile();
      } catch (err) {
        if (!isMountedRef.current || err.name === "AbortError") return;
        const msg = err.message || "";
        setError(msg);
        setErrorStatus(err.status ?? (msg.toLowerCase().includes("not found") ? 404 : null));
        setConnection("closed");
      }
    };

    hydrate();

    // Online event listener to recover when network is restored
    const handleOnline = () => {
      if (!isMountedRef.current) return;
      if (runRef.current && !isTerminalStatus(runRef.current.status)) {
        reconnectAttemptsRef.current = 0;
        openStreamRef.current?.();
      }
    };

    window.addEventListener("online", handleOnline);

    return () => {
      isMountedRef.current = false;
      abortController.abort();
      window.removeEventListener("online", handleOnline);
      closeStream();
      clearReconnectTimer();
      stopPolling();
      stopReconcile();
    };
  }, [runId, mergeEvents, startReconcile, closeStream, clearReconnectTimer, stopPolling, stopReconcile]);

  return {
    run,
    events,
    connection,
    error,
    errorStatus,
    refresh,
  };
}
