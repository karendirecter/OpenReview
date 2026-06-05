import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatDateTime } from "../lib/format";
import { fetchReviewRuns, type ReviewRunItem } from "../lib/api";

export function ReviewRunListPage() {
  const [runs, setRuns] = useState<ReviewRunItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void loadRuns();
  }, []);

  async function loadRuns() {
    setLoading(true);
    try {
      const items = await fetchReviewRuns();
      setRuns(items);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }

  const sortedRuns = [...runs].sort((left, right) => {
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });
  const completedCount = runs.filter((run) => /(success|complete|completed|done)/i.test(run.status)).length;
  const activeCount = runs.filter((run) => /(queued|running|pending|processing|progress)/i.test(run.status)).length;
  const modelCount = new Set(runs.map((run) => run.selected_model)).size;
  const latestRun = sortedRuns[0];
  const latestTime = latestRun ? formatDateTime(latestRun.created_at) : "No history yet";

  return (
    <section className="page-stack">
      <section className="hero-card panel">
        <div className="hero-card__content">
          <p className="eyebrow">Control center</p>
          <h3>Review operations at a glance</h3>
          <p>
            Track persisted review runs, identify active replays, and jump directly into the diff and finding
            breakdown for any PR execution.
          </p>
          <div className="hero-card__actions">
            <button type="button" className="button" onClick={() => void loadRuns()} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh data"}
            </button>
            {latestRun ? (
              <Link className="button button--ghost" to={`/runs/${latestRun.review_run_id}`}>
                Open latest run
              </Link>
            ) : null}
          </div>
        </div>
        <div className="hero-card__highlight">
          <span className="hero-card__label">Latest update</span>
          <strong>{latestTime}</strong>
          <p>{latestRun ? `${latestRun.repo_owner}/${latestRun.repo_name}#${latestRun.pr_number}` : "Awaiting first review run."}</p>
        </div>
      </section>

      <section className="metric-grid" aria-label="Review metrics">
        <MetricCard accent="teal" icon="01" label="Total runs" value={String(runs.length)} detail="Persisted review executions" />
        <MetricCard accent="amber" icon="02" label="Active runs" value={String(activeCount)} detail="Queued or in-progress work" />
        <MetricCard
          accent="rose"
          icon="03"
          label="Completed"
          value={String(completedCount)}
          detail="Runs that produced a terminal result"
        />
        <MetricCard accent="blue" icon="04" label="Models used" value={String(modelCount)} detail="Distinct models across history" />
      </section>

      <section className="content-grid">
        <section className="panel">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Run inventory</p>
              <h2>Review History</h2>
            </div>
            <span className="panel__meta">{runs.length} entries</span>
          </div>
          <div className="run-list">
            {sortedRuns.map((run) => (
              <Link key={run.review_run_id} className="run-card" to={`/runs/${run.review_run_id}`}>
                <div className="run-card__main">
                  <div>
                    <p className="run-card__repo">
                      {run.repo_owner}/{run.repo_name}
                    </p>
                    <strong>Pull Request #{run.pr_number}</strong>
                  </div>
                  <StatusBadge status={run.status} />
                </div>
                <div className="run-card__meta">
                  <span>{run.selected_model}</span>
                  <span>{formatDateTime(run.created_at)}</span>
                  <span className="run-card__arrow">Open</span>
                </div>
              </Link>
            ))}
            {!loading && runs.length === 0 ? <p className="empty-state">No persisted review runs yet.</p> : null}
          </div>
        </section>

        <section className="panel insight-panel">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Operational notes</p>
              <h2>What this view prioritizes</h2>
            </div>
          </div>
          <div className="insight-panel__body">
            <article className="insight-panel__item">
              <strong>Fast routing</strong>
              <p>Every run card routes directly into the detailed audit view, keeping diff, findings, and replay actions nearby.</p>
            </article>
            <article className="insight-panel__item">
              <strong>Status clarity</strong>
              <p>Cards surface state badges and timestamps first so stale or failed runs stand out without opening them.</p>
            </article>
            <article className="insight-panel__item">
              <strong>Model coverage</strong>
              <p>The summary row shows how many distinct models are in rotation across saved executions.</p>
            </article>
          </div>
        </section>
      </section>
    </section>
  );
}
