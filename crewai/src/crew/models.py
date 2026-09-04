from typing import Literal

from pydantic import BaseModel, Field, model_validator


Check = Literal["passed", "failed", "skipped"]
Phase = Literal[
    "planning",
    "implementing",
    "verifying",
    "browser_testing",
    "reviewing",
    "approved",
    "blocked",
]
VerificationProfile = Literal[
    "standard",
    "browser",
    "operational",
    "browser_operational",
]


class AcceptanceCriterion(BaseModel):
    id: str = Field(pattern=r"AC-[0-9]{3}")
    text: str = Field(min_length=1)


class TicketContract(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str
    change_id: str
    ticket_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    acceptance_criteria: list[AcceptanceCriterion]
    objective: str
    in_scope: list[str]
    constraints: list[str]
    dependencies: list[str]
    ambiguities: list[str]


class PlanDraftSpec(BaseModel):
    capability: str = Field(pattern=r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
    content: str = Field(min_length=1)


class PlanDraft(BaseModel):
    profile: VerificationProfile
    proposal: str = Field(min_length=1)
    design: str = Field(min_length=1)
    tasks: str = Field(min_length=1)
    specs: list[PlanDraftSpec] = Field(min_length=1)
    acceptance_map: dict[str, list[str]]

    @model_validator(mode="after")
    def require_unique_capabilities(self):
        capabilities = [spec.capability for spec in self.specs]
        if len(capabilities) != len(set(capabilities)):
            raise ValueError("PlanDraft has duplicate spec capabilities")
        return self


class PlanManifest(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str
    change_id: str
    ticket_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    ticket_contract_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    artifacts: dict[str, str]
    profile: VerificationProfile
    acceptance_map: dict[str, list[str]]
    base_gates: list[str] = Field(
        default_factory=lambda: [
            "python",
            "lint",
            "test",
            "build",
            "integration",
            "openspec",
        ]
    )

    @model_validator(mode="after")
    def require_core_open_spec_artifacts(self):
        required = {"proposal.md", "design.md", "tasks.md"}
        missing = required - set(self.artifacts)
        if missing:
            raise ValueError(
                "PlanManifest is missing required artifacts: "
                + ", ".join(sorted(missing))
            )
        if not any(path.startswith("specs/") for path in self.artifacts):
            raise ValueError("PlanManifest is missing an OpenSpec spec artifact")
        return self


class TaskCompletion(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str
    change_id: str
    plan_path: str
    plan_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    tasks_path: str
    tasks_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    acceptance_evidence: dict[str, dict[str, str]] = Field(default_factory=dict)


class RepairPack(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str
    change_id: str
    phase: Phase
    failure_stage: str
    plan_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    plan_path: str
    evidence_id: str
    evidence_path: str
    evidence_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    repair_hint: str
    repair_scope: list[str]
    referenced_files: dict[str, str]


class GateEvidence(BaseModel):
    evidence_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"[0-9a-f]{64}")


class ReviewPack(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str
    change_id: str
    ticket_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    ticket_contract_path: str
    ticket_contract_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    plan_path: str
    plan_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    profile: VerificationProfile
    acceptance_map: dict[str, list[str]]
    artifacts: dict[str, str]
    incomplete_tasks: bool
    task_completion_path: str
    task_completion_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    modified_paths: list[str]
    diff_summary: str
    gate_evidence_ids: dict[str, str]
    gate_statuses: dict[str, Check]
    gate_evidence: dict[str, GateEvidence]
    browser_result_path: str
    browser_result_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    artifact_paths: dict[str, str]
    operational_evidence: dict[str, dict[str, str]] = Field(default_factory=dict)
    referenced_files: dict[str, str]


class ExecutionState(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str = ""
    change_id: str | None = None
    phase: Phase = "planning"
    ticket_sha256: str | None = Field(default=None, pattern=r"[0-9a-f]{64}")
    plan_sha256: str | None = Field(default=None, pattern=r"[0-9a-f]{64}")
    profile: VerificationProfile | None = None
    last_attempt: int = Field(default=0, ge=0)
    phase_attempts: dict[Phase, int] = Field(default_factory=dict)
    ticket_contract_path: str | None = None
    plan_manifest_path: str | None = None
    task_completion_path: str | None = None
    repair_pack_path: str | None = None
    review_pack_path: str | None = None
    browser_result_path: str | None = None
    phase_usage: dict[str, object] = Field(default_factory=dict)


class TesterResult(BaseModel):
    status: Check
    summary: str
    scenarios: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    python: Check
    lint: Check
    test: Check
    build: Check
    integration: Check
    playwright: Check
    openspec: Check


class ReviewVerdict(BaseModel):
    ticket_id: str
    change_id: str
    status: Literal["approved", "retryable_failure", "blocked"]
    failure_type: Literal[
        "none",
        "implementation",
        "test",
        "infrastructure",
        "configuration",
        "requirements",
        "max_attempts",
    ] = "none"
    failure_stage: str | None = None
    summary: str


class CrewResult(BaseModel):
    ticket_id: str
    change_id: str
    attempt: int = Field(default=0, ge=0)
    evidence: dict[str, str] = Field(default_factory=dict)

    status: Literal[
        "approved",
        "retryable_failure",
        "blocked",
    ]

    failure_type: Literal[
        "none",
        "implementation",
        "test",
        "infrastructure",
        "configuration",
        "requirements",
        "max_attempts",
    ] = "none"

    failure_stage: str | None = None
    summary: str
    verification: VerificationResult


class CrewExecution(BaseModel):
    number: int = Field(default=1, ge=1)
    last_attempt: int = Field(default=0, ge=0)
    attempts: int = Field(default=0, ge=0)
    infrastructure_attempts: int = Field(default=0, ge=0)
    diagnostic_repair_attempts: int = Field(default=0, ge=0)
    diagnosed_fingerprints: list[str] = Field(default_factory=list)
    last_diagnosis_path: str | None = None
    last_failure_type: str | None = None
