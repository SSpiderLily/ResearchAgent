import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
SQLITE_PATH = DATA_DIR / "metadata.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-1b5c5d0f110c479a9b5a3c00156d56dc")

LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus-2025-07-28")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
