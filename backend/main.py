import sys
from pathlib import Path

# Ensure project root is on sys.path so `config` and `backend.*` imports work
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat import router as chat_router
from backend.api.papers import router as papers_router
from backend.storage.database import init_db

app = FastAPI(title="Research Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers_router)
app.include_router(chat_router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
