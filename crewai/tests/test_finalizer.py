from pathlib import Path

import pytest

import crew.finalizer as finalizer
import crew.workflow as workflow
from crew.gates import GateRun
from crew.models import (
    AcceptanceCriterion,
    CrewResult,
    ExecutionState,
    PlanManifest,
    TesterResult,
    TicketContract,
    VerificationResult,
)


def _write_current_review_artifacts(
    tmp_path,
    monkeypatch,
    *,
    design_profile="operational",
    persisted_profile="operational",
    include_operational_evidence=True,
    review_plan_sha256=None,
):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    artifacts = {
        "proposal.md": change / "proposal.md",
        "design.md": change / "design.md",
        "tasks.md": change / "tasks.md",
        "specs/crew-supervision/spec.md": change / "specs/crew-supervision/spec.md",
    }
    for name, path in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"verification_profile: {design_profile}" if name == "design.md" else name,
            encoding="utf-8",
        )

    contract = TicketContract(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256="a" * 64,
        acceptance_criteria=[AcceptanceCriterion(id="AC-001", text="Complete Task 5.")],
        objective="Complete Task 5.",
        in_scope=["crewai"],
        constraints=[],
        dependencies=[],
        ambiguities=[],
    )
    contract_path = workflow.ticket_contract_path("dev-40", 1)
    workflow.save_model(contract_path, contract)
    manifest = PlanManifest(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256=contract.ticket_sha256,
        ticket_contract_sha256=workflow.file_sha256(contract_path),
        artifacts={name: workflow.file_sha256(path) for name, path in artifacts.items()},
        profile=persisted_profile,
        acceptance_map={"AC-001": ["5.1"]},
    )
    plan_path = workflow.plan_manifest_path("dev-40", 1)
    workflow.save_model(plan_path, manifest)
    operational_source = tmp_path / "apps/api/src/operational.py"
    operational_source.parent.mkdir(parents=True, exist_ok=True)
    operational_source.write_text("OPERATIONS_READY = True\n", encoding="utf-8")
    completion_path = workflow.task_completion_path("dev-40", 1)
    workflow.save_model(
        completion_path,
        workflow.build_task_completion(
            manifest,
            plan_path,
            artifacts["tasks.md"],
            {criterion: [operational_source] for criterion in manifest.acceptance_map},
        ),
    )
    browser_path = workflow.browser_result_path("dev-40", 1)
    workflow.save_model(browser_path, TesterResult(status="skipped", summary="Not required."))
    gates = []
    gate_evidence = {}
    for name in workflow.BASE_GATES:
        evidence = change / "attempts/1" / f"{name}.log"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(f"{name} passed", encoding="utf-8")
        gates.append(GateRun(name, True, f"{name}-evidence", evidence.read_text(encoding="utf-8")))
        gate_evidence[name] = {
            "evidence_id": f"{name}-evidence",
            "path": evidence.relative_to(tmp_path).as_posix(),
            "sha256": workflow.file_sha256(evidence),
        }
    review = workflow.build_review_pack(
        manifest=manifest,
        ticket_contract_path=contract_path,
        plan_path=plan_path,
        artifact_paths=artifacts,
        modified_paths=[],
        gate_runs=gates,
        gate_evidence=gate_evidence,
        browser_result_path=browser_path,
        task_completion_path=completion_path,
        incomplete_tasks=False,
        diff_summary="No changes.",
        operational_evidence={"AC-001": [operational_source]}
        if include_operational_evidence
        else {},
    )
    if review_plan_sha256:
        review = review.model_copy(update={"plan_sha256": review_plan_sha256})
    review_path = workflow.review_pack_path("dev-40", 1)
    workflow.save_model(review_path, review)
    workflow.save_execution(
        "DEV-40",
        ExecutionState(
            ticket_id="DEV-40",
            change_id="dev-40",
            phase="approved",
            ticket_sha256=contract.ticket_sha256,
            plan_sha256=workflow.file_sha256(plan_path),
            profile=persisted_profile,
            last_attempt=1,
            ticket_contract_path=contract_path.relative_to(tmp_path).as_posix(),
            plan_manifest_path=plan_path.relative_to(tmp_path).as_posix(),
            task_completion_path=completion_path.relative_to(tmp_path).as_posix(),
            review_pack_path=review_path.relative_to(tmp_path).as_posix(),
            browser_result_path=browser_path.relative_to(tmp_path).as_posix(),
        ),
    )


def test_finalizer_rejects_review_pack_with_a_different_plan_hash(tmp_path, monkeypatch):
    _write_current_review_artifacts(tmp_path, monkeypatch, review_plan_sha256="b" * 64)

    with pytest.raises(RuntimeError, match="ReviewPack.*plan"):
        finalizer._check_review_pack("DEV-40", "dev-40")


def test_finalizer_rejects_profile_that_differs_from_active_design(tmp_path, monkeypatch):
    _write_current_review_artifacts(
        tmp_path,
        monkeypatch,
        design_profile="standard",
    )

    with pytest.raises(RuntimeError, match="profile"):
        finalizer._check_review_pack("DEV-40", "dev-40")


@pytest.mark.parametrize("mutation", ["remove", "modify"])
def test_finalizer_rejects_stale_gate_evidence(tmp_path, monkeypatch, mutation):
    _write_current_review_artifacts(tmp_path, monkeypatch)
    gate_log = tmp_path / "openspec/changes/dev-40/attempts/1/lint.log"
    if mutation == "remove":
        gate_log.unlink()
    else:
        gate_log.write_text("tampered", encoding="utf-8")

    with pytest.raises(RuntimeError, match="gate evidence|stale"):
        finalizer._check_review_pack("DEV-40", "dev-40")


def test_finalizer_requires_operational_evidence_for_every_criterion(tmp_path, monkeypatch):
    _write_current_review_artifacts(
        tmp_path,
        monkeypatch,
        include_operational_evidence=False,
    )

    with pytest.raises(RuntimeError, match="operational"):
        finalizer._check_review_pack("DEV-40", "dev-40")


@pytest.mark.parametrize("case", ["missing", "empty", "unmapped"])
def test_finalizer_rejects_standard_completion_with_malformed_criterion_evidence(
    tmp_path, monkeypatch, case
):
    _write_current_review_artifacts(
        tmp_path,
        monkeypatch,
        design_profile="standard",
        persisted_profile="standard",
    )
    completion_path = workflow.task_completion_path("dev-40", 1)
    completion = workflow.load_model(completion_path, workflow.TaskCompletion)
    completion_data = completion.model_dump()
    evidence_path = tmp_path / "apps/api/src/operational.py"
    evidence = {
        evidence_path.relative_to(tmp_path).as_posix(): workflow.file_sha256(evidence_path)
    }
    completion_data["acceptance_evidence"] = {
        "missing": {},
        "empty": {"AC-001": {}},
        "unmapped": {"AC-001": evidence, "AC-002": evidence},
    }[case]
    workflow.save_model(
        completion_path,
        workflow.TaskCompletion.model_validate(completion_data),
    )
    review_path = workflow.review_pack_path("dev-40", 1)
    review = workflow.load_model(review_path, workflow.ReviewPack)
    completion_sha256 = workflow.file_sha256(completion_path)
    workflow.save_model(
        review_path,
        review.model_copy(
            update={
                "task_completion_sha256": completion_sha256,
                "referenced_files": {
                    **review.referenced_files,
                    review.task_completion_path: completion_sha256,
                },
            }
        ),
    )

    with pytest.raises(RuntimeError, match="TaskCompletion evidence"):
        finalizer._check_review_pack("DEV-40", "dev-40")


def test_check_crew_result_rejects_missing_evidence():
    result = CrewResult(
        ticket_id="DEV-6",
        change_id="dev-6",
        attempt=1,
        status="approved",
        summary="approved",
        verification=VerificationResult(
            python="passed",
            lint="passed",
            test="passed",
            build="passed",
            integration="passed",
            playwright="skipped",
            openspec="passed",
        ),
    )

    with pytest.raises(RuntimeError, match="Evidencia inválida"):
        finalizer._check_crew_result("DEV-6", "dev-6", result, "not_required")


def test_finalize_archives_without_unsupported_json_flag(
    monkeypatch, tmp_path
):
    change = tmp_path / "dev-6"
    change.mkdir()
    (change / "tasks.md").write_text("- [x] completed\n", encoding="utf-8")
    (change / "design.md").write_text(
        "Browser E2E: not_required\n", encoding="utf-8"
    )
    (change / "result.json").write_text(
        CrewResult(
            ticket_id="DEV-6",
            change_id="dev-6",
            status="approved",
            summary="approved",
            verification=VerificationResult(
                python="passed",
                lint="passed",
                test="passed",
                build="passed",
                integration="passed",
                playwright="skipped",
                openspec="passed",
            ),
        ).model_dump_json(),
        encoding="utf-8",
    )

    commands = []
    checks = iter([(change, False), (change, True)])
    monkeypatch.setattr(finalizer, "_find_change", lambda _: next(checks))
    monkeypatch.setattr(finalizer, "_check_branch", lambda _: None)
    monkeypatch.setattr(finalizer, "_check_review_pack", lambda *_: "operational")
    monkeypatch.setattr(finalizer, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(finalizer, "_run_code_gates", lambda: None)
    monkeypatch.setattr(finalizer, "complete_issue", lambda _: None)
    monkeypatch.setattr(finalizer, "_commit", lambda _: None)

    def run(command, cwd=Path("."), timeout=600):
        commands.append(command)
        return ""

    monkeypatch.setattr(finalizer, "_run", run)

    assert finalizer.finalize("DEV-6")["status"] == "done"
    assert [
        "pnpm",
        "exec",
        "openspec",
        "archive",
        "dev-6",
        "--yes",
    ] in commands


def test_run_code_gates_starts_database_before_integration_test(monkeypatch):
    commands = []

    monkeypatch.setattr(
        finalizer,
        "_run",
        lambda command, **_: commands.append(command) or "",
    )

    finalizer._run_code_gates()

    assert commands[-2:] == [
        ["pnpm", "db:start"],
        ["pnpm", "--filter", "@koty-app/api", "test:integration"],
    ]


def test_finalize_reports_a_blocked_crew_result(tmp_path, monkeypatch):
    change = tmp_path / "dev-6"
    change.mkdir()
    (change / "result.json").write_text(
        CrewResult(
            ticket_id="DEV-6",
            change_id="dev-6",
            status="blocked",
            failure_type="configuration",
            summary="Docker unavailable",
            verification=VerificationResult(
                python="skipped",
                lint="skipped",
                test="skipped",
                build="skipped",
                integration="skipped",
                playwright="skipped",
                openspec="skipped",
            ),
        ).model_dump_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr(finalizer, "_find_change", lambda _: (change, False))

    result = finalizer.finalize("DEV-6")

    assert result["status"] == "blocked"
    assert result["reason"] == "blocked"


def test_commit_excludes_runtime_artifacts(monkeypatch):
    commands = []
    monkeypatch.setattr(finalizer, "_current_branch", lambda: "feat/dev-6")
    monkeypatch.setattr(finalizer, "get_issue", lambda _: {"title": "Title"})
    monkeypatch.setattr(
        finalizer,
        "_run",
        lambda command, **_: commands.append(command) or "M crewai/src/crew/main.py\n?? .agent/crew/dev-6/\n",
    )

    finalizer._commit("DEV-6")

    assert ["git", "add", "--all", "--", ".", ":(exclude).agent"] in commands


def test_commit_rejects_previously_staged_runtime_artifacts(monkeypatch):
    monkeypatch.setattr(finalizer, "_current_branch", lambda: "feat/dev-6")
    monkeypatch.setattr(
        finalizer,
        "_run",
        lambda command, **_: ".agent/crew/dev-6/execution.json"
        if command[:3] == ["git", "diff", "--cached"]
        else "M crewai/src/crew/main.py",
    )

    with pytest.raises(RuntimeError, match="runtime"):
        finalizer._commit("DEV-6")


def test_finalizer_failure_uses_finalization_diagnostics_path(tmp_path):
    change = tmp_path / "dev-6"
    change.mkdir()

    finalizer._write_failure(
        change,
        "verification",
        RuntimeError("gate failed"),
    )

    assert list((change / "attempts").glob("attempt-*.md")) == []
    diagnostics = list((change / "finalization").glob("finalizer-*.md"))
    assert len(diagnostics) == 1
    assert "gate failed" in diagnostics[0].read_text(encoding="utf-8")
