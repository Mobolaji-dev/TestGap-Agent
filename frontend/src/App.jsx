import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import AppShell from "./components/layout/AppShell";
import StartPage from "./pages/StartPage";
import RunPage from "./pages/RunPage";
import ResultsPage from "./pages/ResultsPage";
import NotFoundPage from "./pages/NotFoundPage";
import "./styles/tokens.css";
import "./App.css";

/**
 * Main App component with routing and error boundary
 */
export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<StartPage />} />
            <Route path="/run/:runId" element={<RunPage />} />
            <Route path="/results/:runId" element={<ResultsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}
