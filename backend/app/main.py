from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import projects

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)

@app.get("/health")
def health():
    return {"status": "ok"}