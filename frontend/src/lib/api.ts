export type ReviewRunItem = {
  review_run_id: string;
  repo_owner: string;
  repo_name: string;
  pr_number: number;
  selected_model: string;
  status: string;
  created_at: string;
};

export type AgentTrace = {
  id?: number;
  agent_role: "inspector" | "fixer";
  model_name: string;
  prompt_version: string;
  input_payload: Record<string, unknown>;
  raw_response: Record<string, unknown> | string;
  parsed_output: Record<string, unknown>;
};

export type ReviewRunDetail = {
  run: ReviewRunItem & {
    diff_snapshot: string;
    summary_snapshot: string;
    result_payload: Record<string, unknown>;
    rendered_comments: Array<Record<string, unknown>>;
  };
  agent_traces: AgentTrace[];
};

export async function fetchReviewRuns(): Promise<ReviewRunItem[]> {
  const response = await fetch("/api/review-runs");
  const payload = await response.json();
  return payload.items;
}

export async function fetchReviewRunDetail(reviewRunId: string): Promise<ReviewRunDetail> {
  const response = await fetch(`/api/review-runs/${reviewRunId}`);
  return response.json();
}

export async function fetchModels(): Promise<{ default_model: string; items: string[] }> {
  const response = await fetch("/api/models");
  return response.json();
}

export async function replayReviewRun(reviewRunId: string, modelName: string) {
  const response = await fetch(`/api/review-runs/${reviewRunId}/replay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_name: modelName,
      publish_to_github: false
    })
  });
  return response.json();
}
