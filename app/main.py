from fastapi import FastAPI

app = FastAPI(title="GitHub PR Auto Review")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
