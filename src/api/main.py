from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import clients, content, audit, citations, social

ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / ".env")

app = FastAPI(title="SEO Machine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(clients.router,   prefix="/api/v1/clients",               tags=["clients"])
app.include_router(content.router,   prefix="/api/v1/clients/{abbr}/content", tags=["content"])
app.include_router(audit.router,     prefix="/api/v1/clients/{abbr}/audit",   tags=["audit"])
app.include_router(citations.router, prefix="/api/v1/clients/{abbr}/citations", tags=["citations"])
app.include_router(social.router,    prefix="/api/v1/clients/{abbr}/social",  tags=["social"])
