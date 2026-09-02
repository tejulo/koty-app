from typing import Literal

from pydantic import BaseModel, Field


Check = Literal["passed", "failed", "skipped"]


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
