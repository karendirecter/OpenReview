import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { DiffViewer } from "../components/DiffViewer";
import { ModelSwitcher } from "../components/ModelSwitcher";
import { fetchModels, fetchReviewRunDetail, replayReviewRun, type ReviewRunDetail } from "../lib/api";

export function ReviewRunDetailPage() {
  const { reviewRunId = "" } = useParams();
  const [detail, setDetail] = useState<ReviewRunDetail | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [loadingReplay, setLoadingReplay] = useState(false);
  const [replayResponse, setReplayResponse] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetchReviewRunDetail(reviewRunId).then(setDetail).catch(() => setDetail(null));
    fetchModels()
      .then((payload) => {
        setModels(payload.items);
        setSelectedModel(payload.default_model);
      })
      .catch(() => {
        setModels([]);
        setSelectedModel("");
      });
  }, [reviewRunId]);

  async function handleReplay() {
    setLoadingReplay(true);
    try {
      const payload = await replayReviewRun(reviewRunId, selectedModel);
      setReplayResponse(payload);
    } finally {
      setLoadingReplay(false);
    }
  }

  return (
    <div className="detail-layout">
      <ModelSwitcher
        models={models}
        selectedModel={selectedModel}
        loading={loadingReplay}
        onChange={setSelectedModel}
        onReplay={handleReplay}
      />
      <DiffViewer diff={detail?.run.diff_snapshot ?? ""} />
      <section className="panel">
        <div className="panel__header">
          <h2>Agent Output</h2>
        </div>
        <div className="trace-grid">
          {detail?.agent_traces.map((trace) => (
            <article key={`${trace.agent_role}-${trace.prompt_version}`} className="trace-card">
              <h3>{trace.agent_role}</h3>
              <p>{trace.model_name}</p>
              <pre>{JSON.stringify(trace.parsed_output, null, 2)}</pre>
            </article>
          ))}
          {detail?.agent_traces.length ? null : <p className="empty-state">No agent traces recorded.</p>}
        </div>
      </section>
      <section className="panel">
        <div className="panel__header">
          <h2>Final Findings</h2>
        </div>
        <div className="trace-grid">
          {((detail?.run.result_payload as { findings?: unknown[] } | undefined)?.findings ?? []).map(
            (finding, index) => (
              <article key={index} className="trace-card">
                <h3>{(finding as { issue_title?: string }).issue_title ?? "Untitled finding"}</h3>
                <p>
                  {(finding as { file_path?: string }).file_path ?? "unknown"}:
                  {(finding as { line_number?: number }).line_number ?? "?"}
                </p>
                <pre>{JSON.stringify(finding, null, 2)}</pre>
              </article>
            )
          )}
          {(((detail?.run.result_payload as { findings?: unknown[] } | undefined)?.findings ?? []).length ?? 0) === 0 ? (
            <p className="empty-state">No finalized findings recorded.</p>
          ) : null}
        </div>
      </section>
      <section className="panel">
        <div className="panel__header">
          <h2>Replay Result</h2>
        </div>
        <pre className="diff-viewer">{JSON.stringify(replayResponse, null, 2)}</pre>
      </section>
    </div>
  );
}
