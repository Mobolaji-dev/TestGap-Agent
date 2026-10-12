import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import AppShell from "./components/layout/AppShell";
import PublicLayout from "./components/layout/PublicLayout";
import LandingPage from "./pages/LandingPage";
import DocsPage from "./pages/DocsPage";
import StartPage from "./pages/StartPage";
import RunPage from "./pages/RunPage";
import ResultsPage from "./pages/ResultsPage";
import NotFoundPage from "./pages/NotFoundPage";
import "./styles/tokens.css";
import "./App.css";

export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/docs" element={<DocsPage />} />
          </Route>
          <Route element={<AppShell />}>
            <Route path="/app" element={<StartPage />} />
            <Route path="/run/:runId" element={<RunPage />} />
            <Route path="/results/:runId" element={<ResultsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}
