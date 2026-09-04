import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Mapping, TypeVar

from pydantic import BaseModel

from .gates import GateRun
from .models import (
    ExecutionState,
    GateEvidence,
    Phase,
    PlanManifest,
    PlanDraft,
    RepairPack,
    ReviewPack,
    TaskCompletion,
    TesterResult,
    TicketContract,
    VerificationProfile,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_GATES = ("python", "lint", "test", "build", "integration", "openspec")
ModelT = TypeVar("ModelT", bound=BaseModel)
CHANGE_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
TICKET_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")
PROFILE_PATTERN = re.compile(r"^(?:-\s+)?verification_profile:\s*(\S+)\s*$", re.MULTILINE)
VALID_PROFILES = {"standard", "browser", "operational", "browser_operational"}


def _attempt_directory(change_id: str, attempt: int) -> Path:
    _validate_change_id(change_id)
    if attempt < 1:
        raise ValueError("attempt must be at least 1")
    return PROJECT_ROOT / "openspec" / "changes" / change_id / "attempts" / str(attempt)


def ticket_contract_path(change_id: str, attempt: int) -> Path:
    return _attempt_directory(change_id, attempt) / "ticket-contract.json"


def plan_manifest_path(change_id: str, attempt: int) -> Path:
    return _attempt_directory(change_id, attempt) / "plan-manifest.json"


def task_completion_path(change_id: str, attempt: int) -> Path:
    return _attempt_directory(change_id, attempt) / "task-completion.json"


def repair_pack_path(change_id: str, attempt: int) -> Path:
    return _attempt_directory(change_id, attempt) / "repair-pack.json"


def review_pack_path(change_id: str, attempt: int) -> Path:
    return _attempt_directory(change_id, attempt) / "review-pack.json"


def browser_result_path(change_id: str, attempt: int) -> Path:
    return _attempt_directory(change_id, attempt) / "browser-result.json"


def execution_path(ticket_id: str) -> Path:
    _validate_ticket_id(ticket_id)
    return PROJECT_ROOT / ".agent" / "crew" / ticket_id / "execution.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_profile(change_id: str) -> str:
    _validate_change_id(change_id)
    design = PROJECT_ROOT / "openspec" / "changes" / change_id / "design.md"
    return profile_from_design(design.read_text(encoding="utf-8")) if design.is_file() else profile_from_design("")


def profile_from_design(content: str) -> str:
    profiles = PROFILE_PATTERN.findall(content)
    if len(profiles) != 1 or profiles[0] not in VALID_PROFILES:
        raise ValueError("OpenSpec design must have exactly one valid verification_profile")
    return profiles[0]


def write_plan_draft(change_id: str, attempt: int, draft: PlanDraft) -> dict[str, Path]:
    _validate_change_id(change_id)
    change = PROJECT_ROOT / "openspec" / "changes" / change_id
    previous = _attempt_directory(change_id, attempt) / "previous-plan"
    stage = _attempt_directory(change_id, attempt) / "plan-draft"
    _recover_plan_promotion(change)
    _snapshot_plan(change, previous)
    artifacts = {
        "proposal.md": draft.proposal,
        "design.md": draft.design,
        "tasks.md": draft.tasks,
        **{
            f"specs/{spec.capability}/spec.md": spec.content
            for spec in draft.specs
        },
    }
    shutil.rmtree(stage, ignore_errors=True)
    try:
        for name, content in artifacts.items():
            _atomic_write(stage / name, content)
        _atomic_write(_promotion_marker(change), str(attempt))
        _clear_active_plan(change)
        for name in artifacts:
            target = change / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage / name, target)
    except OSError:
        restore_plan_draft(change_id, attempt)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    paths = {name: change / name for name in artifacts}
    return paths


def restore_plan_draft(change_id: str, attempt: int) -> None:
    _validate_change_id(change_id)
    change = PROJECT_ROOT / "openspec" / "changes" / change_id
    previous = _attempt_directory(change_id, attempt) / "previous-plan"
    _clear_active_plan(change)
    for name in ("proposal.md", "design.md", "tasks.md"):
        source = previous / name
        if source.is_file():
            target = change / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    if (previous / "specs").is_dir():
        shutil.copytree(previous / "specs", change / "specs")
    _promotion_marker(change).unlink(missing_ok=True)


def complete_plan_promotion(change_id: str) -> None:
    _validate_change_id(change_id)
    _promotion_marker(PROJECT_ROOT / "openspec" / "changes" / change_id).unlink(missing_ok=True)


def _snapshot_plan(change: Path, previous: Path) -> None:
    shutil.rmtree(previous, ignore_errors=True)
    for name in ("proposal.md", "design.md", "tasks.md"):
        source = change / name
        if source.is_file():
            target = previous / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    if (change / "specs").is_dir():
        shutil.copytree(change / "specs", previous / "specs")


def _clear_active_plan(change: Path) -> None:
    for name in ("proposal.md", "design.md", "tasks.md"):
        (change / name).unlink(missing_ok=True)
    shutil.rmtree(change / "specs", ignore_errors=True)


def _promotion_marker(change: Path) -> Path:
    return change / ".plan-promotion"


def _recover_plan_promotion(change: Path) -> None:
    marker = _promotion_marker(change)
    if not marker.is_file():
        return
    try:
        attempt = int(marker.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ValueError("Invalid pending plan promotion") from error
    change_id = change.name
    restore_plan_draft(change_id, attempt)


def save_model(path: Path, model: BaseModel) -> None:
    try:
        payload = json.dumps(
            model.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("Model cannot be persisted as JSON") from error
    _atomic_write(path, payload + "\n")


def load_model(path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot load {model_type.__name__} from {path}") from error


def save_execution(ticket_id: str, state: ExecutionState) -> None:
    save_model(execution_path(ticket_id), state)


def load_execution(ticket_id: str) -> ExecutionState:
    return load_model(execution_path(ticket_id), ExecutionState)


def validate_plan_manifest(
    manifest: PlanManifest,
    criterion_ids: list[str],
    *,
    expected_profile: VerificationProfile | None = None,
    expected_ticket_sha256: str | None = None,
    ticket_contract_path: Path | None = None,
    artifact_paths: Mapping[str, Path] | None = None,
) -> None:
    if tuple(manifest.base_gates) != BASE_GATES:
        raise ValueError("PlanManifest base gates do not match the immutable gate list")
    if expected_profile is not None and manifest.profile != expected_profile:
        raise ValueError("PlanManifest profile does not match the selected profile")
    if (
        expected_ticket_sha256 is not None
        and manifest.ticket_sha256 != expected_ticket_sha256
    ):
        raise ValueError("PlanManifest ticket hash is stale")

    expected = set(criterion_ids)
    actual = set(manifest.acceptance_map)
    missing = sorted(expected - actual)
    unmapped = sorted(actual - expected)
    if missing:
        raise ValueError(f"PlanManifest is missing acceptance criteria: {', '.join(missing)}")
    if unmapped:
        raise ValueError(
            f"PlanManifest maps unknown acceptance criteria: {', '.join(unmapped)}"
        )
    empty = sorted(key for key, tasks in manifest.acceptance_map.items() if not tasks)
    if empty:
        raise ValueError(f"PlanManifest has criteria without tasks: {', '.join(empty)}")

    for artifact, digest in manifest.artifacts.items():
        if not _is_sha256(digest):
            raise ValueError(f"PlanManifest artifact {artifact} has an invalid hash")
    required_artifacts = _required_open_spec_artifacts(manifest.change_id)
    missing_artifacts = sorted(required_artifacts - set(manifest.artifacts))
    if missing_artifacts:
        raise ValueError(
            "PlanManifest is missing required artifacts: "
            + ", ".join(missing_artifacts)
        )
    if ticket_contract_path is not None:
        _validate_ticket_contract(manifest, ticket_contract_path)
    if artifact_paths is not None:
        missing_paths = sorted(set(manifest.artifacts) - set(artifact_paths))
        if missing_paths:
            raise ValueError(
                f"PlanManifest is missing artifact paths: {', '.join(missing_paths)}"
            )
        unexpected_paths = sorted(set(artifact_paths) - set(manifest.artifacts))
        if unexpected_paths:
            raise ValueError(
                f"PlanManifest has unmapped artifact paths: {', '.join(unexpected_paths)}"
            )
        for name, path in artifact_paths.items():
            expected_hash = manifest.artifacts.get(name)
            if expected_hash is None:
                raise ValueError(f"PlanManifest does not map artifact {name}")
            if file_sha256(_project_path(_relative(path))) != expected_hash:
                raise ValueError(f"PlanManifest artifact {name} is stale")


def build_task_completion(
    manifest: PlanManifest,
    plan_path: Path,
    tasks_path: Path,
    acceptance_evidence: Mapping[str, list[Path]],
) -> TaskCompletion:
    tasks_sha256 = file_sha256(tasks_path)
    if tasks_sha256 != manifest.artifacts.get("tasks.md"):
        raise ValueError("TaskCompletion tasks artifact is stale")
    return TaskCompletion(
        ticket_id=manifest.ticket_id,
        change_id=manifest.change_id,
        plan_path=_relative(plan_path),
        plan_sha256=file_sha256(plan_path),
        tasks_path=_relative(tasks_path),
        tasks_sha256=tasks_sha256,
        acceptance_evidence=_normalize_task_completion_evidence(
            manifest, acceptance_evidence
        ),
    )


def validate_task_completion(
    completion: TaskCompletion,
    manifest: PlanManifest,
    plan_path: Path,
    tasks_path: Path,
) -> None:
    if (
        completion.ticket_id != manifest.ticket_id
        or completion.change_id != manifest.change_id
        or completion.plan_path != _relative(plan_path)
        or completion.plan_sha256 != file_sha256(plan_path)
    ):
        raise ValueError("TaskCompletion plan relationship is stale")
    if (
        completion.tasks_path != _relative(tasks_path)
        or completion.tasks_sha256 != manifest.artifacts.get("tasks.md")
        or completion.tasks_sha256 != file_sha256(tasks_path)
    ):
        raise ValueError("TaskCompletion tasks artifact is stale")
    _validate_task_completion_evidence(completion, manifest)


def build_repair_pack(
    *,
    manifest: PlanManifest,
    plan_path: Path,
    phase: Phase,
    gate: GateRun,
    evidence_path: Path,
    repair_hint: str,
    repair_scope: list[str],
) -> RepairPack:
    if gate.passed:
        raise ValueError("RepairPack requires a failed gate")
    if not gate.evidence_id:
        raise ValueError("RepairPack requires a gate evidence ID")
    plan_sha256 = file_sha256(plan_path)
    evidence_sha256 = file_sha256(evidence_path)
    references = {
        _relative(plan_path): plan_sha256,
        _relative(evidence_path): evidence_sha256,
    }
    return RepairPack(
        ticket_id=manifest.ticket_id,
        change_id=manifest.change_id,
        phase=phase,
        failure_stage=gate.name,
        plan_sha256=plan_sha256,
        plan_path=_relative(plan_path),
        evidence_id=gate.evidence_id,
        evidence_path=_relative(evidence_path),
        evidence_sha256=evidence_sha256,
        repair_hint=repair_hint,
        repair_scope=repair_scope,
        referenced_files=references,
    )


def validate_repair_pack(
    pack: RepairPack,
    *,
    expected_plan_sha256: str | None = None,
    expected_ticket_id: str | None = None,
    expected_change_id: str | None = None,
) -> None:
    if expected_plan_sha256 is not None and pack.plan_sha256 != expected_plan_sha256:
        raise ValueError("RepairPack plan hash is stale")
    if expected_ticket_id is not None and pack.ticket_id != expected_ticket_id:
        raise ValueError("RepairPack ticket ID does not match")
    if expected_change_id is not None and pack.change_id != expected_change_id:
        raise ValueError("RepairPack change ID does not match")
    _validate_references(pack.referenced_files)
    if pack.referenced_files.get(pack.plan_path) != pack.plan_sha256:
        raise ValueError("RepairPack plan reference is stale")
    if pack.referenced_files.get(pack.evidence_path) != pack.evidence_sha256:
        raise ValueError("RepairPack evidence reference is stale")


def build_review_pack(
    *,
    manifest: PlanManifest,
    ticket_contract_path: Path,
    plan_path: Path,
    artifact_paths: Mapping[str, Path],
    modified_paths: list[Path],
    gate_runs: list[GateRun],
    gate_evidence: Mapping[str, Mapping[str, str]] | None = None,
    browser_result_path: Path,
    task_completion_path: Path,
    incomplete_tasks: bool,
    diff_summary: str,
    operational_evidence: Mapping[str, list[Path]] | None = None,
) -> ReviewPack:
    stored_manifest = load_model(plan_path, PlanManifest)
    if stored_manifest != manifest:
        raise ValueError("ReviewPack plan manifest does not match the persisted plan")
    _validate_ticket_contract(manifest, ticket_contract_path)
    validate_plan_manifest(
        manifest,
        [criterion.id for criterion in load_model(ticket_contract_path, TicketContract).acceptance_criteria],
        ticket_contract_path=ticket_contract_path,
        artifact_paths=artifact_paths,
    )

    gate_runs_by_name = {run.name: run for run in gate_runs}
    missing_gates = [gate for gate in BASE_GATES if not gate_runs_by_name.get(gate)]
    if missing_gates:
        raise ValueError(f"ReviewPack is missing gate evidence: {', '.join(missing_gates)}")
    for gate in BASE_GATES:
        run = gate_runs_by_name[gate]
        if not run.evidence_id:
            raise ValueError(f"ReviewPack is missing gate evidence: {gate}")
        if not run.passed:
            raise ValueError(f"ReviewPack gate {gate} did not pass")

    browser_result = load_model(browser_result_path, TesterResult)
    requires_browser = manifest.profile in {"browser", "browser_operational"}
    if requires_browser and browser_result.status != "passed":
        raise ValueError("ReviewPack browser result did not pass")
    if not requires_browser and browser_result.status != "skipped":
        raise ValueError("ReviewPack browser result must be skipped for this profile")
    task_completion = load_model(task_completion_path, TaskCompletion)
    validate_task_completion(
        task_completion,
        manifest,
        plan_path,
        artifact_paths["tasks.md"],
    )

    references = {
        _relative(ticket_contract_path): file_sha256(ticket_contract_path),
        _relative(plan_path): file_sha256(plan_path),
        _relative(browser_result_path): file_sha256(browser_result_path),
        _relative(task_completion_path): file_sha256(task_completion_path),
    }
    normalized_artifact_paths = {}
    for name, path in artifact_paths.items():
        relative_path = _relative(path)
        normalized_artifact_paths[name] = relative_path
        references[relative_path] = file_sha256(path)
    normalized_modified_paths = []
    for path in modified_paths:
        relative_path = _relative(path)
        normalized_modified_paths.append(relative_path)
        references[relative_path] = file_sha256(path)
    normalized_gate_evidence = {}
    for gate in BASE_GATES:
        run = gate_runs_by_name[gate]
        supplied = (gate_evidence or {}).get(gate)
        if supplied is None:
            path = plan_path.parent / f"gate-{gate}.log"
            _atomic_write(path, run.output)
            evidence_id = run.evidence_id
        else:
            evidence_id = supplied.get("evidence_id")
            path = _project_path(supplied.get("path", ""))
        if evidence_id != run.evidence_id:
            raise ValueError(f"ReviewPack gate evidence ID does not match {gate}")
        relative_path = _relative(path)
        digest = file_sha256(path)
        references[relative_path] = digest
        normalized_gate_evidence[gate] = GateEvidence(
            evidence_id=evidence_id,
            path=relative_path,
            sha256=digest,
        )
    normalized_operational_evidence = {}
    for criterion, paths in (operational_evidence or {}).items():
        normalized_paths = {}
        for path in paths:
            relative_path = _relative(path)
            digest = file_sha256(path)
            normalized_paths[relative_path] = digest
            references[relative_path] = digest
        normalized_operational_evidence[criterion] = normalized_paths

    return ReviewPack(
        ticket_id=manifest.ticket_id,
        change_id=manifest.change_id,
        ticket_sha256=manifest.ticket_sha256,
        ticket_contract_path=_relative(ticket_contract_path),
        ticket_contract_sha256=file_sha256(ticket_contract_path),
        plan_path=_relative(plan_path),
        plan_sha256=file_sha256(plan_path),
        profile=manifest.profile,
        acceptance_map=manifest.acceptance_map,
        artifacts=manifest.artifacts,
        incomplete_tasks=incomplete_tasks,
        task_completion_path=_relative(task_completion_path),
        task_completion_sha256=file_sha256(task_completion_path),
        modified_paths=normalized_modified_paths,
        diff_summary=diff_summary,
        gate_evidence_ids={
            name: gate_runs_by_name[name].evidence_id for name in BASE_GATES
        },
        gate_statuses={name: "passed" for name in BASE_GATES},
        gate_evidence=normalized_gate_evidence,
        browser_result_path=_relative(browser_result_path),
        browser_result_sha256=file_sha256(browser_result_path),
        artifact_paths=normalized_artifact_paths,
        operational_evidence=normalized_operational_evidence,
        referenced_files=references,
    )


def validate_review_pack(
    pack: ReviewPack, *, expected_plan_sha256: str | None = None
) -> None:
    if expected_plan_sha256 is not None and pack.plan_sha256 != expected_plan_sha256:
        raise ValueError("ReviewPack plan hash is stale")
    missing_gates = [
        gate
        for gate in BASE_GATES
        if not pack.gate_evidence_ids.get(gate)
        or pack.gate_statuses.get(gate) != "passed"
        or gate not in pack.gate_evidence
    ]
    if missing_gates:
        raise ValueError(f"ReviewPack has invalid gate evidence: {', '.join(missing_gates)}")
    _validate_references(pack.referenced_files)
    for gate in BASE_GATES:
        evidence = GateEvidence.model_validate(pack.gate_evidence[gate])
        if evidence.evidence_id != pack.gate_evidence_ids[gate]:
            raise ValueError(f"ReviewPack gate evidence ID is stale: {gate}")
        if pack.referenced_files.get(evidence.path) != evidence.sha256:
            raise ValueError(f"ReviewPack gate evidence is stale: {gate}")
    plan_path = _project_path(pack.plan_path)
    ticket_contract_path = _project_path(pack.ticket_contract_path)
    browser_result_path = _project_path(pack.browser_result_path)
    manifest = load_model(plan_path, PlanManifest)
    if pack.acceptance_map != manifest.acceptance_map:
        raise ValueError("ReviewPack acceptance mapping does not match the manifest")
    if pack.artifacts != manifest.artifacts:
        raise ValueError("ReviewPack artifacts do not match the manifest")
    manifest_artifact_paths = {
        name: _project_path(path)
        for name, path in pack.artifact_paths.items()
    }
    task_completion_path = _project_path(pack.task_completion_path)
    if pack.referenced_files.get(pack.task_completion_path) != pack.task_completion_sha256:
        raise ValueError("ReviewPack task completion is stale")
    if file_sha256(task_completion_path) != pack.task_completion_sha256:
        raise ValueError("ReviewPack task completion is stale")
    validate_task_completion(
        load_model(task_completion_path, TaskCompletion),
        manifest,
        plan_path,
        manifest_artifact_paths["tasks.md"],
    )
    ticket_contract = load_model(ticket_contract_path, TicketContract)
    validate_plan_manifest(
        manifest,
        [criterion.id for criterion in ticket_contract.acceptance_criteria],
        ticket_contract_path=ticket_contract_path,
        artifact_paths=manifest_artifact_paths,
    )
    if set(pack.artifacts) != set(pack.artifact_paths):
        raise ValueError("ReviewPack artifact paths do not match artifact hashes")
    for name, relative_path in pack.artifact_paths.items():
        artifact_hash = pack.artifacts[name]
        if pack.referenced_files.get(relative_path) != artifact_hash:
            raise ValueError(f"ReviewPack artifact {name} is stale")
    if pack.referenced_files.get(pack.browser_result_path) != pack.browser_result_sha256:
        raise ValueError("ReviewPack browser result is stale")
    if pack.referenced_files.get(pack.ticket_contract_path) != pack.ticket_contract_sha256:
        raise ValueError("ReviewPack ticket contract is stale")
    if pack.referenced_files.get(pack.plan_path) != pack.plan_sha256:
        raise ValueError("ReviewPack plan is stale")

    if (
        manifest.ticket_id != pack.ticket_id
        or manifest.change_id != pack.change_id
        or manifest.ticket_sha256 != pack.ticket_sha256
        or manifest.ticket_contract_sha256 != pack.ticket_contract_sha256
        or manifest.profile != pack.profile
    ):
        raise ValueError("ReviewPack plan relationship is stale")
    _validate_ticket_contract(manifest, ticket_contract_path)

    if pack.profile in {"operational", "browser_operational"}:
        expected_criteria = set(manifest.acceptance_map)
        actual_criteria = set(pack.operational_evidence)
        missing_criteria = sorted(expected_criteria - actual_criteria)
        unexpected_criteria = sorted(actual_criteria - expected_criteria)
        if missing_criteria or unexpected_criteria:
            details = ", ".join(missing_criteria or unexpected_criteria)
            raise ValueError(f"ReviewPack operational evidence is incomplete: {details}")
        change_root = PROJECT_ROOT / "openspec" / "changes" / pack.change_id
        for criterion, evidence in pack.operational_evidence.items():
            if not evidence:
                raise ValueError(f"ReviewPack operational evidence is empty: {criterion}")
            for relative_path, digest in evidence.items():
                path = _project_path(relative_path)
                if path.is_relative_to(change_root.resolve()):
                    raise ValueError(
                        f"ReviewPack operational evidence must be a source, test, or document: {criterion}"
                    )
                if pack.referenced_files.get(relative_path) != digest:
                    raise ValueError(f"ReviewPack operational evidence is stale: {criterion}")

    browser_result = load_model(browser_result_path, TesterResult)
    requires_browser = pack.profile in {"browser", "browser_operational"}
    if requires_browser and browser_result.status != "passed":
        raise ValueError("ReviewPack browser result did not pass")
    if not requires_browser and browser_result.status != "skipped":
        raise ValueError("ReviewPack browser result must be skipped for this profile")


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"Referenced path is outside the project: {path}") from error


def _validate_ticket_contract(manifest: PlanManifest, path: Path) -> TicketContract:
    path = _project_path(_relative(path))
    if file_sha256(path) != manifest.ticket_contract_sha256:
        raise ValueError("PlanManifest ticket contract hash is stale")
    contract = load_model(path, TicketContract)
    if (
        contract.ticket_id != manifest.ticket_id
        or contract.change_id != manifest.change_id
        or contract.ticket_sha256 != manifest.ticket_sha256
    ):
        raise ValueError("PlanManifest ticket contract does not match the manifest")
    return contract


def _validate_references(references: Mapping[str, str]) -> None:
    for relative_path, expected_hash in references.items():
        path = _project_path(relative_path)
        if not _is_sha256(expected_hash) or not path.is_file():
            raise ValueError(f"Referenced file is stale: {relative_path}")
        if file_sha256(path) != expected_hash:
            raise ValueError(f"Referenced file is stale: {relative_path}")


def _normalize_task_completion_evidence(
    manifest: PlanManifest,
    evidence: Mapping[str, list[Path]],
) -> dict[str, dict[str, str]]:
    expected_criteria = set(manifest.acceptance_map)
    actual_criteria = set(evidence)
    missing_criteria = sorted(expected_criteria - actual_criteria)
    unexpected_criteria = sorted(actual_criteria - expected_criteria)
    if missing_criteria or unexpected_criteria:
        details = ", ".join(missing_criteria or unexpected_criteria)
        raise ValueError(f"TaskCompletion evidence is incomplete: {details}")

    change_root = PROJECT_ROOT / "openspec" / "changes" / manifest.change_id
    normalized = {}
    for criterion, paths in evidence.items():
        if not paths:
            raise ValueError(f"TaskCompletion evidence is empty: {criterion}")
        criterion_evidence = {}
        for path in paths:
            relative_path = _relative(path)
            resolved_path = _project_path(relative_path)
            if resolved_path.is_relative_to(change_root.resolve()):
                raise ValueError(
                    "TaskCompletion evidence must be a source, test, or document: "
                    f"{criterion}"
                )
            criterion_evidence[relative_path] = file_sha256(resolved_path)
        normalized[criterion] = criterion_evidence
    return normalized


def _validate_task_completion_evidence(
    completion: TaskCompletion,
    manifest: PlanManifest,
) -> None:
    expected_criteria = set(manifest.acceptance_map)
    actual_criteria = set(completion.acceptance_evidence)
    missing_criteria = sorted(expected_criteria - actual_criteria)
    unexpected_criteria = sorted(actual_criteria - expected_criteria)
    if missing_criteria or unexpected_criteria:
        details = ", ".join(missing_criteria or unexpected_criteria)
        raise ValueError(f"TaskCompletion evidence is incomplete: {details}")

    change_root = PROJECT_ROOT / "openspec" / "changes" / manifest.change_id
    for criterion, evidence in completion.acceptance_evidence.items():
        if not evidence:
            raise ValueError(f"TaskCompletion evidence is empty: {criterion}")
        for relative_path, digest in evidence.items():
            path = _project_path(relative_path)
            if path.is_relative_to(change_root.resolve()):
                raise ValueError(
                    "TaskCompletion evidence must be a source, test, or document: "
                    f"{criterion}"
                )
            if (
                not _is_sha256(digest)
                or not path.is_file()
                or file_sha256(path) != digest
            ):
                raise ValueError(f"TaskCompletion evidence is stale: {criterion}")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _required_open_spec_artifacts(change_id: str) -> set[str]:
    change = PROJECT_ROOT / "openspec" / "changes" / change_id
    required = {"proposal.md", "design.md", "tasks.md"}
    specs = change / "specs"
    if specs.is_dir():
        required.update(path.relative_to(change).as_posix() for path in specs.rglob("*.md"))
    return required


def _project_path(reference: str) -> Path:
    candidate = Path(reference)
    if candidate.is_absolute():
        raise ValueError(f"Referenced path is outside project: {reference}")
    if ".." in candidate.parts:
        raise ValueError(f"Referenced path traversal is not allowed: {reference}")
    resolved = (PROJECT_ROOT / candidate).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"Referenced path is outside project: {reference}") from error
    return resolved


def _validate_change_id(change_id: str) -> None:
    if not CHANGE_ID.fullmatch(change_id):
        raise ValueError("Invalid change ID")


def _validate_ticket_id(ticket_id: str) -> None:
    if not TICKET_ID.fullmatch(ticket_id):
        raise ValueError("Invalid ticket ID")
