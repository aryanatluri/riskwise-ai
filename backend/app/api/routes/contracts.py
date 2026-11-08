import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select

from app.api.deps import OrgContext, admin, get_org_context, reviewer
from app.config import get_settings
from app.engine.extraction import ExtractionError, extract_text
from app.models import AnalysisRun, Clause, Contract, Finding, Organization
from app.services import audit
from app.services.analysis import run_analysis
from app.services.storage import get_storage

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


def _contract_out(c: Contract, counts: dict | None = None) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "counterparty": c.counterparty,
        "contract_type": c.contract_type,
        "file_name": c.file_name,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "open_findings": (counts or {}).get(c.id, 0),
    }


def _run_out(r: AnalysisRun) -> dict:
    return {
        "id": str(r.id),
        "mode": r.mode,
        "provider": r.provider,
        "model": r.model,
        "status": r.status,
        "stats": r.stats,
        "error": r.error,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


@router.post("", status_code=201)
async def upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    counterparty: str = Form(""),
    contract_type: str = Form("Vendor agreement"),
    ctx: OrgContext = Depends(reviewer),
) -> dict:
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {get_settings().max_upload_mb} MB")
    name = (file.filename or "contract.txt")[:255]
    try:
        text = extract_text(name, data)
    except ExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc

    contract = Contract(
        org_id=ctx.org_id,
        title=(title or name)[:255],
        counterparty=counterparty[:255],
        contract_type=contract_type[:64],
        file_name=name,
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=ctx.user.id,
        status="uploaded",
    )
    contract.file_key = get_storage().put(ctx.org_id, name, data)
    ctx.db.add(contract)
    ctx.db.flush()
    audit.record(
        ctx.db,
        ctx.org_id,
        "contract.uploaded",
        actor=ctx.user,
        target_type="contract",
        target_id=contract.id,
        details={"file_name": name, "sha256": contract.sha256},
    )

    org = ctx.db.get(Organization, ctx.org_id)
    run = run_analysis(ctx.db, org, contract, text, ctx.user)
    return {"contract": _contract_out(contract), "run": _run_out(run)}


@router.get("")
def list_contracts(ctx: OrgContext = Depends(get_org_context)) -> list[dict]:
    rows = list(
        ctx.db.scalars(select(Contract).where(Contract.org_id == ctx.org_id).order_by(Contract.created_at.desc()))
    )
    counts = dict(
        ctx.db.execute(
            select(Finding.contract_id, func.count())
            .where(Finding.org_id == ctx.org_id, Finding.status == "open")
            .group_by(Finding.contract_id)
        ).all()
    )
    return [_contract_out(c, counts) for c in rows]


def _get(ctx: OrgContext, contract_id: str) -> Contract:
    c = ctx.db.scalar(select(Contract).where(Contract.id == contract_id, Contract.org_id == ctx.org_id))
    if c is None:
        raise HTTPException(404, "Contract not found")
    return c


@router.get("/{contract_id}")
def get_contract(contract_id: str, ctx: OrgContext = Depends(get_org_context)) -> dict:
    c = _get(ctx, contract_id)
    clauses = ctx.db.scalars(select(Clause).where(Clause.contract_id == c.id).order_by(Clause.idx))
    runs = ctx.db.scalars(
        select(AnalysisRun).where(AnalysisRun.contract_id == c.id).order_by(AnalysisRun.started_at.desc()).limit(10)
    )
    return {
        **_contract_out(c),
        "clauses": [
            {"id": str(x.id), "idx": x.idx, "section_number": x.section_number, "heading": x.heading, "text": x.text}
            for x in clauses
        ],
        "runs": [_run_out(r) for r in runs],
    }


@router.post("/{contract_id}/analyze")
def reanalyze(contract_id: str, ctx: OrgContext = Depends(reviewer)) -> dict:
    c = _get(ctx, contract_id)
    if not c.file_key:
        raise HTTPException(409, "Original file was deleted; upload it again")
    text = extract_text(c.file_name, get_storage().get(c.file_key))
    run = run_analysis(ctx.db, ctx.db.get(Organization, ctx.org_id), c, text, ctx.user)
    return {"contract": _contract_out(c), "run": _run_out(run)}


@router.delete("/{contract_id}", status_code=204)
def delete_contract(contract_id: str, ctx: OrgContext = Depends(admin)) -> None:
    """Deletes the file and all derived data. The audit log keeps a record that this happened."""
    c = _get(ctx, contract_id)
    if c.file_key:
        get_storage().delete(c.file_key)
    audit.record(
        ctx.db,
        ctx.org_id,
        "contract.deleted",
        actor=ctx.user,
        target_type="contract",
        target_id=c.id,
        details={"title": c.title, "sha256": c.sha256},
    )
    ctx.db.delete(c)
