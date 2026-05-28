from fastapi import FastAPI

app = FastAPI(title="GitHub PR Auto Review")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """
    Health check endpoint.
    文档缺陷标注：PLAN.md Task 1 步骤中没有说明此 health check 的用途
    """
    return {"status": "ok"}