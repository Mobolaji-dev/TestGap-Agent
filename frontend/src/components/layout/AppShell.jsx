import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import "./AppShell.css";

/**
 * Main app shell with two-column layout (sidebar + content)
 */
export default function AppShell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
