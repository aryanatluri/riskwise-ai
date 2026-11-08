"""SQLAlchemy models. The schema itself is owned by Alembic migrations (backend/alembic)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Role(str, enum.Enum):
    admin = "admin"
    reviewer = "reviewer"
    viewer = "viewer"


class FindingStatus(str, enum.Enum):
    open = "open"
    approved = "approved"
    rejected = "rejected"
    dispatched = "dispatched"
    resolved = "resolved"


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    jurisdiction: Mapped[str] = mapped_column(String(16), default="IN")
    sector: Mapped[str] = mapped_column(String(64), default="BFSI")
    regulation_packs: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("issuer", "subject"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), default="")
    name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), default=Role.viewer.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrgSettings(Base):
    __tablename__ = "org_settings"
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    # "rules_only" | "hybrid"  (hybrid = rules + the org's own LLM key)
    analysis_mode: Mapped[str] = mapped_column(String(16), default="rules_only")
    llm_provider: Mapped[str | None] = mapped_column(String(32))
    llm_model: Mapped[str | None] = mapped_column(String(128))
    llm_endpoint: Mapped[str | None] = mapped_column(String(512))
    llm_api_version: Mapped[str | None] = mapped_column(String(32))
    llm_api_key_enc: Mapped[str | None] = mapped_column(Text)
    llm_api_key_last4: Mapped[str | None] = mapped_column(String(8))
    jira_base_url: Mapped[str | None] = mapped_column(String(512))
    jira_email: Mapped[str | None] = mapped_column(String(320))
    jira_token_enc: Mapped[str | None] = mapped_column(Text)
    jira_project_key: Mapped[str | None] = mapped_column(String(32))
    slack_webhook_enc: Mapped[str | None] = mapped_column(Text)
    webhook_secret_enc: Mapped[str | None] = mapped_column(Text)
    escalation_email: Mapped[str | None] = mapped_column(String(320))
    sla_escalation_days: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    __table_args__ = (UniqueConstraint("org_id", "code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(64))
    mandate: Mapped[str] = mapped_column(Text)
    criticality: Mapped[str] = mapped_column(String(16), default="HIGH")
    constraints: Mapped[dict] = mapped_column(JSONB, default=dict)
    redline_template: Mapped[str] = mapped_column(Text, default="")
    owner_role: Mapped[str] = mapped_column(String(64), default="Legal")
    sla_days: Mapped[int] = mapped_column(Integer, default=5)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    counterparty: Mapped[str] = mapped_column(String(255), default="")
    contract_type: Mapped[str] = mapped_column(String(64), default="Vendor agreement")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    file_key: Mapped[str | None] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Clause(Base):
    __tablename__ = "clauses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    section_number: Mapped[str] = mapped_column(String(32), default="")
    heading: Mapped[str] = mapped_column(String(512), default="")
    text: Mapped[str] = mapped_column(Text)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(16))
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="running")
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    clause_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clauses.id", ondelete="CASCADE")
    )
    policy_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_rules.id", ondelete="SET NULL")
    )
    domain: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    severity: Mapped[str] = mapped_column(String(16))
    crs: Mapped[float] = mapped_column(Float)
    impact: Mapped[float] = mapped_column(Float)
    likelihood: Mapped[float] = mapped_column(Float)
    exposure: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    evidence_quote: Mapped[str] = mapped_column(Text, default="")
    regulation_refs: Mapped[list] = mapped_column(JSONB, default=list)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    proposed_redline: Mapped[str] = mapped_column(Text, default="")
    owner_role: Mapped[str] = mapped_column(String(64), default="")
    sla_days: Mapped[int] = mapped_column(Integer, default=5)
    source: Mapped[str] = mapped_column(String(16))  # "rules" | "llm"
    status: Mapped[str] = mapped_column(String(16), default=FindingStatus.open.value, index=True)
    assignee_email: Mapped[str | None] = mapped_column(String(320))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str] = mapped_column(Text, default="")
    jira_key: Mapped[str | None] = mapped_column(String(64), index=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_label: Mapped[str] = mapped_column(String(320), default="")
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
