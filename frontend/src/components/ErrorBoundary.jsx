import { Component } from "react";
import "./ErrorBoundary.css";

/**
 * Error boundary to catch render errors and display a user-friendly message
 * Logs errors to console for debugging
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console for debugging
    console.error("Render error caught by ErrorBoundary:");
    console.error(error);
    console.error("Error Info:", errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-container">
            <h1 className="text-display-xl error-boundary-heading">
              Something went wrong
            </h1>
            <p className="text-body-lg error-boundary-message">
              An unexpected error occurred while rendering the page. Please reload
              and try again.
            </p>
            {import.meta.env.MODE === "development" && (
              <details className="error-boundary-details">
                <summary className="text-body-sm">Error details (development only)</summary>
                <pre className="error-boundary-stack">
                  {this.state.error?.toString()}
                </pre>
              </details>
            )}
            <button
              type="button"
              onClick={this.handleReload}
              className="error-boundary-reload-button"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
