import { NavLink, Route, Routes, matchPath, useLocation } from "react-router-dom";

import { ReviewRunDetailPage } from "./pages/ReviewRunDetailPage";
import { ReviewRunListPage } from "./pages/ReviewRunListPage";

export function App() {
  const location = useLocation();
  const detailMatch = matchPath("/runs/:reviewRunId", location.pathname);
  const inDetailPage = detailMatch !== null;

  return (
    <div className="dashboard">
      <aside className="dashboard__sidebar">
        <div className="brand-card">
          <div className="brand-card__mark">PR</div>
          <div>
            <p className="eyebrow">Local Review Console</p>
            <h1>GitHub PR Auto Review</h1>
          </div>
        </div>

        <nav className="sidebar__nav" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => `sidebar__nav-link${isActive ? " is-active" : ""}`}>
            Dashboard
          </NavLink>
          <NavLink
            to={inDetailPage ? location.pathname : "/"}
            className={({ isActive }) => `sidebar__nav-link${isActive && inDetailPage ? " is-active" : ""}`}
          >
            Run Detail
          </NavLink>
        </nav>

        <section className="sidebar__summary panel panel--dark">
          <p className="eyebrow">Workspace</p>
          <h2>Operational Focus</h2>
          <p>
            Review runs, diff snapshots, agent traces, and replay actions are grouped into a single dashboard
            surface.
          </p>
          <div className="sidebar__tags">
            <span className="sidebar__tag">Local API</span>
            <span className="sidebar__tag">Manual replay</span>
            <span className="sidebar__tag">Trace audit</span>
          </div>
        </section>
      </aside>

      <div className="dashboard__workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{inDetailPage ? "Execution Breakdown" : "Overview Dashboard"}</p>
            <h2>{inDetailPage ? "Review Run Detail" : "Review Activity"}</h2>
          </div>
          <div className="topbar__chips">
            <span className="topbar__chip">Material dashboard language</span>
            <span className="topbar__chip">{inDetailPage ? "Route: /runs/:id" : "Route: /"}</span>
          </div>
        </header>

        <main className="dashboard__content">
          <Routes>
            <Route path="/" element={<ReviewRunListPage />} />
            <Route path="/runs/:reviewRunId" element={<ReviewRunDetailPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
