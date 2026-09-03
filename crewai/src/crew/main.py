import hashlib
import json
import os
import re
import subprocess
import argparse
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

from .crew import KotyAppCrew
from .evidence import diagnose_integration_failure
from .gates import GateRun, diagnose_gate_failure, run_gate
from .linear_api import get_issue
from .models import (
    ExecutionState,
    CrewResult,
    PlanManifest,
    RepairPack,
    ReviewPack,
    ReviewVerdict,
    TaskCompletion,
    TesterResult,
    TicketContract,
    VerificationResult,
)
from .tools.custom_tool import close_local_environment, close_playwright_session
from . import workflow


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent
load_dotenv(CREWAI_ROOT / ".env")
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"

ROLE_LIMITS = {
    "analyst": ("ZEN_ANALYST_MODEL", "ZEN_ANALYST_MAX_TOKENS", 4, 800),
    "architect": ("ZEN_ARCHITECT_MODEL", "ZEN_ARCHITECT_MAX_TOKENS", 12, 1200),
    "programmer": ("ZEN_CODER_MODEL", "ZEN_CODER_MAX_TOKENS", 20, 2500),
    "tester": ("ZEN_TESTER_MODEL", "ZEN_TESTER_MAX_TOKENS", 8, 600),
    "reviewer": ("ZEN_REVIEWER_MODEL", "ZEN_REVIEWER_MAX_TOKENS", 8, 800),
}
ROLE_CREWS = {
    "analyst": "analyst_crew",
    "architect": "architect_crew",
    "programmer": "programmer_crew",
    "tester": "tester_crew",
    "reviewer": "reviewer_crew",
}
PROFILE_PATTERN = re.compile(r"^verification_profile:\s*(\S+)\s*$", re.MULTILINE)
ModelT = TypeVar("ModelT", bound=BaseModel)


def normalize(raw_id: str) -> tuple[str, str]:
    raw_id = raw_id.strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*-\d+", raw_id):
        raise ValueError("Ticket inválido. Ejemplo: DEV-40")
    return raw_id.upper(), raw_id.lower()


def active_change(change_id: str) -> Path:
    return workflow.PROJECT_ROOT / "openspec" / "changes" / change_id


def ensure_change(change_id: str) -> None:
    if active_change(change_id).is_dir():
        return
    result = subprocess.run(
        ["pnpm", "exec", "openspec", "new", "change", change_id],
        cwd=workflow.PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def current_ticket_sha256(ticket_id: str) -> str:
    payload = json.dumps(get_issue(ticket_id), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def kickoff_role(role: str, *, inputs: dict[str, str]) -> object:
    crew_factory = getattr(KotyAppCrew(), ROLE_CREWS[role])
    return crew_factory().kickoff(inputs=inputs)


def _run_gate(name: str, change_id: str) -> GateRun:
    return run_gate(name, change_id)


def run_base_gates(_ticket_id: str, change_id: str) -> list[GateRun]:
    return [_run_gate(name, change_id) for name in workflow.BASE_GATES]


def _project_path(reference: str) -> Path:
    candidate = Path(reference)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Persisted path is outside the project")
    path = (workflow.PROJECT_ROOT / candidate).resolve()
    if not path.is_relative_to(workflow.PROJECT_ROOT.resolve()):
        raise ValueError("Persisted path is outside the project")
    return path


def _relative(path: Path) -> str:
    return path.resolve().relative_to(workflow.PROJECT_ROOT.resolve()).as_posix()


def _attempt(state: ExecutionState) -> int:
    if state.last_attempt == 0:
        state.last_attempt = 1
    return state.last_attempt


def _selected_profile(change_id: str) -> str:
    design = active_change(change_id) / "design.md"
    match = PROFILE_PATTERN.search(design.read_text(encoding="utf-8")) if design.is_file() else None
    if not match or match.group(1) not in {"standard", "browser", "operational", "browser_operational"}:
        raise ValueError("OpenSpec design has no valid verification_profile")
    return match.group(1)


def _as_model(output: object, model_type: type[ModelT]) -> ModelT:
    value = getattr(output, "pydantic", None)
    if isinstance(value, model_type):
        return value
    if value is not None:
        return model_type.model_validate(value)
    raise ValueError(f"Role did not return {model_type.__name__}")


def _serializable(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return json.loads(json.dumps(value, default=str))


def _record_usage(state: ExecutionState, role: str, output: object) -> None:
    phase = state.phase
    attempt = _attempt(state)
    model_env, max_tokens_env, max_iter, default_max_tokens = ROLE_LIMITS[role]
    max_tokens = int(os.environ.get(max_tokens_env, default_max_tokens))
    usage = getattr(output, "token_usage", None)
    if usage is None:
        usage = getattr(output, "usage_metrics", None)
    payload = {
        "phase": phase,
        "role": role,
        "model": os.environ.get(model_env),
        "limits": {"max_iter": max_iter, "max_tokens": max_tokens},
        "attempt": attempt,
        "usage": _serializable(usage) if usage is not None else None,
    }
    path = workflow.ticket_contract_path(state.change_id or "invalid", attempt).parent / f"phase-usage-{phase}-{role}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    reference = _relative(path)
    state.phase_usage[f"{phase}:{role}"] = reference
    state.phase_usage[phase] = reference
    state.phase_attempts[phase] = state.phase_attempts.get(phase, 0) + 1


def _reset_for_planning(state: ExecutionState, ticket_sha256: str) -> ExecutionState:
    state.phase = "planning"
    state.ticket_sha256 = ticket_sha256
    state.last_attempt += 1
    state.plan_sha256 = None
    state.profile = None
    state.ticket_contract_path = None
    state.plan_manifest_path = None
    state.task_completion_path = None
    state.repair_pack_path = None
    state.review_pack_path = None
    state.browser_result_path = None
    return state


def _check_ticket(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    ticket_sha256 = current_ticket_sha256(ticket_id)
    state.ticket_id = ticket_id
    state.change_id = change_id
    if state.ticket_sha256 is None:
        state.ticket_sha256 = ticket_sha256
    elif state.ticket_sha256 != ticket_sha256:
        return _reset_for_planning(state, ticket_sha256)
    return state


def _current_contracts(
    ticket_id: str, change_id: str, state: ExecutionState, *, repair: bool = False
) -> tuple[TicketContract, PlanManifest, Path, Path] | None:
    try:
        if not state.ticket_contract_path or not state.plan_manifest_path or not state.plan_sha256:
            raise ValueError("Execution state has no current planning contracts")
        contract_path = _project_path(state.ticket_contract_path)
        plan_path = _project_path(state.plan_manifest_path)
        if workflow.file_sha256(plan_path) != state.plan_sha256:
            raise ValueError("Execution plan hash is stale")
        contract = workflow.load_model(contract_path, TicketContract)
        manifest = workflow.load_model(plan_path, PlanManifest)
        profile = _selected_profile(change_id)
        artifact_paths = {name: active_change(change_id) / name for name in manifest.artifacts}
        workflow.validate_plan_manifest(
            manifest,
            [criterion.id for criterion in contract.acceptance_criteria],
            expected_profile=profile,
            expected_ticket_sha256=state.ticket_sha256,
            ticket_contract_path=contract_path,
            artifact_paths=artifact_paths,
        )
        if manifest.ticket_id != ticket_id or manifest.change_id != change_id or state.profile != manifest.profile:
            raise ValueError("Execution state does not match the current plan")
        if repair:
            if not state.repair_pack_path:
                raise ValueError("Execution state has no RepairPack")
            pack = workflow.load_model(_project_path(state.repair_pack_path), RepairPack)
            workflow.validate_repair_pack(
                pack,
                expected_plan_sha256=state.plan_sha256,
                expected_ticket_id=ticket_id,
                expected_change_id=change_id,
            )
        return contract, manifest, contract_path, plan_path
    except (OSError, ValueError) as error:
        state.phase = "blocked"
        state.phase_usage["blocked_reason"] = str(error)
        return None


def _write_gate_evidence(change_id: str, attempt: int, gate: GateRun) -> Path:
    path = workflow.repair_pack_path(change_id, attempt).with_name(
        f"{gate.name}-{gate.evidence_id or 'evidence'}.log"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(gate.output, encoding="utf-8")
    return path


def _repair_scope(change_id: str, gate: GateRun) -> list[str]:
    diagnosis = (
        diagnose_integration_failure(gate.output)
        if gate.name == "integration"
        else diagnose_gate_failure(gate.name, gate.output)
    )
    scope = diagnosis.get("repairScope")
    if isinstance(scope, list) and scope and all(isinstance(path, str) for path in scope):
        return [path.replace("<change>", change_id) for path in scope]
    defaults = {
        "python": ["crewai/src"],
        "openspec": [f"openspec/changes/{change_id}"],
        "browser_testing": ["apps", "crewai", "packages"],
        "reviewer": ["apps", "crewai", "packages", "openspec"],
    }
    return defaults.get(gate.name, ["apps", "crewai", "packages", "openspec"])


def _repair_budget(gate: GateRun) -> str:
    return gate.failure_kind


def _block(state: ExecutionState, error: Exception | str) -> ExecutionState:
    state.phase = "blocked"
    state.phase_usage["blocked_reason"] = str(error)
    return state


def _save_repair_pack(
    change_id: str,
    state: ExecutionState,
    manifest: PlanManifest,
    plan_path: Path,
    phase: str,
    gate: GateRun,
) -> ExecutionState:
    attempt = _attempt(state)
    evidence_path = _write_gate_evidence(change_id, attempt, gate)
    pack = workflow.build_repair_pack(
        manifest=manifest,
        plan_path=plan_path,
        phase=phase,  # type: ignore[arg-type]
        gate=gate,
        evidence_path=evidence_path,
        repair_hint=gate.output,
        repair_scope=_repair_scope(change_id, gate),
    )
    path = workflow.repair_pack_path(change_id, attempt)
    workflow.save_model(path, pack)
    state.repair_pack_path = _relative(path)
    state.phase_usage["pending_repair_budget"] = _repair_budget(gate)
    state.last_attempt = attempt + 1
    state.phase = "implementing"
    return state


def run_planning(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    try:
        attempt = _attempt(state)
        ticket_sha256 = state.ticket_sha256 or current_ticket_sha256(ticket_id)
        analyst = kickoff_role(
            "analyst",
            inputs={
                "ticket_id": ticket_id,
                "change_id": change_id,
                "ticket_sha256": ticket_sha256,
            },
        )
        _record_usage(state, "analyst", analyst)
        contract = _as_model(analyst, TicketContract)
        if (contract.ticket_id, contract.change_id, contract.ticket_sha256) != (ticket_id, change_id, ticket_sha256):
            raise ValueError("TicketContract does not match the current ticket")
        contract_path = workflow.ticket_contract_path(change_id, attempt)
        workflow.save_model(contract_path, contract)

        plan_path = workflow.plan_manifest_path(change_id, attempt)
        architect = kickoff_role(
            "architect",
            inputs={
                "ticket_contract_path": _relative(contract_path),
                "plan_manifest_path": _relative(plan_path),
                "ticket_id": ticket_id,
                "change_id": change_id,
                "ticket_sha256": ticket_sha256,
                "ticket_contract_sha256": workflow.file_sha256(contract_path),
                "base_gates": ",".join(workflow.BASE_GATES),
            },
        )
        _record_usage(state, "architect", architect)
        manifest = _as_model(architect, PlanManifest)
        profile = _selected_profile(change_id)
        artifact_paths = {name: active_change(change_id) / name for name in manifest.artifacts}
        workflow.validate_plan_manifest(
            manifest,
            [criterion.id for criterion in contract.acceptance_criteria],
            expected_profile=profile,  # type: ignore[arg-type]
            expected_ticket_sha256=ticket_sha256,
            ticket_contract_path=contract_path,
            artifact_paths=artifact_paths,
        )
        workflow.save_model(plan_path, manifest)
        preflight = _run_gate("openspec", change_id)
        if not preflight.passed:
            state.phase = "blocked"
            state.phase_usage["blocked_reason"] = preflight.output
            return state
        state.ticket_sha256 = ticket_sha256
        state.ticket_contract_path = _relative(contract_path)
        state.plan_manifest_path = _relative(plan_path)
        state.plan_sha256 = workflow.file_sha256(plan_path)
        state.profile = manifest.profile
        state.phase = "implementing"
        return state
    except (OSError, ValueError, KeyError) as error:
        state.phase = "blocked"
        state.phase_usage["blocked_reason"] = str(error)
        return state


def run_programmer(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    previous_scope = os.environ.get("CREW_REPAIR_SCOPE")
    try:
        contracts = _current_contracts(ticket_id, change_id, state, repair=bool(state.repair_pack_path))
        if not contracts:
            return state
        _, _, _, plan_path = contracts
        if state.repair_pack_path:
            budget = state.phase_usage.get("pending_repair_budget", "ticket")
            if budget not in {"ticket", "infrastructure"}:
                raise ValueError("Execution state has an invalid repair budget")
            attempts = state.phase_usage.setdefault("repair_attempts", {"ticket": 0, "infrastructure": 0})
            if not isinstance(attempts, dict) or not isinstance(attempts.get(budget, 0), int):
                raise ValueError("Execution state has invalid repair attempts")
            maximum = int(os.environ.get(
                "MAX_INFRASTRUCTURE_ATTEMPTS" if budget == "infrastructure" else "MAX_TICKET_ATTEMPTS",
                "2" if budget == "infrastructure" else "3",
            ))
            if attempts[budget] >= maximum:
                return _block(state, f"Se alcanzaron {maximum} intentos de reparación {budget}.")
            attempts[budget] += 1
            pack = workflow.load_model(_project_path(state.repair_pack_path), RepairPack)
            if not pack.repair_scope:
                raise ValueError("RepairPack has no allowed repair scope")
            os.environ["CREW_REPAIR_SCOPE"] = json.dumps(pack.repair_scope)
        else:
            os.environ.pop("CREW_REPAIR_SCOPE", None)
        output = kickoff_role(
            "programmer",
            inputs={
                "plan_manifest_path": _relative(plan_path),
                "repair_pack_path": state.repair_pack_path or "NONE",
            },
        )
        _record_usage(state, "programmer", output)
        manifest = workflow.load_model(plan_path, PlanManifest)
        completion = workflow.build_task_completion(
            manifest,
            plan_path,
            active_change(change_id) / "tasks.md",
            _task_completion_evidence(manifest, state, plan_path),
        )
        completion_path = workflow.task_completion_path(change_id, _attempt(state))
        workflow.save_model(completion_path, completion)
        state.task_completion_path = _relative(completion_path)
        state.phase = "verifying"
        return state
    except Exception as error:
        return _block(state, error)
    finally:
        if previous_scope is None:
            os.environ.pop("CREW_REPAIR_SCOPE", None)
        else:
            os.environ["CREW_REPAIR_SCOPE"] = previous_scope


def _gate_evidence_records(change_id: str, state: ExecutionState, gates: list[GateRun]) -> list[dict[str, object]]:
    attempt = _attempt(state)
    records = []
    for gate in gates:
        if not gate.evidence_id:
            raise ValueError(f"Gate {gate.name} has no evidence ID")
        path = _write_gate_evidence(change_id, attempt, gate)
        records.append(
            {
                "name": gate.name,
                "passed": gate.passed,
                "evidence_id": gate.evidence_id,
                "evidence_path": _relative(path),
                "evidence_sha256": workflow.file_sha256(path),
            }
        )
    return records


def run_verification(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    contracts = _current_contracts(ticket_id, change_id, state)
    if not contracts:
        return state
    _, manifest, _, plan_path = contracts
    try:
        if not state.task_completion_path:
            raise ValueError("Execution state has no TaskCompletion")
        workflow.validate_task_completion(
            workflow.load_model(_project_path(state.task_completion_path), TaskCompletion),
            manifest,
            plan_path,
            active_change(change_id) / "tasks.md",
        )
    except (OSError, ValueError) as error:
        return _block(state, error)
    gates = run_base_gates(ticket_id, change_id)
    if tuple(gate.name for gate in gates) != workflow.BASE_GATES:
        return _block(state, "Base gate results do not match the immutable gate list")
    try:
        state.phase_usage["gate_runs"] = _gate_evidence_records(change_id, state, gates)
    except (OSError, ValueError) as error:
        return _block(state, error)
    failed = next((gate for gate in gates if not gate.passed), None)
    if failed:
        return _save_repair_pack(change_id, state, manifest, plan_path, "verifying", failed)
    if manifest.profile in {"browser", "browser_operational"}:
        state.phase = "browser_testing"
        return state
    browser_path = workflow.browser_result_path(change_id, _attempt(state))
    workflow.save_model(
        browser_path,
        TesterResult(status="skipped", summary="Browser testing is not required by the profile."),
    )
    state.browser_result_path = _relative(browser_path)
    state.phase = "reviewing"
    return state


def run_browser_testing(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    try:
        contracts = _current_contracts(ticket_id, change_id, state)
        if not contracts:
            return state
        _, manifest, _, plan_path = contracts
        path = workflow.browser_result_path(change_id, _attempt(state))
        if manifest.profile not in {"browser", "browser_operational"}:
            workflow.save_model(path, TesterResult(status="skipped", summary="Browser testing is not required by the profile."))
            state.browser_result_path = _relative(path)
            state.phase = "reviewing"
            return state
        output = kickoff_role(
            "tester",
            inputs={
                "verification_profile_path": _relative(active_change(change_id) / "design.md"),
                "scenario_paths": "NONE",
            },
        )
        _record_usage(state, "tester", output)
        result = _as_model(output, TesterResult)
        workflow.save_model(path, result)
        state.browser_result_path = _relative(path)
        if result.status == "passed":
            state.phase = "reviewing"
            return state
        return _save_repair_pack(
            change_id,
            state,
            manifest,
            plan_path,
            "browser_testing",
            GateRun("browser_testing", False, f"browser-{_attempt(state)}", result.summary),
        )
    except Exception as error:
        return _block(state, error)


def _changed_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only"], cwd=workflow.PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    return [workflow.PROJECT_ROOT / name for name in result.stdout.splitlines() if (workflow.PROJECT_ROOT / name).is_file()]


def _diff_summary() -> str:
    result = subprocess.run(
        ["git", "diff", "--stat"], cwd=workflow.PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "No changes."


def _gate_runs_from_state(state: ExecutionState) -> list[GateRun]:
    records = state.phase_usage.get("gate_runs")
    if not isinstance(records, list):
        raise ValueError("Execution state has no base gate evidence")
    runs = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Execution state has invalid base gate evidence")
        path = _project_path(str(record.get("evidence_path", "")))
        expected_hash = record.get("evidence_sha256")
        if not isinstance(expected_hash, str) or not path.is_file() or workflow.file_sha256(path) != expected_hash:
            raise ValueError("Execution state base gate evidence is stale")
        runs.append(GateRun(
            str(record.get("name", "")),
            record.get("passed") is True,
            record.get("evidence_id") if isinstance(record.get("evidence_id"), str) else None,
            path.read_text(encoding="utf-8"),
        ))
    if tuple(run.name for run in runs) != workflow.BASE_GATES:
        raise ValueError("Execution state base gate evidence is stale")
    return runs


def _gate_evidence_from_state(state: ExecutionState) -> dict[str, dict[str, str]]:
    records = state.phase_usage.get("gate_runs")
    if not isinstance(records, list):
        raise ValueError("Execution state has no base gate evidence")
    evidence = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Execution state has invalid base gate evidence")
        name = record.get("name")
        evidence_id = record.get("evidence_id")
        path = record.get("evidence_path")
        digest = record.get("evidence_sha256")
        if not all(isinstance(value, str) for value in (name, evidence_id, path, digest)):
            raise ValueError("Execution state has invalid base gate evidence")
        evidence[name] = {"evidence_id": evidence_id, "path": path, "sha256": digest}
    if set(evidence) != set(workflow.BASE_GATES):
        raise ValueError("Execution state has invalid base gate evidence")
    return evidence


def _operational_evidence(manifest: PlanManifest, modified_paths: list[Path]) -> dict[str, list[Path]]:
    if manifest.profile not in {"operational", "browser_operational"}:
        return {}
    change = active_change(manifest.change_id).resolve()
    evidence_paths = [path for path in modified_paths if not path.resolve().is_relative_to(change)]
    return {criterion: evidence_paths for criterion in manifest.acceptance_map}


def _task_completion_evidence(
    manifest: PlanManifest,
    state: ExecutionState,
    plan_path: Path,
) -> dict[str, list[Path]]:
    change = active_change(manifest.change_id).resolve()
    evidence_paths = [
        path
        for path in _changed_paths()
        if not path.resolve().is_relative_to(change)
    ]
    if state.task_completion_path:
        previous = workflow.load_model(
            _project_path(state.task_completion_path), TaskCompletion
        )
        workflow.validate_task_completion(
            previous,
            manifest,
            plan_path,
            active_change(manifest.change_id) / "tasks.md",
        )
        for evidence in previous.acceptance_evidence.values():
            evidence_paths.extend(_project_path(path) for path in evidence)
    unique_paths = list(dict.fromkeys(path.resolve() for path in evidence_paths))
    return {criterion: unique_paths for criterion in manifest.acceptance_map}


def run_review(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    contracts = _current_contracts(ticket_id, change_id, state)
    if not contracts:
        return state
    _, manifest, contract_path, plan_path = contracts
    try:
        if not state.browser_result_path:
            raise ValueError("Execution state has no browser result")
        if not state.task_completion_path:
            raise ValueError("Execution state has no TaskCompletion")
        browser_path = _project_path(state.browser_result_path)
        task_completion_path = _project_path(state.task_completion_path)
        artifact_paths = {name: active_change(change_id) / name for name in manifest.artifacts}
        modified_paths = _changed_paths()
        pack = workflow.build_review_pack(
            manifest=manifest,
            ticket_contract_path=contract_path,
            plan_path=plan_path,
            artifact_paths=artifact_paths,
            modified_paths=modified_paths,
            gate_runs=_gate_runs_from_state(state),
            gate_evidence=_gate_evidence_from_state(state),
            browser_result_path=browser_path,
            task_completion_path=task_completion_path,
            incomplete_tasks=False,
            diff_summary=_diff_summary(),
            operational_evidence=_operational_evidence(manifest, modified_paths),
        )
        path = workflow.review_pack_path(change_id, _attempt(state))
        workflow.save_model(path, pack)
        workflow.validate_review_pack(pack, expected_plan_sha256=state.plan_sha256)
        state.review_pack_path = _relative(path)
        output = kickoff_role("reviewer", inputs={"review_pack_path": state.review_pack_path})
        _record_usage(state, "reviewer", output)
        verdict = _as_model(output, ReviewVerdict)
        if verdict.ticket_id != ticket_id or verdict.change_id != change_id:
            raise ValueError("ReviewVerdict does not match the current ticket")
        if verdict.status == "approved":
            state.phase = "approved"
            return state
        if verdict.status == "retryable_failure":
            return _save_repair_pack(
                change_id,
                state,
                manifest,
                plan_path,
                "reviewing",
                GateRun("reviewer", False, f"reviewer-{_attempt(state)}", verdict.summary),
            )
        state.phase = "blocked"
        return state
    except (OSError, ValueError, KeyError) as error:
        state.phase = "blocked"
        state.phase_usage["blocked_reason"] = str(error)
        return state


def advance_phase(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    had_current_plan = bool(state.ticket_contract_path or state.plan_manifest_path)
    state = _check_ticket(ticket_id, change_id, state)
    if had_current_plan and state.phase == "planning" and state.plan_manifest_path is None:
        return state
    if state.phase == "planning":
        return run_planning(ticket_id, change_id, state)
    if state.phase == "implementing":
        return run_programmer(ticket_id, change_id, state)
    if state.phase == "verifying":
        return run_verification(ticket_id, change_id, state)
    if state.phase == "browser_testing":
        return run_browser_testing(ticket_id, change_id, state)
    if state.phase == "reviewing":
        return run_review(ticket_id, change_id, state)
    return state


def run_ticket(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    previous_environment = {name: os.environ.get(name) for name in (
        "CREW_VERIFICATION_CHANGE_ID", "CREW_VERIFICATION_ATTEMPT", "CREW_TICKET_ID"
    )}
    try:
        for _ in range(20):
            state = _check_ticket(ticket_id, change_id, state)
            if state.phase in {"approved", "blocked"}:
                break
            os.environ["CREW_VERIFICATION_CHANGE_ID"] = change_id
            os.environ["CREW_VERIFICATION_ATTEMPT"] = str(_attempt(state))
            os.environ["CREW_TICKET_ID"] = ticket_id
            if state.phase == "planning" and not state.ticket_contract_path:
                state = run_planning(ticket_id, change_id, state)
            else:
                state = advance_phase(ticket_id, change_id, state)
            workflow.save_execution(ticket_id, state)
        else:
            state.phase = "blocked"
            state.phase_usage["blocked_reason"] = "Phase machine exceeded its dispatch limit"
    finally:
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        close_playwright_session()
        close_local_environment()
    workflow.save_execution(ticket_id, state)
    return state


def run() -> None:
    parser = argparse.ArgumentParser(prog="run_crew")
    parser.add_argument("ticket_id", nargs="?", help="Identificador del ticket de Linear")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--resume", action="store_true", help="Continúa la fase persistida")
    modes.add_argument("--replan", action="store_true", help="Invalida los contratos de planificación")
    args = parser.parse_args()
    ticket_id, change_id = normalize(args.ticket_id or input("Ticket: "))
    ensure_change(change_id)
    try:
        state = workflow.load_execution(ticket_id)
    except ValueError:
        state = ExecutionState(ticket_id=ticket_id, change_id=change_id)
    if args.replan:
        state.ticket_id = ticket_id
        state.change_id = change_id
        state = _reset_for_planning(state, current_ticket_sha256(ticket_id))
        workflow.save_execution(ticket_id, state)
    state = run_ticket(ticket_id, change_id, state)
    gate_statuses = {name: "skipped" for name in workflow.BASE_GATES}
    evidence = {}
    records = state.phase_usage.get("gate_runs")
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, dict):
                continue
            name = record.get("name")
            if name not in gate_statuses:
                continue
            gate_statuses[name] = "passed" if record.get("passed") is True else "failed"
            if isinstance(record.get("evidence_id"), str):
                evidence[name] = record["evidence_id"]
    playwright = "skipped"
    if state.browser_result_path:
        try:
            playwright = workflow.load_model(
                _project_path(state.browser_result_path), TesterResult
            ).status
        except ValueError:
            playwright = "failed"
    result = CrewResult(
        ticket_id=ticket_id,
        change_id=change_id,
        attempt=state.last_attempt,
        evidence=evidence,
        status="approved" if state.phase == "approved" else "blocked" if state.phase == "blocked" else "retryable_failure",
        summary=state.phase_usage.get("blocked_reason", f"Phase {state.phase}.") if isinstance(state.phase_usage.get("blocked_reason", f"Phase {state.phase}."), str) else f"Phase {state.phase}.",
        verification=VerificationResult(
            **gate_statuses,
            playwright=playwright,
        ),
    )
    workflow.save_model(active_change(change_id) / "result.json", result)
    print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    run()
