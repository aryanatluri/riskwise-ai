"""Runs the engine for a contract and saves clauses, the run record and findings."""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.engine.analyzer import analyze_text
from app.engine.llm import LLMClient, LLMConfig, LLMError
from app.engine.rules import RuleView
from app.models import AnalysisRun, Clause, Contract, Finding, Organization, OrgSettings, PolicyRule, User
from app.security.crypto import decrypt
from app.services import audit


def build_llm(s: OrgSettings) -> LLMClient | None:
    if s.analysis_mode != "hybrid":
        return None
    key = decrypt(s.llm_api_key_enc)
    if not (s.llm_provider and s.llm_model and key):
        raise LLMError("Hybrid mode needs a provider, model and API key in settings", fatal=True)
    return LLMClient(
        LLMConfig(
            provider=s.llm_provider,
            model=s.llm_model,
            api_key=key,
            endpoint=s.llm_endpoint,
            api_version=s.llm_api_version,
            timeout=get_settings().llm_timeout_seconds,
        )
    )


def run_analysis(
    db: Session,
    org: Organization,
    contract: Contract,
    text: str,
    actor: User | None,
    llm: LLMClient | None = None,
    use_org_llm: bool = True,
) -> AnalysisRun:
    cfg = get_settings()
    settings_row = db.get(OrgSettings, org.id)
    rules = [
        RuleView(
            code=r.code,
            title=r.title,
            domain=r.domain,
            mandate=r.mandate,
            criticality=r.criticality,
            constraints=r.constraints or {},
            redline_template=r.redline_template or "",
        )
        for r in db.scalars(select(PolicyRule).where(PolicyRule.org_id == org.id, PolicyRule.active.is_(True)))
    ]
    rule_ids = {
        code: rid for code, rid in db.execute(select(PolicyRule.code, PolicyRule.id).where(PolicyRule.org_id == org.id))
    }

    run = AnalysisRun(
        org_id=org.id,
        contract_id=contract.id,
        mode=settings_row.analysis_mode,
        provider=settings_row.llm_provider if settings_row.analysis_mode == "hybrid" else None,
        model=settings_row.llm_model if settings_row.analysis_mode == "hybrid" else None,
    )
    db.add(run)
    db.flush()

    owns_client = False
    try:
        if llm is None and use_org_llm:
            llm = build_llm(settings_row)
            owns_client = llm is not None
        result = analyze_text(
            text,
            rules,
            org.regulation_packs or [],
            llm,
            max_clauses=cfg.max_clauses_per_contract,
            max_llm_clauses=cfg.max_llm_clauses_per_run,
        )
    except LLMError as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
        contract.status = "failed"
        audit.record(
            db,
            org.id,
            "analysis.failed",
            actor=actor,
            target_type="contract",
            target_id=contract.id,
            details={"error": str(exc)},
        )
        db.flush()
        return run
    finally:
        if owns_client and llm is not None:
            llm.close()

    # Replace open findings and unreferenced clauses; decided findings (and their clauses) stay for the audit trail.
    db.execute(delete(Finding).where(Finding.contract_id == contract.id, Finding.status == "open"))
    referenced = select(Finding.clause_id).where(Finding.contract_id == contract.id, Finding.clause_id.is_not(None))
    db.execute(delete(Clause).where(Clause.contract_id == contract.id, Clause.id.not_in(referenced)))
    clause_rows = []
    for seg in result.segments:
        c = Clause(
            org_id=org.id,
            contract_id=contract.id,
            idx=seg.idx,
            section_number=seg.section_number,
            heading=seg.heading[:500],
            text=seg.text,
        )
        db.add(c)
        clause_rows.append(c)
    db.flush()

    for h in result.hits:
        clause = clause_rows[h.clause_index] if h.clause_index is not None else None
        db.add(
            Finding(
                org_id=org.id,
                contract_id=contract.id,
                run_id=run.id,
                clause_id=clause.id if clause else None,
                policy_rule_id=rule_ids.get(h.rule_code) if h.rule_code else None,
                domain=h.domain,
                title=h.title,
                severity=h.severity,
                crs=h.crs,
                impact=h.impact,
                likelihood=h.likelihood,
                exposure=h.exposure,
                confidence=h.confidence,
                evidence_quote=h.evidence_quote,
                regulation_refs=h.regulation_refs,
                reasoning=h.reasoning,
                recommended_action=h.recommended_action,
                proposed_redline=h.proposed_redline,
                owner_role=_owner_for(db, rule_ids.get(h.rule_code)) if h.rule_code else "Legal",
                sla_days=_sla_for(db, rule_ids.get(h.rule_code)) if h.rule_code else 5,
                source=h.source,
            )
        )

    run.status = "completed" if not result.stats.get("llm_errors") else "completed_with_errors"
    run.stats = result.stats
    run.finished_at = datetime.now(UTC)
    contract.status = "analyzed"
    audit.record(
        db,
        org.id,
        "analysis.completed",
        actor=actor,
        target_type="contract",
        target_id=contract.id,
        details={
            "run_id": str(run.id),
            "mode": run.mode,
            "findings": len(result.hits),
            "llm_errors": result.stats.get("llm_errors", 0),
        },
    )
    db.flush()
    return run


def _owner_for(db: Session, rule_id) -> str:
    r = db.get(PolicyRule, rule_id) if rule_id else None
    return r.owner_role if r else "Legal"


def _sla_for(db: Session, rule_id) -> int:
    r = db.get(PolicyRule, rule_id) if rule_id else None
    return r.sla_days if r else 5
