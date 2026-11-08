from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.db import get_db
from app.engine.packs import PACKS
from app.models import User
from app.security.auth import mint_dev_token

router = APIRouter()


@router.get("/healthz", include_in_schema=False)
def healthz(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"ok": True}


class DevTokenRequest(BaseModel):
    email: EmailStr
    name: str = ""


@router.post("/api/v1/dev/token", tags=["dev"])
def dev_token(body: DevTokenRequest) -> dict:
    s = get_settings()
    if s.auth_mode != "dev" or s.env == "prod":
        raise HTTPException(404, "Not found")
    return {
        "access_token": mint_dev_token(subject=body.email, email=body.email, name=body.name),
        "token_type": "bearer",
    }


@router.get("/api/v1/me", tags=["account"])
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": str(user.id), "email": user.email, "name": user.name}


@router.get("/api/v1/packs", tags=["reference"])
def packs() -> list[dict]:
    return [
        {
            "key": p.key,
            "title": p.title,
            "jurisdiction": p.jurisdiction,
            "reviewed": p.reviewed,
            "mandates": [
                {
                    "code": m.code,
                    "regulation": m.regulation,
                    "reference": m.reference,
                    "summary": m.summary,
                    "domains": list(m.domains),
                    "penalty": m.penalty,
                }
                for m in p.mandates
            ],
        }
        for p in PACKS.values()
    ]
