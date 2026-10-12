import { Link, NavLink, Outlet } from "react-router-dom";
import { HiArrowUpRight } from "react-icons/hi2";
import "./PublicLayout.css";

export default function PublicLayout() {
  return (
    <div className="public-site">
      <header className="public-header">
        <Link className="public-brand" to="/" aria-label="TestGap home">
          <img src="/testgap-logo.png" alt="" />
          <span>TestGap<span className="brand-period">.</span></span>
        </Link>
        <nav className="public-nav" aria-label="Main navigation">
          <a href="/#how-it-works">How it works</a>
          <NavLink to="/docs">Docs</NavLink>
          <a href="https://github.com/techbyFEMI/TestGap-Agent" target="_blank" rel="noreferrer">
            GitHub <HiArrowUpRight aria-hidden="true" />
          </a>
          <Link className="public-nav-cta" to="/app">Open scanner <span aria-hidden="true">→</span></Link>
        </nav>
      </header>
      <main className="public-main"><Outlet /></main>
      <footer className="public-footer">
        <Link className="public-brand" to="/">
          <img src="/testgap-logo.png" alt="" />
          <span>TestGap<span className="brand-period">.</span></span>
        </Link>
        <span>Find the gaps. Draft the tests. Review every patch.</span>
        <div><Link to="/docs">Documentation</Link><Link to="/app">Start a scan</Link></div>
      </footer>
    </div>
  );
}
