from fastapi import FastAPI

app = FastAPI(title="SourcePilot API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
