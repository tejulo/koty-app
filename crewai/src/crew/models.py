import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


ArtifactKind = Literal["proposal", "design", "tasks", "spec"]


class StrictPlanningModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def canonical_model_sha256(model: BaseModel) -> str:
    content = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ProjectContextSection(StrictPlanningModel):
    ref: str = Field(pattern=r"^context-[0-9]{3}$")
    heading: str = Field(pattern=r"^#{2,3} .+$")
    body: str
    size: int = Field(ge=0)

    @model_validator(mode="after")
    def require_exact_size(self):
        if self.size != len(self.body):
            raise ValueError("ProjectContextSection size does not match its body")
        return self


class ProjectContextCatalog(StrictPlanningModel):
    schema_version: Literal[1] = 1
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sections: list[ProjectContextSection] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_refs(self):
        refs = [section.ref for section in self.sections]
        if len(refs) != len(set(refs)):
            raise ValueError("ProjectContextCatalog has duplicate refs")
        return self


class PlanUnitOutline(StrictPlanningModel):
    artifact: ArtifactKind
    capability: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
    )
    objective: str = Field(min_length=1, pattern=r"\S")
    context_refs: list[str]

    @model_validator(mode="after")
    def require_artifact_capability(self):
        if self.artifact == "spec" and self.capability is None:
            raise ValueError("spec units require a capability")
        if self.artifact != "spec" and self.capability is not None:
            raise ValueError("core units cannot declare a capability")
        return self

    @property
    def unit_key(self) -> str:
        return f"spec:{self.capability}" if self.artifact == "spec" else self.artifact


class PlanOutline(StrictPlanningModel):
    schema_version: Literal[1] = 1
    profile: VerificationProfile
    units: list[PlanUnitOutline]
    acceptance_map: dict[str, list[str]]

    @model_validator(mode="after")
    def require_complete_unique_units(self):
        keys = [unit.unit_key for unit in self.units]
        if len(keys) != len(set(keys)):
            raise ValueError("PlanOutline has duplicate units")
        core = {unit.artifact for unit in self.units if unit.artifact != "spec"}
        missing = {"proposal", "design", "tasks"} - core
        if missing:
            raise ValueError(
                "PlanOutline is missing core units: " + ", ".join(sorted(missing))
            )
        if not any(unit.artifact == "spec" for unit in self.units):
            raise ValueError("PlanOutline requires at least one spec unit")
        return self


class PlanArtifactUnit(StrictPlanningModel):
    schema_version: Literal[1] = 1
    artifact: ArtifactKind
    capability: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
    )
    content: str = Field(min_length=1, pattern=r"\S")

    @model_validator(mode="after")
    def require_artifact_capability(self):
        if self.artifact == "spec" and self.capability is None:
            raise ValueError("spec units require a capability")
        if self.artifact != "spec" and self.capability is not None:
            raise ValueError("core units cannot declare a capability")
        return self

    @property
    def unit_key(self) -> str:
        return f"spec:{self.capability}" if self.artifact == "spec" else self.artifact


class PlanningCheckpoint(StrictPlanningModel):
    schema_version: Literal[1] = 1
    ticket_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    context_catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outline_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outline: PlanOutline
    units: list[PlanArtifactUnit] = Field(default_factory=list)
    unit_sha256: dict[str, str] = Field(default_factory=dict)
    invocation_status: dict[str, Literal["pending", "completed", "failed"]] = Field(
        default_factory=dict
    )
    length_retry_status: dict[str, Literal["pending", "consumed"]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def require_hash_bound_units(self):
        if self.outline_sha256 != canonical_model_sha256(self.outline):
            raise ValueError("PlanningCheckpoint outline hash does not match outline")
        unit_keys = [unit.unit_key for unit in self.units]
        if len(unit_keys) != len(set(unit_keys)):
            raise ValueError("PlanningCheckpoint has duplicate units")
        if set(unit_keys) != set(self.unit_sha256):
            raise ValueError("PlanningCheckpoint unit hashes do not match units")
        if any(
            len(value) != 64 or set(value) - set("0123456789abcdef")
            for value in self.unit_sha256.values()
        ):
            raise ValueError("PlanningCheckpoint has an invalid unit hash")
        if any(
            self.unit_sha256[unit.unit_key] != canonical_model_sha256(unit)
            for unit in self.units
        ):
            raise ValueError("PlanningCheckpoint unit hash does not match stored unit")
        outline_keys = {unit.unit_key for unit in self.outline.units}
        if not set(unit_keys) <= outline_keys:
            raise ValueError("PlanningCheckpoint contains units outside its outline")
        if not set(self.invocation_status) <= outline_keys:
            raise ValueError("PlanningCheckpoint has status for an unknown unit")
        if not set(self.length_retry_status) <= outline_keys:
            raise ValueError("PlanningCheckpoint has length retry for an unknown unit")
        completed = {
            key for key, status in self.invocation_status.items() if status == "completed"
        }
        if completed != set(unit_keys):
            raise ValueError(
                "PlanningCheckpoint completed statuses must match stored units"
            )
        stored = set(unit_keys)
        for key, retry_status in self.length_retry_status.items():
            invocation_status = self.invocation_status.get(key)
            if retry_status == "pending" and (
                invocation_status != "failed" or key in stored
            ):
                raise ValueError(
                    "PlanningCheckpoint pending length retry requires failed "
                    "invocation status and no stored unit"
                )
            if retry_status == "consumed" and invocation_status not in {
                "failed",
                "completed",
            }:
                raise ValueError(
                    "PlanningCheckpoint consumed length retry requires failed or "
                    "completed invocation status"
                )
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
    planning_checkpoint_path: str | None = None
    planning_checkpoint_sha256: str | None = Field(
        default=None, pattern=r"[0-9a-f]{64}"
    )
    planning_empty_response_retry_state: Literal[
        "available", "pending", "consumed"
    ] = "available"
    planning_empty_response_retry_target: str | None = Field(
        default=None, min_length=1
    )
    plan_manifest_path: str | None = None
    task_completion_path: str | None = None
    repair_pack_path: str | None = None
    review_pack_path: str | None = None
    browser_result_path: str | None = None
    phase_usage: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_bound_planning_control_state(self):
        if (self.planning_checkpoint_path is None) != (
            self.planning_checkpoint_sha256 is None
        ):
            raise ValueError(
                "ExecutionState planning checkpoint path and hash must be set together"
            )
        if self.planning_empty_response_retry_state == "available":
            if self.planning_empty_response_retry_target is not None:
                raise ValueError(
                    "Available planning empty-response retry cannot have a target"
                )
        elif self.planning_empty_response_retry_target is None:
            raise ValueError(
                "Pending or consumed planning empty-response retry requires a target"
            )
        return self


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
