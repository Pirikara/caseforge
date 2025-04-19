from fastapi import FastAPI
from app.api import projects

app = FastAPI()
app.include_router(projects.router)

@app.get("/health")
def health():
    return {"status": "ok"}