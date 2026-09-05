import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import crew.workflow as workflow
from crew.gates import GateRun
from crew.models import (
    AcceptanceCriterion,
    ExecutionState,
    PlanArtifactUnit,
    PlanDraft,
    PlanDraftSpec,
    PlanManifest,
    PlanOutline,
    PlanningCheckpoint,
    PlanUnitOutline,
    ProjectContextCatalog,
    ProjectContextSection,
    TesterResult as BrowserResult,
    TicketContract,
    canonical_model_sha256,
)


def ticket_contract(ticket_sha256: str = "a" * 64) -> TicketContract:
    return TicketContract(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256=ticket_sha256,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-001", text="Persist contracts."),
            AcceptanceCriterion(id="AC-002", text="Validate profiles."),
        ],
        objective="Persist phase contracts.",
        in_scope=["crewai"],
        constraints=["Use atomic JSON writes."],
        dependencies=[],
        ambiguities=[],
    )


def write_model(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(), encoding="utf-8")


def persisted_inputs(tmp_path: Path, profile="standard"):
    contract_path = tmp_path / "ticket-contract.json"
    artifact_paths = {
        "proposal.md": tmp_path / "proposal.md",
        "design.md": tmp_path / "design.md",
        "tasks.md": tmp_path / "tasks.md",
        "specs/crew-supervision/spec.md": (
            tmp_path / "specs/crew-supervision/spec.md"
        ),
    }
    for name, path in artifact_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    completion_source = tmp_path / "crewai/src/crew/implementation.py"
    completion_source.parent.mkdir(parents=True, exist_ok=True)
    completion_source.write_text("COMPLETION_EVIDENCE = True\n", encoding="utf-8")
    write_model(contract_path, ticket_contract())
    manifest = PlanManifest(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256="a" * 64,
        ticket_contract_sha256=workflow.file_sha256(contract_path),
        artifacts={
            name: workflow.file_sha256(path)
            for name, path in artifact_paths.items()
        },
        profile=profile,
        acceptance_map={"AC-001": ["2.1"], "AC-002": ["2.2"]},
    )
    plan_path = tmp_path / "plan-manifest.json"
    write_model(plan_path, manifest)
    completion_path = tmp_path / "task-completion.json"
    write_model(
        completion_path,
        workflow.build_task_completion(
            manifest,
            plan_path,
            artifact_paths["tasks.md"],
            {criterion: [completion_source] for criterion in manifest.acceptance_map},
        ),
    )
    return contract_path, plan_path, artifact_paths, manifest, completion_path


def plan_draft() -> PlanDraft:
    return PlanDraft(
        profile="standard",
        proposal="# Proposal\n",
        design="verification_profile: standard\n",
        tasks="# Tasks\n",
        specs=[
            PlanDraftSpec(
                capability="identity-registration",
                content="## ADDED Requirements\n\n### Requirement: Register identity\n\n#### Scenario: Valid email\n",
            )
        ],
        acceptance_map={"AC-001": ["T-001"]},
    )


def passed_gates() -> list[GateRun]:
    return [
        GateRun(name, True, f"{name}-evidence", "")
        for name in workflow.BASE_GATES
    ]


def test_plan_manifest_rejects_missing_unmapped_and_mismatched_criteria():
    manifest = PlanManifest(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256="a" * 64,
        ticket_contract_sha256="b" * 64,
        artifacts={
            "proposal.md": "c" * 64,
            "design.md": "c" * 64,
            "tasks.md": "c" * 64,
            "specs/crew-supervision/spec.md": "c" * 64,
        },
        profile="operational",
        acceptance_map={"AC-001": ["2.1"], "AC-003": ["2.3"]},
    )

    with pytest.raises(ValueError, match="AC-002"):
        workflow.validate_plan_manifest(
            manifest,
            ["AC-001", "AC-002"],
            expected_profile="operational",
        )

    manifest.acceptance_map = {"AC-001": ["2.1"], "AC-002": ["2.2"]}
    with pytest.raises(ValueError, match="profile"):
        workflow.validate_plan_manifest(
            manifest,
            ["AC-001", "AC-002"],
            expected_profile="browser",
        )


def test_write_plan_draft_replaces_stale_specs_and_retains_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    stale_spec = change / "specs/stale/spec.md"
    stale_spec.parent.mkdir(parents=True)
    stale_spec.write_text("stale", encoding="utf-8")
    evidence = change / "attempts/1/ticket-contract.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence", encoding="utf-8")

    paths = workflow.write_plan_draft("dev-40", 1, plan_draft())

    assert set(paths) == {
        "proposal.md",
        "design.md",
        "tasks.md",
        "specs/identity-registration/spec.md",
    }
    assert paths["proposal.md"].read_text(encoding="utf-8") == "# Proposal\n"
    assert paths["specs/identity-registration/spec.md"].is_file()
    assert not stale_spec.exists()
    assert evidence.read_text(encoding="utf-8") == "evidence"


def test_write_plan_draft_snapshots_the_previous_active_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    for name, content in {
        "proposal.md": "old proposal",
        "design.md": "old design",
        "tasks.md": "old tasks",
        "specs/old/spec.md": "old spec",
    }.items():
        path = change / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    workflow.write_plan_draft("dev-40", 2, plan_draft())

    snapshot = change / "attempts/2/previous-plan"
    assert (snapshot / "proposal.md").read_text(encoding="utf-8") == "old proposal"
    assert (snapshot / "specs/old/spec.md").read_text(encoding="utf-8") == "old spec"


def test_restore_plan_draft_restores_the_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    for name, content in {
        "proposal.md": "old proposal",
        "design.md": "verification_profile: standard\n",
        "tasks.md": "old tasks",
        "specs/old/spec.md": "old spec",
    }.items():
        path = change / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    workflow.write_plan_draft("dev-40", 2, plan_draft())
    workflow.restore_plan_draft("dev-40", 2)

    assert (change / "proposal.md").read_text(encoding="utf-8") == "old proposal"
    assert (change / "specs/old/spec.md").read_text(encoding="utf-8") == "old spec"
    assert not (change / "specs/identity-registration/spec.md").exists()


def test_write_plan_draft_preserves_the_active_plan_when_staging_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    proposal = change / "proposal.md"
    proposal.parent.mkdir(parents=True)
    proposal.write_text("old proposal", encoding="utf-8")

    def fail_staging(path, _content):
        if "plan-draft" in path.parts:
            raise OSError("disk full")

    monkeypatch.setattr(workflow, "_atomic_write", fail_staging)

    with pytest.raises(OSError, match="disk full"):
        workflow.write_plan_draft("dev-40", 2, plan_draft())

    assert proposal.read_text(encoding="utf-8") == "old proposal"


def test_write_plan_draft_recovers_an_interrupted_promotion_before_replanning(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    proposal = change / "proposal.md"
    proposal.parent.mkdir(parents=True)
    proposal.write_text("old proposal", encoding="utf-8")

    workflow.write_plan_draft("dev-40", 1, plan_draft())
    workflow.write_plan_draft("dev-40", 2, plan_draft())

    snapshot = change / "attempts/2/previous-plan/proposal.md"
    assert snapshot.read_text(encoding="utf-8") == "old proposal"


def test_plan_manifest_requires_a_ticket_contract_hash():
    with pytest.raises(ValidationError, match="ticket_contract_sha256"):
        PlanManifest(
            ticket_id="DEV-40",
            change_id="dev-40",
            ticket_sha256="a" * 64,
            artifacts={"proposal.md": "b" * 64},
            profile="operational",
            acceptance_map={"AC-001": ["2.1"]},
        )


def test_plan_manifest_rejects_stale_artifact_and_ticket_contract(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, _, artifact_paths, manifest, _ = persisted_inputs(tmp_path)

    artifact_paths["proposal.md"].write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact proposal.md is stale"):
        workflow.validate_plan_manifest(
            manifest,
            ["AC-001", "AC-002"],
            ticket_contract_path=contract_path,
            artifact_paths=artifact_paths,
        )

    artifact_paths["proposal.md"].write_text("proposal.md", encoding="utf-8")
    write_model(contract_path, ticket_contract(ticket_sha256="d" * 64))
    with pytest.raises(ValueError, match="ticket contract"):
        workflow.validate_plan_manifest(
            manifest,
            ["AC-001", "AC-002"],
            ticket_contract_path=contract_path,
            artifact_paths=artifact_paths,
        )


def test_artifact_paths_are_open_spec_attempt_scoped_and_reject_invalid_ids(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)

    assert workflow.ticket_contract_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/ticket-contract.json"
    )
    assert workflow.plan_manifest_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/plan-manifest.json"
    )
    assert workflow.repair_pack_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/repair-pack.json"
    )
    assert workflow.review_pack_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/review-pack.json"
    )
    assert workflow.browser_result_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/browser-result.json"
    )
    assert workflow.context_catalog_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/context-catalog.json"
    )
    assert workflow.planning_checkpoint_path("dev-40", 2) == (
        tmp_path / "openspec/changes/dev-40/attempts/2/planning-checkpoint.json"
    )

    for value in ("../other", "/tmp/other"):
        with pytest.raises(ValueError, match="change ID"):
            workflow.ticket_contract_path(value, 1)
        with pytest.raises(ValueError, match="ticket ID"):
            workflow.execution_path(value)


def test_planning_checkpoint_is_atomically_saved_and_reloaded(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    outline = PlanOutline(
        profile="standard",
        units=[
            PlanUnitOutline(artifact="proposal", objective="Propose", context_refs=[]),
            PlanUnitOutline(artifact="design", objective="Design", context_refs=[]),
            PlanUnitOutline(artifact="tasks", objective="Task", context_refs=[]),
            PlanUnitOutline(
                artifact="spec",
                capability="crew-supervision",
                objective="Specify",
                context_refs=[],
            ),
        ],
        acceptance_map={"AC-001": ["T-001"]},
    )
    unit = PlanArtifactUnit(artifact="proposal", content="proposal")
    catalog = ProjectContextCatalog(
        source_path="CONTEXT.md",
        source_sha256="b" * 64,
        sections=[
            ProjectContextSection(
                ref="context-001", heading="## Context", body="body", size=4
            )
        ],
    )
    checkpoint = PlanningCheckpoint(
        ticket_contract_sha256=canonical_model_sha256(ticket_contract()),
        context_catalog_sha256=canonical_model_sha256(catalog),
        outline_sha256=canonical_model_sha256(outline),
        outline=outline,
        units=[unit],
        unit_sha256={"proposal": canonical_model_sha256(unit)},
        invocation_status={
            "proposal": "completed",
            "design": "pending",
            "tasks": "pending",
            "spec:crew-supervision": "pending",
        },
    )
    replaced = []
    original_replace = workflow.os.replace
    monkeypatch.setattr(
        workflow.os,
        "replace",
        lambda source, target: replaced.append(target) or original_replace(source, target),
    )
    path = workflow.planning_checkpoint_path("dev-40", 3)

    workflow.save_model(path, checkpoint)

    assert replaced == [path]
    assert workflow.load_model(path, PlanningCheckpoint) == checkpoint


def planning_checkpoint_values():
    outline = PlanOutline(
        profile="standard",
        units=[
            PlanUnitOutline(artifact="proposal", objective="Propose", context_refs=[]),
            PlanUnitOutline(artifact="design", objective="Design", context_refs=[]),
            PlanUnitOutline(artifact="tasks", objective="Task", context_refs=[]),
            PlanUnitOutline(
                artifact="spec",
                capability="crew-supervision",
                objective="Specify",
                context_refs=[],
            ),
        ],
        acceptance_map={"AC-001": ["T-001"]},
    )
    return {
        "ticket_contract_sha256": "a" * 64,
        "context_catalog_sha256": "b" * 64,
        "outline_sha256": canonical_model_sha256(outline),
        "outline": outline,
        "invocation_status": {unit.unit_key: "pending" for unit in outline.units},
    }


def test_planning_checkpoint_bounds_length_retry_state_to_outline_units():
    values = planning_checkpoint_values()
    values["invocation_status"]["proposal"] = "failed"
    values["invocation_status"]["design"] = "failed"

    checkpoint = PlanningCheckpoint(
        **values,
        length_retry_status={"proposal": "pending", "design": "consumed"},
    )

    assert checkpoint.length_retry_status == {
        "proposal": "pending",
        "design": "consumed",
    }
    with pytest.raises(ValidationError, match="unknown unit"):
        PlanningCheckpoint(**values, length_retry_status={"unknown": "pending"})
    with pytest.raises(ValidationError, match="length_retry_status"):
        PlanningCheckpoint(**values, length_retry_status={"proposal": 2})


@pytest.mark.parametrize("invocation_status", [None, "pending"])
def test_planning_checkpoint_rejects_pending_length_retry_without_failed_status(
    invocation_status,
):
    values = planning_checkpoint_values()
    if invocation_status is None:
        values["invocation_status"].pop("proposal")
    else:
        values["invocation_status"]["proposal"] = invocation_status

    with pytest.raises(ValidationError, match="pending length retry"):
        PlanningCheckpoint(**values, length_retry_status={"proposal": "pending"})


def test_planning_checkpoint_rejects_pending_length_retry_for_stored_completed_unit():
    values = planning_checkpoint_values()
    unit = PlanArtifactUnit(artifact="proposal", content="proposal")
    values["units"] = [unit]
    values["unit_sha256"] = {"proposal": canonical_model_sha256(unit)}
    values["invocation_status"]["proposal"] = "completed"

    with pytest.raises(ValidationError, match="pending length retry"):
        PlanningCheckpoint(**values, length_retry_status={"proposal": "pending"})


@pytest.mark.parametrize("invocation_status", [None, "pending"])
def test_planning_checkpoint_rejects_consumed_length_retry_without_terminal_status(
    invocation_status,
):
    values = planning_checkpoint_values()
    if invocation_status is None:
        values["invocation_status"].pop("proposal")
    else:
        values["invocation_status"]["proposal"] = invocation_status

    with pytest.raises(ValidationError, match="consumed length retry"):
        PlanningCheckpoint(**values, length_retry_status={"proposal": "consumed"})


def test_planning_checkpoint_accepts_valid_length_retry_status_combinations():
    for retry_status, invocation_status, stored in [
        ("pending", "failed", False),
        ("consumed", "failed", False),
        ("consumed", "completed", True),
    ]:
        values = planning_checkpoint_values()
        values["invocation_status"]["proposal"] = invocation_status
        if stored:
            unit = PlanArtifactUnit(artifact="proposal", content="proposal")
            values["units"] = [unit]
            values["unit_sha256"] = {"proposal": canonical_model_sha256(unit)}

        checkpoint = PlanningCheckpoint(
            **values,
            length_retry_status={"proposal": retry_status},
        )

        assert checkpoint.length_retry_status == {"proposal": retry_status}


def test_save_execution_replaces_state_atomically_and_rejects_non_json_data(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    replaced = []
    original_replace = workflow.os.replace
    monkeypatch.setattr(
        workflow.os,
        "replace",
        lambda source, target: replaced.append(target) or original_replace(source, target),
    )

    workflow.save_execution("DEV-40", ExecutionState(ticket_id="DEV-40"))

    path = tmp_path / ".agent/crew/DEV-40/execution.json"
    assert replaced == [path]
    assert workflow.load_execution("DEV-40").phase == "planning"

    unsafe = ExecutionState.model_construct(
        ticket_id="DEV-40", phase_usage={"planning": object()}
    )
    with pytest.raises(ValueError, match="JSON"):
        workflow.save_execution("DEV-40", unsafe)


def test_execution_state_preserves_legacy_empty_response_retry_state_when_loaded():
    pending = ExecutionState.model_validate_json(
        '{"ticket_id":"DEV-40","planning_empty_response_retry_state":"pending","planning_empty_response_retry_target":"outline"}'
    )
    consumed = ExecutionState.model_validate_json(
        '{"ticket_id":"DEV-40","planning_empty_response_retry_state":"consumed","planning_empty_response_retry_target":"proposal"}'
    )

    assert pending.planning_empty_response_retry_state == "pending"
    assert pending.planning_empty_response_retry_target == "outline"
    assert consumed.planning_empty_response_retry_state == "consumed"
    assert consumed.planning_empty_response_retry_target == "proposal"


def test_execution_state_bounds_contract_output_retries_to_named_pending_or_consumed_targets():
    available = ExecutionState(ticket_id="DEV-40")
    pending = ExecutionState(
        ticket_id="DEV-40",
        contract_output_retry_state={"architect:artifact:proposal": "pending"},
    )
    consumed = ExecutionState(
        ticket_id="DEV-40",
        contract_output_retry_state={"reviewer": "consumed"},
    )

    assert available.contract_output_retry_state == {}
    assert pending.contract_output_retry_state == {
        "architect:artifact:proposal": "pending"
    }
    assert consumed.contract_output_retry_state == {"reviewer": "consumed"}
    with pytest.raises(ValidationError, match="contract output retry target"):
        ExecutionState(
            ticket_id="DEV-40", contract_output_retry_state={"": "pending"}
        )


def test_repair_pack_rejects_a_successful_gate_and_persists_failure_stage(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    _, plan_path, _, manifest, _ = persisted_inputs(tmp_path)
    evidence_path = tmp_path / "lint.log"
    evidence_path.write_text("the full command output", encoding="utf-8")

    with pytest.raises(ValueError, match="failed gate"):
        workflow.build_repair_pack(
            manifest=manifest,
            plan_path=plan_path,
            phase="verifying",
            gate=GateRun("lint", True, "evidence-1", ""),
            evidence_path=evidence_path,
            repair_hint="Fix lint.",
            repair_scope=["crewai/src/crew"],
        )

    pack = workflow.build_repair_pack(
        manifest=manifest,
        plan_path=plan_path,
        phase="verifying",
        gate=GateRun("lint", False, "evidence-1", "the full command output"),
        evidence_path=evidence_path,
        repair_hint="Fix lint.",
        repair_scope=["crewai/src/crew"],
    )

    assert pack.failure_stage == "lint"
    assert "the full command output" not in json.dumps(pack.model_dump(mode="json"))


def test_repair_pack_rejects_a_stale_plan_and_ticket_relationship(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    _, plan_path, _, manifest, _ = persisted_inputs(tmp_path)
    evidence_path = tmp_path / "lint.log"
    evidence_path.write_text("failure", encoding="utf-8")
    pack = workflow.build_repair_pack(
        manifest=manifest,
        plan_path=plan_path,
        phase="verifying",
        gate=GateRun("lint", False, "evidence-1", ""),
        evidence_path=evidence_path,
        repair_hint="Fix lint.",
        repair_scope=[],
    )

    with pytest.raises(ValueError, match="plan hash is stale"):
        workflow.validate_repair_pack(pack, expected_plan_sha256="f" * 64)
    with pytest.raises(ValueError, match="ticket ID"):
        workflow.validate_repair_pack(pack, expected_ticket_id="DEV-41")


def test_review_pack_rejects_failed_base_gate_before_persisting(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, plan_path, artifact_paths, manifest, completion_path = persisted_inputs(tmp_path)
    browser_path = tmp_path / "browser-result.json"
    write_model(browser_path, BrowserResult(status="skipped", summary="Not required."))

    gates = passed_gates()
    gates[2] = GateRun("test", False, "test-evidence", "failed")
    with pytest.raises(ValueError, match="test did not pass"):
        workflow.build_review_pack(
            manifest=manifest,
            ticket_contract_path=contract_path,
            plan_path=plan_path,
            artifact_paths=artifact_paths,
            modified_paths=[],
            gate_runs=gates,
            browser_result_path=browser_path,
            task_completion_path=completion_path,
            incomplete_tasks=False,
            diff_summary="Add contracts.",
        )

    pack = workflow.build_review_pack(
        manifest=manifest,
        ticket_contract_path=contract_path,
        plan_path=plan_path,
        artifact_paths=artifact_paths,
        modified_paths=[],
        gate_runs=passed_gates(),
        browser_result_path=browser_path,
        task_completion_path=completion_path,
        incomplete_tasks=False,
        diff_summary="Add contracts.",
    )
    corrupted = pack.model_copy(
        update={**pack.model_dump(), "gate_statuses": {**pack.gate_statuses, "test": "failed"}}
    )
    with pytest.raises(ValueError, match="test"):
        workflow.validate_review_pack(corrupted)


@pytest.mark.parametrize(
    ("profile", "browser_status", "case"),
    [
        ("standard", "skipped", "missing"),
        ("standard", "skipped", "empty"),
        ("standard", "skipped", "unmapped"),
        ("browser", "passed", "missing"),
        ("browser", "passed", "empty"),
        ("browser", "passed", "unmapped"),
    ],
)
def test_review_pack_rejects_malformed_completion_evidence(
    tmp_path, monkeypatch, profile, browser_status, case
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, plan_path, artifact_paths, manifest, completion_path = persisted_inputs(
        tmp_path, profile
    )
    completion = workflow.load_model(completion_path, workflow.TaskCompletion)
    completion_data = completion.model_dump()
    evidence_path = tmp_path / "crewai/src/crew/implementation.py"
    evidence = {
        evidence_path.relative_to(tmp_path).as_posix(): workflow.file_sha256(evidence_path)
    }
    completion_data["acceptance_evidence"] = {
        "missing": {},
        "empty": {"AC-001": {}, "AC-002": evidence},
        "unmapped": {"AC-001": evidence, "AC-002": evidence, "AC-003": evidence},
    }[case]
    write_model(
        completion_path,
        workflow.TaskCompletion.model_validate(completion_data),
    )
    browser_path = tmp_path / "browser-result.json"
    write_model(browser_path, BrowserResult(status=browser_status, summary="Complete."))

    with pytest.raises(ValueError, match="TaskCompletion evidence"):
        workflow.build_review_pack(
            manifest=manifest,
            ticket_contract_path=contract_path,
            plan_path=plan_path,
            artifact_paths=artifact_paths,
            modified_paths=[],
            gate_runs=passed_gates(),
            browser_result_path=browser_path,
            task_completion_path=completion_path,
            incomplete_tasks=False,
            diff_summary="Add contracts.",
        )


def test_review_pack_rejects_missing_and_stale_open_spec_references(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, plan_path, artifact_paths, manifest, completion_path = persisted_inputs(tmp_path)
    browser_path = tmp_path / "browser-result.json"
    write_model(browser_path, BrowserResult(status="skipped", summary="Not required."))

    with pytest.raises(ValueError, match="artifact paths"):
        workflow.build_review_pack(
            manifest=manifest,
            ticket_contract_path=contract_path,
            plan_path=plan_path,
            artifact_paths={},
            modified_paths=[],
            gate_runs=passed_gates(),
            browser_result_path=browser_path,
            task_completion_path=completion_path,
            incomplete_tasks=False,
            diff_summary="Add contracts.",
        )

    pack = workflow.build_review_pack(
        manifest=manifest,
        ticket_contract_path=contract_path,
        plan_path=plan_path,
        artifact_paths=artifact_paths,
        modified_paths=[],
        gate_runs=passed_gates(),
        browser_result_path=browser_path,
        task_completion_path=completion_path,
        incomplete_tasks=False,
        diff_summary="Add contracts.",
    )
    assert pack.artifact_paths == {
        name: path.relative_to(tmp_path).as_posix()
        for name, path in artifact_paths.items()
    }
    assert pack.referenced_files["proposal.md"] == workflow.file_sha256(
        artifact_paths["proposal.md"]
    )

    artifact_paths["proposal.md"].write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        workflow.validate_review_pack(pack)


def test_review_pack_rejects_mismatched_ticket_contract_and_browser_profile(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, plan_path, artifact_paths, manifest, completion_path = persisted_inputs(tmp_path, "browser")
    write_model(contract_path, ticket_contract(ticket_sha256="d" * 64))
    browser_path = tmp_path / "browser-result.json"
    write_model(browser_path, BrowserResult(status="skipped", summary="Not run."))

    with pytest.raises(ValueError, match="ticket contract"):
        workflow.build_review_pack(
            manifest=manifest,
            ticket_contract_path=contract_path,
            plan_path=plan_path,
            artifact_paths=artifact_paths,
            modified_paths=[],
            gate_runs=passed_gates(),
            browser_result_path=browser_path,
            task_completion_path=completion_path,
            incomplete_tasks=False,
            diff_summary="Add contracts.",
        )

    write_model(contract_path, ticket_contract())
    with pytest.raises(ValueError, match="browser result"):
        workflow.build_review_pack(
            manifest=manifest,
            ticket_contract_path=contract_path,
            plan_path=plan_path,
            artifact_paths=artifact_paths,
            modified_paths=[],
            gate_runs=passed_gates(),
            browser_result_path=browser_path,
            task_completion_path=completion_path,
            incomplete_tasks=False,
            diff_summary="Add contracts.",
        )


def test_plan_manifest_rejects_a_missing_active_open_spec_artifact(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, _, artifact_paths, manifest, _ = persisted_inputs(tmp_path)
    active_spec = tmp_path / "openspec/changes/dev-40/specs/extra/spec.md"
    active_spec.parent.mkdir(parents=True)
    active_spec.write_text("extra", encoding="utf-8")

    with pytest.raises(ValueError, match="specs/extra/spec.md"):
        workflow.validate_plan_manifest(
            manifest,
            ["AC-001", "AC-002"],
            ticket_contract_path=contract_path,
            artifact_paths=artifact_paths,
        )


def test_review_pack_rejects_tampered_manifest_required_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, plan_path, artifact_paths, manifest, completion_path = persisted_inputs(tmp_path)
    browser_path = tmp_path / "browser-result.json"
    write_model(browser_path, BrowserResult(status="skipped", summary="Not required."))
    pack = workflow.build_review_pack(
        manifest=manifest,
        ticket_contract_path=contract_path,
        plan_path=plan_path,
        artifact_paths=artifact_paths,
        modified_paths=[],
        gate_runs=passed_gates(),
        browser_result_path=browser_path,
        task_completion_path=completion_path,
        incomplete_tasks=False,
        diff_summary="Add contracts.",
    )

    without_artifacts = pack.model_copy(
        update={**pack.model_dump(), "artifacts": {}, "artifact_paths": {}}
    )
    with pytest.raises(ValueError, match="artifact"):
        workflow.validate_review_pack(without_artifacts)

    without_mapping = pack.model_copy(
        update={**pack.model_dump(), "acceptance_map": {"AC-001": ["2.1"]}}
    )
    with pytest.raises(ValueError, match="acceptance"):
        workflow.validate_review_pack(without_mapping)

    active_spec = tmp_path / "openspec/changes/dev-40/specs/extra/spec.md"
    active_spec.parent.mkdir(parents=True)
    active_spec.write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="specs/extra/spec.md"):
        workflow.validate_review_pack(pack)


def test_pack_validation_rejects_tampered_evidence_and_external_references(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    contract_path, plan_path, artifact_paths, manifest, completion_path = persisted_inputs(tmp_path)
    evidence_path = tmp_path / "lint.log"
    evidence_path.write_text("failed", encoding="utf-8")
    repair_pack = workflow.build_repair_pack(
        manifest=manifest,
        plan_path=plan_path,
        phase="verifying",
        gate=GateRun("lint", False, "lint-evidence", ""),
        evidence_path=evidence_path,
        repair_hint="Fix lint.",
        repair_scope=[],
    )
    browser_path = tmp_path / "browser-result.json"
    write_model(browser_path, BrowserResult(status="skipped", summary="Not required."))
    review_pack = workflow.build_review_pack(
        manifest=manifest,
        ticket_contract_path=contract_path,
        plan_path=plan_path,
        artifact_paths=artifact_paths,
        modified_paths=[],
        gate_runs=passed_gates(),
        browser_result_path=browser_path,
        task_completion_path=completion_path,
        incomplete_tasks=False,
        diff_summary="Add contracts.",
    )

    evidence_path.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        workflow.validate_repair_pack(repair_pack)
    completion_evidence_path = tmp_path / "crewai/src/crew/implementation.py"
    completion_evidence_path.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="TaskCompletion evidence is stale"):
        workflow.validate_review_pack(review_pack)
    evidence_path.write_text("failed", encoding="utf-8")
    without_evidence = repair_pack.model_copy(
        update={
            **repair_pack.model_dump(),
            "referenced_files": {
                key: value
                for key, value in repair_pack.referenced_files.items()
                if key != repair_pack.evidence_path
            },
        }
    )
    with pytest.raises(ValueError, match="evidence"):
        workflow.validate_repair_pack(without_evidence)

    outside_path = tmp_path.parent / "workflow-outside.txt"
    outside_path.write_text("outside", encoding="utf-8")
    for reference in (str(outside_path), "../workflow-outside.txt"):
        external_hash = workflow.file_sha256(outside_path)
        with pytest.raises(ValueError, match="outside|traversal"):
            workflow.validate_repair_pack(
                repair_pack.model_copy(
                    update={
                        **repair_pack.model_dump(),
                        "referenced_files": {
                            **repair_pack.referenced_files,
                            reference: external_hash,
                        },
                    }
                )
            )
        with pytest.raises(ValueError, match="outside|traversal"):
            workflow.validate_review_pack(
                review_pack.model_copy(
                    update={
                        **review_pack.model_dump(),
                        "referenced_files": {
                            **review_pack.referenced_files,
                            reference: external_hash,
                        },
                    }
                )
            )
