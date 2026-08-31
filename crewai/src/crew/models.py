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
    playwright: Check
    openspec: Check


class CrewResult(BaseModel):
    ticket_id: str
    change_id: str

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
    attempts: int = Field(default=0, ge=0)
    infrastructure_attempts: int = Field(default=0, ge=0)
    last_failure_type: str | None = None
