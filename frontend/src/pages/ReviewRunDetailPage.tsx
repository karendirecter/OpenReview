import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { DiffViewer } from "../components/DiffViewer";
import { MetricCard } from "../components/MetricCard";
import { ModelSwitcher } from "../components/ModelSwitcher";
import { StatusBadge } from "../components/StatusBadge";
import { formatDateTime } from "../lib/format";
import { fetchModels, fetchReviewRunDetail, replayReviewRun, type ReviewRunDetail } from "../lib/api";

export function ReviewRunDetailPage() {
  const { reviewRunId = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<ReviewRunDetail | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [loadingReplay, setLoadingReplay] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [replayResponse, setReplayResponse] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      setLoadingDetail(true);

      try {
        const [nextDetail, modelPayload] = await Promise.all([fetchReviewRunDetail(reviewRunId), fetchModels()]);
        if (cancelled) {
          return;
        }

        setDetail(nextDetail);
        setModels(modelPayload.items);
        setSelectedModel(modelPayload.default_model);
      } catch {
        if (cancelled) {
          return;
        }

        setDetail(null);
        setModels([]);
        setSelectedModel("");
      } finally {
        if (!cancelled) {
          setLoadingDetail(false);
        }
      }
    }

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, [reviewRunId]);

  async function handleReplay() {
    setLoadingReplay(true);
    try {
      const payload = await replayReviewRun(reviewRunId, selectedModel);
      setReplayResponse(payload);
    } catch {
      setReplayResponse({ error: "Replay request failed." });
    } finally {
      setLoadingReplay(false);
    }
  }

  const findings = ((detail?.run.result_payload as { findings?: unknown[] } | undefined)?.findings ?? []) as Array<
    Record<string, unknown>
  >;
  const traceCount = detail?.agent_traces.length ?? 0;
  const renderedCommentsCount = detail?.run.rendered_comments.length ?? 0;
  const diffLineCount = detail?.run.diff_snapshot ? detail.run.diff_snapshot.split("\n").length : 0;
  const repoLabel = detail ? `${detail.run.repo_owner}/${detail.run.repo_name}#${detail.run.pr_number}` : "Review run";
  const summaryText =
    detail?.run.summary_snapshot?.trim() || "No summary snapshot was stored for this review run.";
  const createdAt = detail ? formatDateTime(detail.run.created_at) : "Unknown time";

  return (
    <section className="page-stack">
      <section className="hero-card panel">
        <div className="hero-card__content">
          <div className="detail-hero__topline">
            <Link className="link-back" to="/">
              Back to dashboard
            </Link>
            {detail ? <StatusBadge status={detail.run.status} /> : null}
          </div>
          <p className="eyebrow">Review run</p>
          <h3>{repoLabel}</h3>
          <p>{summaryText}</p>
        </div>
        <div className="hero-card__highlight">
          <span className="hero-card__label">Created at</span>
          <strong>{createdAt}</strong>
          <p>{loadingDetail ? "Loading execution context..." : "Diff, trace, and findings are grouped below."}</p>
        </div>
      </section>

      <section className="metric-grid" aria-label="Run metrics">
        <MetricCard accent="teal" icon="FG" label="Findings" value={String(findings.length)} detail="Finalized issues in result payload" />
        <MetricCard accent="amber" icon="DF" label="Diff lines" value={String(diffLineCount)} detail="Saved lines in the diff snapshot" />
        <MetricCard accent="rose" icon="AI" label="Agent traces" value={String(traceCount)} detail="Captured inspector or fixer executions" />
        <MetricCard
          accent="blue"
          icon="CM"
          label="Rendered comments"
          value={String(renderedCommentsCount)}
          detail="Comments prepared for publication"
        />
      </section>

      <section className="detail-grid">
        <div className="detail-grid__main">
          <DiffViewer diff={detail?.run.diff_snapshot ?? ""} />

          <section className="panel">
            <div className="panel__header">
              <div>
                <p className="panel__eyebrow">Resolved issues</p>
                <h2>Final Findings</h2>
              </div>
              <span className="panel__meta">{findings.length} items</span>
            </div>
            <div className="trace-grid">
              {findings.map((finding, index) => (
                <article key={`${String(finding.issue_title ?? "finding")}-${index}`} className="trace-card">
                  <div className="trace-card__header">
                    <h3>{String(finding.issue_title ?? "Untitled finding")}</h3>
                    <span className="trace-card__meta">
                      {String(finding.file_path ?? "unknown")}:{String(finding.line_number ?? "?")}
                    </span>
                  </div>
                  <pre>{JSON.stringify(finding, null, 2)}</pre>
                </article>
              ))}
              {!findings.length ? <p className="empty-state">No finalized findings recorded.</p> : null}
            </div>
          </section>

          <section className="panel">
            <div className="panel__header">
              <div>
                <p className="panel__eyebrow">Trace log</p>
                <h2>Agent Output</h2>
              </div>
              <span className="panel__meta">{traceCount} traces</span>
            </div>
            <div className="trace-grid">
              {detail?.agent_traces.map((trace) => (
                <article key={String(trace.id ?? `${trace.agent_role}-${trace.prompt_version}`)} className="trace-card">
                  <div className="trace-card__header">
                    <div>
                      <h3>{trace.agent_role}</h3>
                      <p>{trace.model_name}</p>
                    </div>
                    <span className="trace-card__meta">{trace.prompt_version}</span>
                  </div>
                  <pre>{JSON.stringify(trace.parsed_output, null, 2)}</pre>
                </article>
              ))}
              {detail?.agent_traces.length ? null : <p className="empty-state">No agent traces recorded.</p>}
            </div>
          </section>
        </div>

        <div className="detail-grid__side">
          <ModelSwitcher
            models={models}
            selectedModel={selectedModel}
            loading={loadingReplay}
            onChange={setSelectedModel}
            onReplay={handleReplay}
          />

          <section className="panel">
            <div className="panel__header">
              <div>
                <p className="panel__eyebrow">Run metadata</p>
                <h2>Execution Notes</h2>
              </div>
            </div>
            <div className="detail-meta">
              <div>
                <span>Run ID</span>
                <strong>{reviewRunId}</strong>
              </div>
              <div>
                <span>Selected model</span>
                <strong>{selectedModel || "Unavailable"}</strong>
              </div>
              <div>
                <span>Created</span>
                <strong>{createdAt}</strong>
              </div>
              <button type="button" className="button button--ghost" onClick={() => navigate("/")}>
                Return to overview
              </button>
            </div>
          </section>

          <section className="panel">
            <div className="panel__header">
              <div>
                <p className="panel__eyebrow">Replay output</p>
                <h2>Latest Response</h2>
              </div>
            </div>
            <pre className="diff-viewer">
              {replayResponse ? JSON.stringify(replayResponse, null, 2) : "Replay has not been executed yet."}
            </pre>
          </section>
        </div>
      </section>
    </section>
  );
}
