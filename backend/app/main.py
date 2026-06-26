from fastapi import FastAPI

app = FastAPI(title="Attribution Analysis API")


@app.get("/health")
async def health():
    return {"status": "ok"}