import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { HiMenu, HiX } from "react-icons/hi";
import "./Sidebar.css";

/**
 * Sidebar with navigation and hamburger menu toggle on mobile
 */
export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const sidebarRef = useRef(null);

  const isActive = location.pathname === "/";

  // Extract runId from URL (e.g., /run/:runId or /results/:runId)
  const runIdMatch = location.pathname.match(/\/(?:run|results)\/([^/]+)/);
  const currentRunId = runIdMatch ? runIdMatch[1] : null;
  const isRunActive = Boolean(currentRunId && location.pathname === `/run/${currentRunId}`);
  const isResultsActive = Boolean(currentRunId && location.pathname === `/results/${currentRunId}`);

  // Close drawer on item click
  const handleNavClick = (path) => {
    navigate(path);
    setIsOpen(false);
  };

  // Close drawer on Escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen]);

  // Close drawer on backdrop click
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      setIsOpen(false);
    }
  };

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="sidebar">
        <div className="sidebar-content">
          {/* Wordmark */}
          <div className="sidebar-brand">
            <span className="text-caption-lg">TestGap</span>
          </div>

          {/* Navigation section */}
          <div className="sidebar-nav">
            <span className="text-caption-lg sidebar-nav-label">Navigation</span>
            <nav>
              <button
                className={`nav-item ${isActive ? "nav-item-active" : ""}`}
                onClick={() => handleNavClick("/")}
                aria-current={isActive ? "page" : undefined}
              >
                New scan
              </button>
              {currentRunId && (
                <>
                  <button
                    className={`nav-item ${isRunActive ? "nav-item-active" : ""}`}
                    onClick={() => handleNavClick(`/run/${currentRunId}`)}
                    aria-current={isRunActive ? "page" : undefined}
                    title={`Run ${currentRunId}`}
                  >
                    Current run
                  </button>
                  <button
                    className={`nav-item ${isResultsActive ? "nav-item-active" : ""}`}
                    onClick={() => handleNavClick(`/results/${currentRunId}`)}
                    aria-current={isResultsActive ? "page" : undefined}
                    title={`Results ${currentRunId}`}
                  >
                    Results
                  </button>
                </>
              )}
            </nav>
          </div>
        </div>
      </aside>

      {/* Mobile hamburger button */}
      <button
        className="hamburger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? "Close menu" : "Open menu"}
        aria-expanded={isOpen}
      >
        {isOpen ? <HiX size={24} /> : <HiMenu size={24} />}
      </button>

      {/* Mobile drawer overlay backdrop */}
      {isOpen && (
        <div
          className="drawer-backdrop"
          onClick={handleBackdropClick}
          role="presentation"
        >
          {/* Mobile drawer */}
          <div
            className="drawer"
            ref={sidebarRef}
            role="navigation"
            aria-label="Mobile navigation"
          >
            {/* Wordmark */}
            <div className="sidebar-brand">
              <span className="text-caption-lg">TestGap</span>
            </div>

            {/* Navigation section */}
            <div className="sidebar-nav">
              <span className="text-caption-lg sidebar-nav-label">Navigation</span>
              <nav>
                <button
                  className={`nav-item ${isActive ? "nav-item-active" : ""}`}
                  onClick={() => handleNavClick("/")}
                  aria-current={isActive ? "page" : undefined}
                >
                  New scan
                </button>
                {currentRunId && (
                  <>
                    <button
                      className={`nav-item ${isRunActive ? "nav-item-active" : ""}`}
                      onClick={() => handleNavClick(`/run/${currentRunId}`)}
                      aria-current={isRunActive ? "page" : undefined}
                      title={`Run ${currentRunId}`}
                    >
                      Current run
                    </button>
                    <button
                      className={`nav-item ${isResultsActive ? "nav-item-active" : ""}`}
                      onClick={() => handleNavClick(`/results/${currentRunId}`)}
                      aria-current={isResultsActive ? "page" : undefined}
                      title={`Results ${currentRunId}`}
                    >
                      Results
                    </button>
                  </>
                )}
              </nav>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
