import { Link } from "react-router-dom";
import { HiArrowRight, HiArrowUpRight, HiCheck, HiCodeBracket, HiCommandLine, HiMagnifyingGlass, HiShieldCheck, HiSparkles } from "react-icons/hi2";
import "./LandingPage.css";

const steps = [
  { number: "01", title: "Connect a repository", body: "Paste a public GitHub repository URL. TestGap clones it into an isolated temporary workspace." },
  { number: "02", title: "Find the gaps", body: "Run the existing test suite with coverage, then rank Python files that have the most uncovered code." },
  { number: "03", title: "Review a test patch", body: "Draft a focused test for a high-priority gap, run it against the repository suite, and review the patch before applying it." },
];

const capabilities = [
  { icon: HiMagnifyingGlass, title: "Coverage-led priorities", body: "Use a passing baseline and line coverage to direct attention to under-tested Python code." },
  { icon: HiSparkles, title: "Focused test drafts", body: "Generate a candidate for a ranked gap, with the target and reasoning visible in the run." },
  { icon: HiShieldCheck, title: "Check before you apply", body: "Candidate tests are run in a disposable copy. Passing test-only patches are available for review and download." },
];

export default function LandingPage() {
  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> PYTHON TEST COVERAGE, MADE ACTIONABLE</div>
          <h1>Ship with confidence.<br /><span>Close the test gaps.</span></h1>
          <p className="hero-lede">TestGap Finder analyzes your repository, pinpoints under-tested code, and drafts tests you can verify and review before they touch your project.</p>
          <div className="hero-actions">
            <Link className="button-primary" to="/app">Scan a repository <HiArrowRight aria-hidden="true" /></Link>
            <Link className="button-secondary" to="/docs">Read the docs</Link>
          </div>
          <div className="hero-note"><HiShieldCheck aria-hidden="true" /> Your source checkout stays untouched. Patches are yours to review.</div>
        </div>
        <div className="hero-visual" aria-label="Illustration of coverage analysis and test generation">
          <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
          <div className="terminal-card">
            <div className="terminal-top"><div><i /><i /><i /></div><span>testgap · analysis</span><span className="terminal-live">● LIVE</span></div>
            <div className="terminal-content">
              <div className="terminal-line muted">$ testgap scan ./my-project</div>
              <div className="terminal-step"><span className="step-check"><HiCheck /></span><div><strong>Baseline tests</strong><small>Passed · 78% line coverage</small></div><span className="step-time">12.4s</span></div>
              <div className="terminal-step"><span className="step-check"><HiCheck /></span><div><strong>Rank test gaps</strong><small>3 under-tested files found</small></div><span className="step-time">2.1s</span></div>
              <div className="terminal-step step-active"><span className="step-spark"><HiSparkles /></span><div><strong>Draft candidate</strong><small>tests/test_billing.py</small></div><span className="step-pulse" /></div>
              <div className="coverage-row"><span>Coverage before</span><b>78%</b><div className="coverage-track"><i /></div></div>
              <div className="terminal-result"><HiCheck /> Candidate passed the existing suite <span>View patch ↗</span></div>
            </div>
          </div>
          <div className="floating-chip chip-coverage"><span>LINE COVERAGE</span><strong>+ 8.4%</strong><i>after verified tests</i></div>
          <div className="floating-chip chip-files"><HiCodeBracket /><span>3 target files</span></div>
        </div>
        <a className="hero-scroll" href="#how-it-works">SCROLL TO EXPLORE <span>↓</span></a>
      </section>

      <section className="trust-strip" aria-label="Product workflow summary">
        <span>BUILT FOR THE LOOP BETWEEN</span><b>existing tests</b><i>→</i><b>coverage gaps</b><i>→</i><b>reviewable test patches</b>
      </section>

      <section className="landing-section process-section" id="how-it-works">
        <div className="section-heading"><div className="eyebrow">A CLEAR PATH FROM SIGNAL TO TEST</div><h2>Make the next test<br /><span>the right test.</span></h2><p>Move from a coverage report to a verified, reviewable test patch in one guided workflow.</p></div>
        <div className="process-grid">{steps.map((step) => <article className="process-card" key={step.number}><span className="process-number">{step.number}</span><div className="process-rule" /><h3>{step.title}</h3><p>{step.body}</p></article>)}</div>
      </section>

      <section className="landing-section capabilities-section">
        <div className="capabilities-head"><div><div className="eyebrow">BUILT AROUND TRUST</div><h2>Useful signal.<br /><span>Human control.</span></h2></div><p>TestGap automates the repetitive analysis while keeping generated code transparent and optional.</p></div>
        <div className="capabilities-grid">{capabilities.map(({ icon: Icon, title, body }) => <article className="capability-card" key={title}><div className="capability-icon"><Icon aria-hidden="true" /></div><h3>{title}</h3><p>{body}</p></article>)}</div>
      </section>

      <section className="landing-section boundary-section">
        <div className="boundary-card"><div className="boundary-icon"><HiCommandLine /></div><div><div className="eyebrow">CURRENT SCOPE</div><h2>Focused on Python repositories.</h2><p>TestGap supports public GitHub repositories, pytest-based baselines, and test-only candidate patches. Generated tests are verified against the existing suite; mutation verification and automatic source edits are not part of the current workflow.</p><Link to="/docs#scope">See supported behavior <HiArrowUpRight /></Link></div></div>
      </section>

      <section className="landing-cta"><div className="eyebrow">READY WHEN YOU ARE</div><h2>Find your next high-value test.</h2><p>Start with a public repository and see what your test suite is missing.</p><Link className="button-primary" to="/app">Start a scan <HiArrowRight /></Link></section>
    </div>
  );
}
