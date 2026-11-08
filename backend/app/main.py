import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import contracts, findings, ops, orgs, policies, settings, system
from app.config import get_settings


def create_app() -> FastAPI:
    cfg = get_settings()
    logging.basicConfig(level=logging.INFO if cfg.env != "test" else logging.WARNING)
    if cfg.env == "prod" and cfg.auth_mode == "dev":
        raise RuntimeError("AUTH_MODE=dev is not allowed when ENV=prod")

    app = FastAPI(
        title="RISKWISE AI",
        version="0.2.0",
        description="Contract risk review for regulated financial institutions. Bring your own LLM key.",
        docs_url="/docs" if cfg.env != "prod" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Org-Id"],
    )
    for r in (system, orgs, settings, policies, contracts, findings, ops):
        app.include_router(r.router)
    return app


app = create_app()
