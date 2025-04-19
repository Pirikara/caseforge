from fastapi import FastAPI
app = FastAPI(title="Caseforge API")

@app.get("/health")
def health():
    return {"status": "ok"}
