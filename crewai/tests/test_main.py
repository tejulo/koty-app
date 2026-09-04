import json
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import crew.main as main
import crew.finalizer as finalizer
import crew.workflow as workflow
import crew.tools.custom_tool as tools
from crewai.utilities.converter import ConverterError
from crew.gates import GateRun
from crew.models import (
    AcceptanceCriterion,
    CrewResult,
    ExecutionState,
    PlanDraft,
    PlanDraftSpec,
    PlanManifest,
    ReviewVerdict,
    TesterResult,
    TicketContract,
)


TICKET_HASH = "a" * 64


def contract() -> TicketContract:
    return TicketContract(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256=TICKET_HASH,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-001", text="Persist phase contracts."),
        ],
        objective="Persist phase contracts.",
        in_scope=["crewai"],
        constraints=["Use persisted paths."],
        dependencies=[],
        ambiguities=[],
    )


def prepare_state(
    tmp_path: Path,
    monkeypatch,
    *,
    phase="implementing",
    profile="standard",
    tasks_content="tasks.md",
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
            (
                f"verification_profile: {profile}"
                if name == "design.md"
                else tasks_content
                if name == "tasks.md"
                else name
            ),
            encoding="utf-8",
        )
    completion_source = tmp_path / "crewai/src/crew/implementation.py"
    completion_source.parent.mkdir(parents=True, exist_ok=True)
    completion_source.write_text("COMPLETION_EVIDENCE = True\n", encoding="utf-8")

    contract_path = workflow.ticket_contract_path("dev-40", 1)
    workflow.save_model(contract_path, contract())
    manifest = PlanManifest(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256=TICKET_HASH,
        ticket_contract_sha256=workflow.file_sha256(contract_path),
        artifacts={name: workflow.file_sha256(path) for name, path in artifacts.items()},
        profile=profile,
        acceptance_map={"AC-001": ["4.1"]},
    )
    plan_path = workflow.plan_manifest_path("dev-40", 2)
    workflow.save_model(plan_path, manifest)
    completion_path = workflow.task_completion_path("dev-40", 2)
    workflow.save_model(
        completion_path,
        workflow.build_task_completion(
            manifest,
            plan_path,
            artifacts["tasks.md"],
            {criterion: [completion_source] for criterion in manifest.acceptance_map},
        ),
    )
    return ExecutionState(
        ticket_id="DEV-40",
        change_id="dev-40",
        phase=phase,
        ticket_sha256=TICKET_HASH,
        plan_sha256=workflow.file_sha256(plan_path),
        profile=profile,
        last_attempt=2,
        ticket_contract_path=contract_path.relative_to(tmp_path).as_posix(),
        plan_manifest_path=plan_path.relative_to(tmp_path).as_posix(),
        task_completion_path=completion_path.relative_to(tmp_path).as_posix(),
    )


def passed_gates():
    return [GateRun(name, True, f"{name}-evidence", "") for name in workflow.BASE_GATES]


def test_current_ticket_hash_is_computed_from_serialized_ticket(monkeypatch):
    ticket = {"id": "DEV-40", "title": "Persist phase contracts"}
    monkeypatch.setattr(main, "get_issue", lambda _: ticket)

    actual = main.current_ticket_sha256("DEV-40")

    expected = hashlib.sha256(
        json.dumps(ticket, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert actual == expected


def test_repair_runs_only_programmer_and_reviewer_when_plan_is_current(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")

    def kickoff(role, **_):
        calls.append(role)
        if role == "reviewer":
            return SimpleNamespace(
                pydantic=ReviewVerdict(
                    ticket_id="DEV-40", change_id="dev-40", status="approved", summary="Approved."
                )
            )
        return SimpleNamespace(raw="Implemented.")

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_ticket("DEV-40", "dev-40", state)

    assert calls == ["programmer", "reviewer"]
    assert result.phase == "approved"


def test_standard_profile_persists_skipped_browser_result_without_tester(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="browser_testing", profile="standard")
    calls = []
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.advance_phase("DEV-40", "dev-40", state)

    assert result.phase == "reviewing"
    assert calls == []
    browser = workflow.load_model(
        workflow.browser_result_path("dev-40", result.last_attempt), TesterResult
    )
    assert browser == TesterResult(status="skipped", summary="Browser testing is not required by the profile.")


def test_stale_plan_blocks_before_programmer_invocation(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    state.plan_sha256 = "b" * 64
    calls = []
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.advance_phase("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert calls == []


def test_changed_ticket_restarts_planning_and_clears_stale_contract_paths(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: "b" * 64)

    result = main.advance_phase("DEV-40", "dev-40", state)

    assert result.phase == "planning"
    assert result.plan_manifest_path is None
    assert result.repair_pack_path is None


def test_verification_runs_each_immutable_gate_once_before_creating_repair_pack(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    calls = []
    gates = passed_gates()
    gates[1] = GateRun("lint", False, "lint-evidence", "full lint output")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: calls.append(True) or gates)

    result = main.run_verification("DEV-40", "dev-40", state)

    assert calls == [True]
    assert result.phase == "implementing"
    pack = workflow.load_model(tmp_path / result.repair_pack_path, main.RepairPack)
    assert pack.failure_stage == "lint"
    assert pack.evidence_id == "lint-evidence"


def test_planning_persists_architect_draft_and_builds_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec/changes/dev-40"
    calls = []
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "_run_gate", lambda *_: GateRun("openspec", True, "open-evidence", ""))

    def kickoff(role, *, inputs):
        calls.append((role, inputs))
        if role == "analyst":
            return SimpleNamespace(pydantic=contract())
        return SimpleNamespace(
            pydantic=PlanDraft(
                profile="operational",
                proposal="proposal",
                design="- verification_profile: operational\n",
                tasks="tasks",
                specs=[PlanDraftSpec(capability="crew-supervision", content="spec")],
                acceptance_map={"AC-001": ["4.1"]},
            )
        )

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "implementing"
    assert (change / "specs/crew-supervision/spec.md").is_file()
    persisted_manifest = workflow.load_model(tmp_path / result.plan_manifest_path, PlanManifest)
    assert persisted_manifest.artifacts == {
        name: workflow.file_sha256(change / name)
        for name in ("proposal.md", "design.md", "tasks.md", "specs/crew-supervision/spec.md")
    }
    assert calls[0] == (
        "analyst",
        {
            "ticket_id": "DEV-40",
            "change_id": "dev-40",
            "ticket_sha256": TICKET_HASH,
        },
    )
    assert calls[1] == (
        "architect",
        {
            "ticket_contract_json": contract().model_dump_json(),
            "project_context": "",
        },
    )


def test_planning_restores_the_active_plan_when_openspec_preflight_fails(tmp_path, monkeypatch):
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
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "_run_gate", lambda *_: GateRun("openspec", False, "open-evidence", "invalid"))

    def kickoff(role, **_):
        if role == "analyst":
            return SimpleNamespace(pydantic=contract())
        return SimpleNamespace(
            pydantic=PlanDraft(
                profile="operational",
                proposal="new proposal",
                design="verification_profile: operational\n",
                tasks="new tasks",
                specs=[PlanDraftSpec(capability="crew-supervision", content="new spec")],
                acceptance_map={"AC-001": ["4.1"]},
            )
        )

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "blocked"
    assert (change / "proposal.md").read_text(encoding="utf-8") == "old proposal"
    assert (change / "specs/old/spec.md").read_text(encoding="utf-8") == "old spec"
    assert not (change / "specs/crew-supervision/spec.md").exists()


def test_planning_rejects_an_invalid_draft_without_replacing_the_active_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    proposal = tmp_path / "openspec/changes/dev-40/proposal.md"
    proposal.parent.mkdir(parents=True)
    proposal.write_text("old proposal", encoding="utf-8")
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)

    def kickoff(role, **_):
        if role == "analyst":
            return SimpleNamespace(pydantic=contract())
        return SimpleNamespace(
            pydantic=PlanDraft(
                profile="operational",
                proposal="new proposal",
                design="missing profile",
                tasks="new tasks",
                specs=[PlanDraftSpec(capability="crew-supervision", content="new spec")],
                acceptance_map={"AC-001": ["4.1"]},
            )
        )

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "blocked"
    assert proposal.read_text(encoding="utf-8") == "old proposal"


def test_planning_rejects_a_profile_mismatch_before_staging(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)

    def kickoff(role, **_):
        if role == "analyst":
            return SimpleNamespace(pydantic=contract())
        return SimpleNamespace(
            pydantic=PlanDraft(
                profile="operational",
                proposal="proposal",
                design="verification_profile: standard\n",
                tasks="tasks",
                specs=[PlanDraftSpec(capability="crew-supervision", content="spec")],
                acceptance_map={"AC-001": ["4.1"]},
            )
        )

    monkeypatch.setattr(main, "kickoff_role", kickoff)
    monkeypatch.setattr(
        workflow,
        "write_plan_draft",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not write")),
    )

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "blocked"
    assert result.phase_usage["blocked_reason"] == "PlanDraft profile does not match design"


def test_planning_retries_an_empty_architect_response(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "_run_gate", lambda *_: GateRun("openspec", True, "open-evidence", ""))
    monkeypatch.setenv("MAX_ARCHITECT_EMPTY_RESPONSE_RETRIES", "1")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "analyst":
            return SimpleNamespace(pydantic=contract())
        if calls.count("architect") == 1:
            raise ValueError("Invalid response from LLM call - None or empty.")
        return SimpleNamespace(
            pydantic=PlanDraft(
                profile="standard",
                proposal="proposal",
                design="verification_profile: standard\n",
                tasks="tasks",
                specs=[PlanDraftSpec(capability="crew-supervision", content="spec")],
                acceptance_map={"AC-001": ["4.1"]},
            )
        )

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "implementing"
    assert calls == ["analyst", "architect", "architect"]
    assert result.phase_usage["planning:architect_empty_response_retries"] == 1


def test_planning_retries_an_empty_architect_response_once(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "_run_gate", lambda *_: GateRun("openspec", True, "open-evidence", ""))
    monkeypatch.setenv("MAX_ARCHITECT_EMPTY_RESPONSE_RETRIES", "3")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "analyst":
            return SimpleNamespace(pydantic=contract())
        raise ValueError("Invalid response from LLM call - None or empty.")

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "blocked"
    assert calls == ["analyst", "architect", "architect"]


def test_selected_profile_rejects_multiple_declarations(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    design = tmp_path / "openspec/changes/dev-40/design.md"
    design.parent.mkdir(parents=True)
    design.write_text(
        "verification_profile: standard\nverification_profile: browser\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly one"):
        main._selected_profile("dev-40")


def test_planning_blocks_when_crewai_cannot_convert_a_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ConverterError("invalid contract")),
    )

    result = main.run_planning("DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40"))

    assert result.phase == "blocked"
    assert result.phase_usage["blocked_reason"] == "invalid contract"


def test_phase_usage_is_serializable_and_records_configured_limits(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "kickoff_role", lambda *_args, **_kwargs: SimpleNamespace(raw="done", token_usage={"total_tokens": 7}))

    result = main.run_programmer("DEV-40", "dev-40", state)

    usage_path = tmp_path / result.phase_usage["implementing"]
    usage = json.loads(usage_path.read_text(encoding="utf-8"))
    assert usage["phase"] == "implementing"
    assert usage["role"] == "programmer"
    assert usage["limits"] == {"max_iter": 20, "max_tokens": 2500}
    assert usage["usage"] == {"total_tokens": 7}


def test_repair_scope_is_persisted_and_available_only_to_programmer(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    gates = passed_gates()
    gates[0] = GateRun("python", False, "python-evidence", "src/crew/main.py: failure")
    monkeypatch.setattr(
        main,
        "run_base_gates",
        lambda *_: gates,
    )

    state = main.run_verification("DEV-40", "dev-40", state)
    pack = workflow.load_model(tmp_path / state.repair_pack_path, main.RepairPack)
    observed_scopes = []
    writes = []
    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)

    def programmer(role, **_):
        observed_scopes.append((role, main.os.environ.get("CREW_REPAIR_SCOPE")))
        writes.append(tools.escribir_archivo_raiz.func("apps/api/src/app.ts", "blocked"))
        return SimpleNamespace(raw="fixed")

    monkeypatch.setattr(
        main,
        "kickoff_role",
        programmer,
    )

    result = main.run_programmer("DEV-40", "dev-40", state)

    assert pack.repair_scope
    assert observed_scopes == [("programmer", json.dumps(pack.repair_scope))]
    assert writes == ["Error: ruta fuera del repairScope"]
    assert "CREW_REPAIR_SCOPE" not in main.os.environ
    assert result.last_attempt == 3


def test_each_repair_uses_a_retained_new_attempt_directory(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    failed = passed_gates()
    failed[1] = GateRun("lint", False, "lint-evidence", "lint failure")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: failed)
    monkeypatch.setattr(main, "kickoff_role", lambda *_args, **_kwargs: SimpleNamespace(raw="fixed"))

    state = main.run_verification("DEV-40", "dev-40", state)
    first_pack = tmp_path / state.repair_pack_path
    state = main.run_programmer("DEV-40", "dev-40", state)
    state = main.run_verification("DEV-40", "dev-40", state)
    second_pack = tmp_path / state.repair_pack_path

    assert first_pack != second_pack
    assert first_pack.is_file()
    assert second_pack.is_file()
    assert state.last_attempt == 4
    assert (tmp_path / "openspec/changes/dev-40/attempts/3/phase-usage-implementing-programmer.json").is_file()


def test_resume_blocks_ticket_repairs_after_the_persisted_budget(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    failed = passed_gates()
    failed[1] = GateRun("lint", False, "lint-evidence", "lint failure")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: failed)
    state = main.run_verification("DEV-40", "dev-40", state)
    state.phase_usage["repair_attempts"] = {"ticket": 1, "infrastructure": 0}
    state.phase_usage["pending_repair_budget"] = "ticket"
    calls = []
    monkeypatch.setenv("MAX_TICKET_ATTEMPTS", "1")
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    workflow.save_execution("DEV-40", state)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    result = main.run_ticket("DEV-40", "dev-40", workflow.load_execution("DEV-40"))

    assert result.phase == "blocked"
    assert calls == []
    assert workflow.load_execution("DEV-40").phase == "blocked"


def test_resume_blocks_infrastructure_repairs_after_the_persisted_budget(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    failed = passed_gates()
    failed[4] = GateRun(
        "integration", False, "integration-evidence", "connection refused", "infrastructure"
    )
    monkeypatch.setattr(main, "run_base_gates", lambda *_: failed)
    state = main.run_verification("DEV-40", "dev-40", state)
    state.phase_usage["repair_attempts"] = {"ticket": 0, "infrastructure": 1}
    monkeypatch.setenv("MAX_INFRASTRUCTURE_ATTEMPTS", "1")
    calls = []
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.run_programmer("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert calls == []


def test_repair_budget_uses_structured_gate_provenance_not_output_text():
    assert main._repair_budget(
        GateRun("integration", False, "integration-evidence", "Docker unavailable")
    ) == "ticket"
    assert main._repair_budget(
        GateRun("integration", False, "integration-evidence", "test assertion failed", "infrastructure")
    ) == "infrastructure"


def test_review_blocks_when_successful_gate_evidence_hash_changes(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")
    state = main.run_verification("DEV-40", "dev-40", state)
    gate_path = tmp_path / state.phase_usage["gate_runs"][0]["evidence_path"]
    gate_path.write_text("tampered", encoding="utf-8")
    calls = []
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.run_review("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert calls == []


def test_review_blocks_when_successful_gate_evidence_is_missing(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")
    state = main.run_verification("DEV-40", "dev-40", state)
    gate_path = tmp_path / state.phase_usage["gate_runs"][0]["evidence_path"]
    gate_path.unlink()
    calls = []
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.run_review("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert calls == []


def test_invalid_gate_results_block_before_tester_selection(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying", profile="browser")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates()[:-1])
    calls = []
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.run_verification("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert calls == []


def test_usage_records_the_configured_token_limit(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    monkeypatch.setenv("ZEN_CODER_MAX_TOKENS", "1337")
    monkeypatch.setattr(main, "kickoff_role", lambda *_args, **_kwargs: SimpleNamespace(raw="done"))

    result = main.run_programmer("DEV-40", "dev-40", state)

    usage_path = tmp_path / result.phase_usage["implementing"]
    assert json.loads(usage_path.read_text(encoding="utf-8"))["limits"]["max_tokens"] == 1337


def test_programmer_failure_transitions_to_blocked(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "kickoff_role", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("provider down")))

    result = main.run_programmer("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert "provider down" in result.phase_usage["blocked_reason"]


def test_tester_failure_transitions_to_blocked(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="browser_testing", profile="browser")
    monkeypatch.setattr(main, "kickoff_role", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("provider down")))

    result = main.run_browser_testing("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert "provider down" in result.phase_usage["blocked_reason"]


def test_failed_browser_tester_returns_only_to_programmer(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="browser_testing", profile="browser")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "tester":
            return SimpleNamespace(pydantic=TesterResult(status="failed", summary="scenario failed"))
        return SimpleNamespace(raw="fixed")

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    state = main.run_browser_testing("DEV-40", "dev-40", state)
    result = main.run_programmer("DEV-40", "dev-40", state)

    assert result.phase == "verifying"
    assert calls == ["tester", "programmer"]


def test_reviewer_retry_returns_only_to_programmer(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "reviewer":
            return SimpleNamespace(
                pydantic=ReviewVerdict(
                    ticket_id="DEV-40",
                    change_id="dev-40",
                    status="retryable_failure",
                    summary="needs repair",
                )
            )
        return SimpleNamespace(raw="fixed")

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    state = main.run_verification("DEV-40", "dev-40", state)
    state = main.run_review("DEV-40", "dev-40", state)
    result = main.run_programmer("DEV-40", "dev-40", state)

    assert result.phase == "verifying"
    assert calls == ["reviewer", "programmer"]


def test_replan_atomically_clears_current_contract_references_before_running(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    state.repair_pack_path = "openspec/changes/dev-40/attempts/2/repair-pack.json"
    state.review_pack_path = "openspec/changes/dev-40/attempts/2/review-pack.json"
    state.browser_result_path = "openspec/changes/dev-40/attempts/2/browser-result.json"
    state.phase_usage["prior_evidence"] = "openspec/changes/dev-40/attempts/1/lint.log"
    saved = []
    observed = []
    monkeypatch.setattr(main, "ensure_change", lambda _: None)
    monkeypatch.setattr(workflow, "load_execution", lambda _: state)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: "b" * 64)
    monkeypatch.setattr(workflow, "save_execution", lambda _, value: saved.append(value.model_copy(deep=True)))
    monkeypatch.setattr(main, "run_ticket", lambda *_args: observed.append(_args[2].model_copy(deep=True)) or _args[2])
    monkeypatch.setattr(sys, "argv", ["run_crew", "DEV-40", "--replan"])

    main.run()

    assert saved[0].phase == "planning"
    assert saved[0].ticket_contract_path is None
    assert saved[0].plan_manifest_path is None
    assert saved[0].repair_pack_path is None
    assert saved[0].review_pack_path is None
    assert saved[0].browser_result_path is None
    assert saved[0].last_attempt == 3
    assert saved[0].phase_usage["prior_evidence"].endswith("lint.log")
    assert observed[0].phase == "planning"


def test_review_pack_uses_completion_artifact_for_unchecked_tasks(tmp_path, monkeypatch):
    state = prepare_state(
        tmp_path,
        monkeypatch,
        phase="verifying",
        tasks_content="- [ ] finish the implementation\n",
    )
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda *_args, **_kwargs: SimpleNamespace(
            pydantic=ReviewVerdict(
                ticket_id="DEV-40",
                change_id="dev-40",
                status="approved",
                summary="Approved.",
            )
        ),
    )

    state = main.run_verification("DEV-40", "dev-40", state)
    result = main.run_review("DEV-40", "dev-40", state)

    pack = workflow.load_model(tmp_path / result.review_pack_path, main.ReviewPack)
    assert pack.incomplete_tasks is False
    assert pack.task_completion_path == state.task_completion_path


def test_unchanged_task_manifest_completes_review_and_finalization(tmp_path, monkeypatch):
    tasks_content = "- [ ] 4.1 finish the implementation\n"
    state = prepare_state(
        tmp_path,
        monkeypatch,
        tasks_content=tasks_content,
    )
    tasks_path = tmp_path / "openspec/changes/dev-40/tasks.md"
    original_hash = workflow.file_sha256(tasks_path)
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)

    def kickoff(role, **_):
        if role == "reviewer":
            return SimpleNamespace(
                pydantic=ReviewVerdict(
                    ticket_id="DEV-40",
                    change_id="dev-40",
                    status="approved",
                    summary="Approved.",
                )
            )
        return SimpleNamespace(raw="Implemented.")

    monkeypatch.setattr(main, "kickoff_role", kickoff)

    result = main.run_ticket("DEV-40", "dev-40", state)

    assert result.phase == "approved"
    assert tasks_path.read_text(encoding="utf-8") == tasks_content
    assert workflow.file_sha256(tasks_path) == original_hash
    completion = workflow.load_model(
        tmp_path / result.task_completion_path,
        main.TaskCompletion,
    )
    assert completion.tasks_path == "openspec/changes/dev-40/tasks.md"
    assert completion.tasks_sha256 == original_hash
    assert finalizer._check_review_pack("DEV-40", "dev-40") == "standard"


def test_run_writes_the_approved_crew_result_consumed_by_the_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    browser_path = workflow.browser_result_path("dev-40", 2)
    workflow.save_model(browser_path, TesterResult(status="skipped", summary="Not required."))
    state = ExecutionState(
        ticket_id="DEV-40",
        change_id="dev-40",
        phase="approved",
        ticket_sha256=TICKET_HASH,
        plan_sha256="b" * 64,
        profile="standard",
        last_attempt=2,
        browser_result_path=browser_path.relative_to(tmp_path).as_posix(),
        phase_usage={
            "gate_runs": [
                {"name": name, "passed": True, "evidence_id": f"{name}-evidence"}
                for name in workflow.BASE_GATES
            ]
        },
    )
    monkeypatch.setattr(main, "ensure_change", lambda _: None)
    monkeypatch.setattr(workflow, "load_execution", lambda _: state)
    monkeypatch.setattr(main, "run_ticket", lambda *_: state)
    monkeypatch.setattr(sys, "argv", ["run_crew", "DEV-40"])

    main.run()

    result = CrewResult.model_validate_json(
        (tmp_path / "openspec/changes/dev-40/result.json").read_text(encoding="utf-8")
    )
    assert result.status == "approved"
    assert result.attempt == 2
    assert result.evidence == {
        name: f"{name}-evidence" for name in workflow.BASE_GATES
    }
    assert result.verification.playwright == "skipped"
