import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchReviewRuns, type ReviewRunItem } from "../lib/api";

export function ReviewRunListPage() {
  const [runs, setRuns] = useState<ReviewRunItem[]>([]);

  useEffect(() => {
    fetchReviewRuns().then(setRuns).catch(() => setRuns([]));
  }, []);

  return (
    <section className="panel">
      <div className="panel__header">
        <h2>Review History</h2>
      </div>
      <div className="run-list">
        {runs.map((run) => (
          <Link key={run.review_run_id} className="run-card" to={`/runs/${run.review_run_id}`}>
            <strong>
              {run.repo_owner}/{run.repo_name}#{run.pr_number}
            </strong>
            <span>{run.selected_model}</span>
            <span>{run.status}</span>
          </Link>
        ))}
        {runs.length === 0 ? <p className="empty-state">No persisted review runs yet.</p> : null}
      </div>
    </section>
  );
}
