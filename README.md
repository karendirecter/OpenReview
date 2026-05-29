# GitHub PR Auto Review

An MVP GitHub App service that listens for `/review` comments on pull requests, runs Stage 1 static checks plus Stage 2 LLM review, and posts summary and inline review comments back to GitHub.

## What It Does

- Listens for GitHub `issue_comment` webhooks at `POST /webhooks/github`
- Only triggers when the comment body is exactly `/review`
- Pulls the PR diff and changed file contents through the GitHub App installation
- Runs Stage 1 checks:
  - broad exception swallowing in diffs
  - Python `None` dereference heuristics
  - missing `await`
  - blocking calls inside `async def`
  - resource leak heuristics
- Runs Stage 2 LLM review through an OpenAI-compatible API
- Posts:
  - one PR summary comment
  - zero or more inline review comments

## Requirements

- Python `3.11+`
- Docker Desktop or Docker Engine
- A GitHub App installed on the target repository
- An OpenAI-compatible LLM endpoint

## 1. Clone And Prepare

```powershell
git clone <your-repo-url>
cd <repo>\.claude\worktrees\task18-detail
copy .env.example .env
```

Fill `.env` with real values:

- `GITHUB_WEBHOOK_SECRET`
- `GITHUB_APP_ID`
- `GITHUB_PRIVATE_KEY`
- `GITHUB_INSTALLATION_ID`
- `LLM_API_KEY`

Notes:

- `GITHUB_PRIVATE_KEY` should be a single-line value with literal `\n`
- `LLM_BASE_URL` defaults to Volcengine Ark in `.env.example`
- `LLM_MODEL` defaults to `deepseek-v4-flash-260425`

## 2. Configure The GitHub App

Recommended GitHub App settings:

- Repository permissions:
  - `Contents: Read-only`
  - `Pull requests: Read and write`
  - `Issues: Read-only`
- Subscribe to webhook events:
  - `Issue comment`

Webhook URL must point to:

```text
https://<your-public-url>/webhooks/github
```

The service only reacts to PR comments. Normal issue comments are ignored.

## 3. Start The Service

This repository already includes DNS settings in `docker-compose.yml` because some Docker environments incorrectly resolve `github.com` and `api.github.com`.

Start with:

```powershell
docker compose up -d --build
```

Stop with:

```powershell
docker compose down
```

Check container status:

```powershell
docker ps
docker logs github-pr-auto-review
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 4. Expose The Webhook Publicly

If you run locally, you still need a public URL for GitHub webhooks. You can use a tunnel such as `localtunnel`, `ngrok`, or another reverse tunnel.

After you get the public URL, update the GitHub App webhook URL to:

```text
https://<public-url>/webhooks/github
```

## 5. End-To-End Test

1. Open a PR in a repository where the GitHub App is installed.
2. Comment:

```text
/review
```

3. Watch the service log:

```powershell
docker logs -f github-pr-auto-review
```

Expected behavior:

- webhook request returns `202 Accepted`
- the PR receives a summary comment
- if findings are produced, the PR also receives inline review comments

## 6. Optional Connectivity Checks

Verify GitHub access from inside the container:

```powershell
docker exec github-pr-auto-review uv run python -c "from app.config import Settings; from github import Auth, GithubIntegration; s=Settings(); auth=Auth.AppAuth(s.github_app_id, s.github_private_key); gh=GithubIntegration(auth=auth).get_github_for_installation(int(s.github_installation_id)); pr=gh.get_repo('karendirecter/notion-lite').get_pull(2); print(pr.title); print(pr.html_url); print(pr.head.sha)"
```

Verify LLM access from inside the container:

```powershell
docker exec github-pr-auto-review uv run python -c "from openai import OpenAI; from app.config import Settings; s=Settings(); c=OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key); r=c.chat.completions.create(model=s.llm_model, messages=[{'role':'user','content':'Reply with the single word OK'}]); print(r.choices[0].message.content)"
```

## 7. Run Tests

Local test command:

```powershell
uv run pytest -q
```

## 8. Known Limitations

- The current webhook path only supports `/review` comment-triggered review
- The container DNS fix is encoded in `docker-compose.yml`; if you use raw `docker run`, you need equivalent DNS settings yourself
- Some LLM responses may still include weak or noisy findings; the current system prioritizes getting a real review flow running end-to-end
