import json
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

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
    PlanArtifactUnit,
    PlanManifest,
    PlanOutline,
    PlanningCheckpoint,
    PlanUnitOutline,
    ProjectContextCatalog,
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


def outline() -> PlanOutline:
    return PlanOutline(
        profile="standard",
        units=[
            PlanUnitOutline(
                artifact="proposal", objective="Propose the change.", context_refs=["context-001"]
            ),
            PlanUnitOutline(
                artifact="design", objective="Design the change.", context_refs=["context-002"]
            ),
            PlanUnitOutline(artifact="tasks", objective="Plan tasks.", context_refs=[]),
            PlanUnitOutline(
                artifact="spec",
                capability="crew-supervision",
                objective="Specify supervision.",
                context_refs=["context-001", "context-002"],
            ),
        ],
        acceptance_map={"AC-001": ["4.1"]},
    )


def artifact(unit: PlanUnitOutline) -> PlanArtifactUnit:
    content = {
        "proposal": "new proposal",
        "design": "verification_profile: standard\nBrowser E2E: not_required\n",
        "tasks": "new tasks",
        "spec:crew-supervision": "new spec",
    }[unit.unit_key]
    return PlanArtifactUnit(
        artifact=unit.artifact,
        capability=unit.capability,
        content=content,
    )


def raw_output(model, **attributes):
    return SimpleNamespace(raw=model.model_dump_json(), **attributes)


def prepare_planning_root(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    context = tmp_path / "CONTEXT.md"
    context.write_text(
        "# Project\n\n## Product\nProduct body.\n\n## Delivery\nDelivery body.\n",
        encoding="utf-8",
    )
    change = tmp_path / "openspec/changes/dev-40"
    for name, content in {
        "proposal.md": "old proposal",
        "design.md": "verification_profile: operational\n",
        "tasks.md": "old tasks",
        "specs/old/spec.md": "old spec",
    }.items():
        path = change / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: TICKET_HASH)
    monkeypatch.setattr(
        main, "_run_gate", lambda *_: GateRun("openspec", True, "open-evidence", "")
    )
    return change


def install_staged_architect(monkeypatch, artifact_call):
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: raw_output(contract())
        if role == "analyst"
        else (_ for _ in ()).throw(AssertionError(f"legacy role dispatch: {role}")),
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda *, inputs: raw_output(outline(), token_usage={"total_tokens": 11}),
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        artifact_call,
        raising=False,
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


def test_as_model_parses_plain_raw_json_before_pydantic_output():
    output = SimpleNamespace(
        raw='{"artifact":"proposal","objective":"Raw output.","context_refs":[]}',
        pydantic=PlanUnitOutline(
            artifact="tasks", objective="Structured output.", context_refs=[]
        ),
    )

    result = main._as_model(output, PlanUnitOutline)

    assert result == PlanUnitOutline(
        artifact="proposal", objective="Raw output.", context_refs=[]
    )


def test_as_model_parses_raw_json_in_a_json_code_fence():
    output = SimpleNamespace(
        raw="\n```json\n{\"artifact\":\"proposal\",\"objective\":\"Fenced output.\",\"context_refs\":[]}\n```\n"
    )

    result = main._as_model(output, PlanUnitOutline)

    assert result == PlanUnitOutline(
        artifact="proposal", objective="Fenced output.", context_refs=[]
    )


def test_as_model_parses_raw_json_after_a_think_block():
    output = SimpleNamespace(
        raw='<think>Reasoning belongs outside the contract.</think>\n{"artifact":"proposal","objective":"After thinking.","context_refs":[]}'
    )

    result = main._as_model(output, PlanUnitOutline)

    assert result == PlanUnitOutline(
        artifact="proposal", objective="After thinking.", context_refs=[]
    )


def test_as_model_rejects_malformed_raw_json():
    output = SimpleNamespace(raw='{"artifact":"proposal"')

    with pytest.raises(ValidationError, match="Invalid JSON"):
        main._as_model(output, PlanUnitOutline)


def test_as_model_rejects_raw_json_that_fails_model_validation():
    output = SimpleNamespace(raw='{"artifact":"proposal","objective":"Invalid output.","context_refs":"not a list"}')

    with pytest.raises(ValidationError, match="context_refs"):
        main._as_model(output, PlanUnitOutline)


def test_as_model_rejects_an_empty_raw_contract_before_pydantic_fallback():
    output = SimpleNamespace(
        raw=None,
        pydantic=PlanUnitOutline(
            artifact="proposal", objective="Legacy fallback must not bypass raw.", context_refs=[]
        ),
    )

    with pytest.raises(ValueError, match="raw JSON"):
        main._as_model(output, PlanUnitOutline)


def test_as_model_rejects_constructed_pydantic_output_without_raw_json():
    output = SimpleNamespace(
        pydantic=PlanUnitOutline(
            artifact="proposal", objective="Constructed output.", context_refs=[]
        )
    )

    with pytest.raises(ValueError, match="raw JSON"):
        main._as_model(output, PlanUnitOutline)


def test_invalid_analyst_raw_contract_retries_once_and_records_each_invocation(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    analyst_calls = []

    def analyst(role, **_):
        assert role == "analyst"
        analyst_calls.append(role)
        raw = "{invalid" if len(analyst_calls) == 1 else contract().model_dump_json()
        return SimpleNamespace(raw=raw, token_usage={"total_tokens": len(analyst_calls)})

    monkeypatch.setattr(main, "kickoff_role", analyst)
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: SimpleNamespace(raw=outline().model_dump_json()),
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda *, inputs, retry=False: SimpleNamespace(
            raw=artifact(
                PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
            ).model_dump_json()
        ),
    )

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "implementing"
    assert analyst_calls == ["analyst", "analyst"]
    usage_paths = sorted(
        workflow.ticket_contract_path("dev-40", 1).parent.glob(
            "phase-usage-planning-analyst-*.json"
        )
    )
    assert len(usage_paths) == 2
    failed = json.loads(usage_paths[0].read_text(encoding="utf-8"))
    completed = json.loads(usage_paths[1].read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["raw"] == "{invalid"
    assert failed["usage"] == {"total_tokens": 1}
    assert failed["expected_model"] == "TicketContract"
    assert failed["validation_error"]
    assert failed["retry_state"] == "pending"
    assert completed["status"] == "completed"
    assert completed["usage"] == {"total_tokens": 2}
    assert completed["retry_state"] == "consumed"
    assert result.contract_output_retry_state == {}


def test_two_invalid_analyst_contracts_exhaust_the_single_retry(tmp_path, monkeypatch):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: calls.append(role) or SimpleNamespace(raw="{invalid"),
    )

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert calls == ["analyst", "analyst"]
    assert result.contract_output_retry_state == {"analyst": "consumed"}
    usage_paths = sorted(
        workflow.ticket_contract_path("dev-40", 1).parent.glob(
            "phase-usage-planning-analyst-*.json"
        )
    )
    assert len(usage_paths) == 2
    assert [json.loads(path.read_text())["status"] for path in usage_paths] == [
        "failed",
        "failed",
    ]


def test_invalid_contract_persists_pending_retry_before_failed_usage_recording(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda *_args, **_kwargs: SimpleNamespace(raw="{invalid"),
    )

    def crash_while_recording(*_args, **_kwargs):
        raise SystemExit("crashed while writing failed usage")

    monkeypatch.setattr(main, "_record_usage", crash_while_recording)
    with pytest.raises(SystemExit, match="failed usage"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    persisted = workflow.load_execution("DEV-40")
    assert persisted.contract_output_retry_state == {"analyst": "pending"}
    audit = persisted.phase_usage["contract_output_retry:analyst"]
    assert audit["raw"] == "{invalid"
    assert audit["expected_model"] == "TicketContract"
    assert "Invalid JSON" in audit["validation_error"]
    assert audit["invocation"] == 1
    assert audit["retry_state"] == "pending"


def test_resume_reconstructs_pending_contract_failure_before_distinct_retry(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    analyst_calls = []

    def analyst(role, **_):
        analyst_calls.append(role)
        raw = "{invalid" if len(analyst_calls) == 1 else contract().model_dump_json()
        return SimpleNamespace(raw=raw)

    monkeypatch.setattr(main, "kickoff_role", analyst)
    original_record_usage = main._record_usage

    def crash_before_failed_usage(*_args, **_kwargs):
        raise SystemExit("crashed before failed usage")

    monkeypatch.setattr(main, "_record_usage", crash_before_failed_usage)
    with pytest.raises(SystemExit, match="failed usage"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    monkeypatch.setattr(main, "_record_usage", original_record_usage)
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: raw_output(outline()),
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda *, inputs, retry=False: raw_output(
            artifact(PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"]))
        ),
    )

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "implementing"
    assert analyst_calls == ["analyst", "analyst"]
    usage_paths = sorted(
        workflow.ticket_contract_path("dev-40", 1).parent.glob(
            "phase-usage-planning-analyst-*.json"
        )
    )
    assert len(usage_paths) == 2
    evidence = [json.loads(path.read_text(encoding="utf-8")) for path in usage_paths]
    assert [(item["status"], item["invocation"]) for item in evidence] == [
        ("failed", 1),
        ("completed", 2),
    ]
    assert evidence[0]["raw"] == "{invalid"
    assert evidence[0]["validation_error"]


def test_semantic_contract_failure_blocks_without_a_second_dispatch(tmp_path, monkeypatch):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    invalid = contract().model_copy(update={"ticket_id": "DEV-41"})
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: calls.append(role) or raw_output(invalid),
    )

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert calls == ["analyst"]
    assert result.contract_output_retry_state == {}


def test_dispatch_value_error_blocks_without_consuming_a_contract_retry(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: calls.append(role) or (_ for _ in ()).throw(ValueError("Falta configuración")),
    )

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert calls == ["analyst"]
    assert result.contract_output_retry_state == {}


def test_restart_blocks_consumed_analyst_contract_retry_before_redispatch(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: calls.append(role) or SimpleNamespace(raw="{invalid"),
    )
    original_save = workflow.save_execution

    def stop_after_consumption(ticket_id, state):
        original_save(ticket_id, state)
        if state.contract_output_retry_state.get("analyst") == "consumed":
            raise SystemExit("stopped after analyst retry consumption")

    monkeypatch.setattr(workflow, "save_execution", stop_after_consumption)
    with pytest.raises(SystemExit, match="analyst retry consumption"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    assert resumed.contract_output_retry_state == {"analyst": "consumed"}
    assert calls == ["analyst"]
    monkeypatch.setattr(workflow, "save_execution", original_save)
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role))

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == ["analyst"]
    assert "contract output retry" in result.phase_usage["blocked_reason"].lower()


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
            return raw_output(
                ReviewVerdict(
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
    state.planning_checkpoint_path = (
        "openspec/changes/dev-40/attempts/2/planning-checkpoint.json"
    )
    state.planning_checkpoint_sha256 = "c" * 64
    monkeypatch.setattr(main, "current_ticket_sha256", lambda _: "b" * 64)

    result = main.advance_phase("DEV-40", "dev-40", state)

    assert result.phase == "planning"
    assert result.plan_manifest_path is None
    assert result.repair_pack_path is None
    assert result.planning_checkpoint_path is None
    assert result.planning_checkpoint_sha256 is None


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


def test_staged_planning_uses_exact_inputs_and_outline_order_before_promotion(
    tmp_path, monkeypatch
):
    change = prepare_planning_root(tmp_path, monkeypatch)
    calls = []

    def analyst(role, *, inputs):
        calls.append((role, inputs))
        return raw_output(contract(), token_usage={"total_tokens": 7})

    def outline_call(*, inputs):
        calls.append(("outline", inputs))
        return raw_output(outline(), token_usage={"total_tokens": 11})

    def artifact_call(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        calls.append((requested.unit_key, inputs, retry))
        assert (change / "proposal.md").read_text(encoding="utf-8") == "old proposal"
        assert (change / "specs/old/spec.md").is_file()
        assert set(inputs) == {
            "ticket_contract_json",
            "plan_outline_json",
            "plan_unit_outline_json",
            "project_context",
        }
        assert inputs["ticket_contract_json"] == contract().model_dump_json()
        assert inputs["plan_outline_json"] == outline().model_dump_json()
        assert inputs["plan_unit_outline_json"] == requested.model_dump_json()
        return raw_output(artifact(requested), token_usage={"total_tokens": 13})

    monkeypatch.setattr(main, "kickoff_role", analyst)
    monkeypatch.setattr(main, "kickoff_architect_outline", outline_call, raising=False)
    monkeypatch.setattr(main, "kickoff_architect_artifact", artifact_call, raising=False)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "implementing"
    assert [call[0] for call in calls] == [
        "analyst",
        "outline",
        "proposal",
        "design",
        "tasks",
        "spec:crew-supervision",
    ]
    assert set(calls[1][1]) == {"ticket_contract_json", "context_index"}
    context_index = json.loads(calls[1][1]["context_index"])
    assert all("body" not in section for section in context_index["sections"])
    assert calls[2][1]["project_context"] == "[context-001] ## Product\n\nProduct body."
    assert calls[3][1]["project_context"] == "[context-002] ## Delivery\n\nDelivery body."
    assert calls[4][1]["project_context"] == ""
    assert (change / "specs/crew-supervision/spec.md").read_text(encoding="utf-8") == "new spec"
    persisted_manifest = workflow.load_model(tmp_path / result.plan_manifest_path, PlanManifest)
    assert persisted_manifest.profile == "standard"
    checkpoint = workflow.load_model(
        tmp_path / result.planning_checkpoint_path, PlanningCheckpoint
    )
    assert [unit.unit_key for unit in checkpoint.units] == [
        "proposal",
        "design",
        "tasks",
        "spec:crew-supervision",
    ]
    assert result.planning_checkpoint_sha256 == workflow.file_sha256(
        tmp_path / result.planning_checkpoint_path
    )


def test_pending_promotion_is_restored_before_early_staged_planning_failure(
    tmp_path, monkeypatch
):
    change = prepare_planning_root(tmp_path, monkeypatch)
    draft = main.assemble_plan_draft(
        outline(), [artifact(unit) for unit in outline().units]
    )
    workflow.write_plan_draft("dev-40", 1, draft)
    assert (change / ".plan-promotion").is_file()
    assert (change / "proposal.md").read_text(encoding="utf-8") == "new proposal"
    calls = []
    monkeypatch.setattr(main, "kickoff_role", lambda *args, **kwargs: calls.append(args))
    state = ExecutionState(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256=TICKET_HASH,
        last_attempt=1,
        ticket_contract_path="openspec/changes/dev-40/attempts/9/ticket-contract.json",
    )

    result = main.run_planning("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert calls == []
    assert (change / "proposal.md").read_text(encoding="utf-8") == "old proposal"
    assert (change / "specs/old/spec.md").read_text(encoding="utf-8") == "old spec"
    assert not (change / "specs/crew-supervision/spec.md").exists()
    assert not (change / ".plan-promotion").exists()


@pytest.mark.parametrize("wrapped", [False, True])
def test_artifact_length_failure_records_usage_and_retries_only_that_unit(
    tmp_path, monkeypatch, wrapped
):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []

    def artifact_call(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        calls.append((requested.unit_key, retry))
        if requested.unit_key == "proposal" and not retry:
            length_error = main.LengthFinishReasonError(
                completion=SimpleNamespace(usage={"total_tokens": 8000})
            )
            if wrapped:
                raise RuntimeError("wrapped") from length_error
            raise length_error
        return raw_output(artifact(requested), token_usage={"total_tokens": 5})

    install_staged_architect(monkeypatch, artifact_call)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "implementing"
    assert result.last_attempt == 1
    assert calls == [
        ("proposal", False),
        ("proposal", True),
        ("design", False),
        ("tasks", False),
        ("spec:crew-supervision", False),
    ]
    usage_paths = sorted(
        workflow.ticket_contract_path("dev-40", 1).parent.glob(
            "phase-usage-planning-architect-artifact-proposal-*.json"
        )
    )
    assert len(usage_paths) == 2
    failed = json.loads(usage_paths[0].read_text(encoding="utf-8"))
    retried = json.loads(usage_paths[1].read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["stage"] == "artifact"
    assert failed["unit"] == "proposal"
    assert failed["invocation"] == 1
    assert failed["effective_limit"] == 8000
    assert failed["usage"] == {"total_tokens": 8000}
    assert retried["status"] == "completed"
    assert retried["effective_limit"] == 16000


def test_length_error_detection_traverses_cyclic_cause_and_context_chains(monkeypatch):
    class FakeLengthFinishReasonError(Exception):
        pass

    monkeypatch.setattr(main, "LengthFinishReasonError", FakeLengthFinishReasonError, raising=False)
    first = RuntimeError("first")
    second = RuntimeError("second")
    first.__cause__ = second
    second.__context__ = first

    assert main._is_length_finish_reason(first) is False

    length_error = FakeLengthFinishReasonError("length")
    second.__cause__ = length_error
    assert main._is_length_finish_reason(first) is True


def test_length_error_detection_traverses_context_when_cause_is_also_present(
    monkeypatch,
):
    class FakeLengthFinishReasonError(Exception):
        pass

    monkeypatch.setattr(
        main, "LengthFinishReasonError", FakeLengthFinishReasonError, raising=False
    )
    outer = RuntimeError("outer")
    outer.__cause__ = RuntimeError("non-length cause")
    outer.__context__ = FakeLengthFinishReasonError("context-only length")

    assert main._is_length_finish_reason(outer) is True


def test_length_retry_exhaustion_blocks_with_checkpoint_and_stable_attempt(
    tmp_path, monkeypatch
):
    change = prepare_planning_root(tmp_path, monkeypatch)

    class FakeLengthFinishReasonError(Exception):
        pass

    monkeypatch.setattr(main, "LengthFinishReasonError", FakeLengthFinishReasonError, raising=False)
    calls = []

    def artifact_call(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        calls.append((requested.unit_key, retry))
        raise FakeLengthFinishReasonError("length")

    install_staged_architect(monkeypatch, artifact_call)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert result.last_attempt == 1
    assert calls == [("proposal", False), ("proposal", True)]
    checkpoint = workflow.load_model(
        tmp_path / result.planning_checkpoint_path, PlanningCheckpoint
    )
    assert checkpoint.invocation_status["proposal"] == "failed"
    assert (change / "proposal.md").read_text(encoding="utf-8") == "old proposal"
    assert len(
        list(
            workflow.ticket_contract_path("dev-40", 1).parent.glob(
                "phase-usage-planning-architect-artifact-proposal-*.json"
            )
        )
    ) == 2
    persisted = workflow.load_execution("DEV-40")
    assert persisted.phase == "blocked"
    assert persisted.planning_checkpoint_path == result.planning_checkpoint_path


def test_restart_after_normal_length_failure_resumes_with_retry_budget(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    first_calls = []

    def first_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        first_calls.append((requested.unit_key, retry))
        raise main.LengthFinishReasonError(
            completion=SimpleNamespace(usage={"total_tokens": 8000})
        )

    install_staged_architect(monkeypatch, first_artifact)
    original_save = main._save_planning_checkpoint
    failure_checkpoint_saves = 0

    def stop_after_first_failure_checkpoint(ticket_id, state, path, checkpoint):
        nonlocal failure_checkpoint_saves
        original_save(ticket_id, state, path, checkpoint)
        if checkpoint.invocation_status.get("proposal") == "failed":
            failure_checkpoint_saves += 1
            raise SystemExit("stopped after first failure checkpoint")

    monkeypatch.setattr(
        main, "_save_planning_checkpoint", stop_after_first_failure_checkpoint
    )

    with pytest.raises(SystemExit, match="first failure checkpoint"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    checkpoint = workflow.load_model(
        tmp_path / resumed.planning_checkpoint_path, PlanningCheckpoint
    )
    assert checkpoint.length_retry_status == {"proposal": "pending"}
    assert resumed.last_attempt == 1
    assert first_calls == [("proposal", False)]
    assert failure_checkpoint_saves == 1

    monkeypatch.setattr(main, "_save_planning_checkpoint", original_save)
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("analyst repeated")),
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: (_ for _ in ()).throw(AssertionError("outline repeated")),
    )
    resumed_calls = []

    def resumed_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        resumed_calls.append((requested.unit_key, retry))
        return raw_output(artifact(requested))

    monkeypatch.setattr(main, "kickoff_architect_artifact", resumed_artifact)

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "implementing"
    assert result.last_attempt == 1
    assert resumed_calls == [
        ("proposal", True),
        ("design", False),
        ("tasks", False),
        ("spec:crew-supervision", False),
    ]


def test_restart_after_length_retry_is_consumed_blocks_without_another_call(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)

    def first_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        if requested.unit_key == "proposal":
            return raw_output(artifact(requested))
        raise main.LengthFinishReasonError(
            completion=SimpleNamespace(usage={"total_tokens": 8000})
        )

    install_staged_architect(monkeypatch, first_artifact)
    original_save = main._save_planning_checkpoint

    def stop_after_pending(ticket_id, state, path, checkpoint):
        original_save(ticket_id, state, path, checkpoint)
        if getattr(checkpoint, "length_retry_status", {}).get("design") == "pending":
            raise SystemExit("stopped before retry consumption")

    monkeypatch.setattr(main, "_save_planning_checkpoint", stop_after_pending)
    with pytest.raises(SystemExit, match="before retry consumption"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    pending = workflow.load_execution("DEV-40")

    def stop_after_consumed(ticket_id, state, path, checkpoint):
        original_save(ticket_id, state, path, checkpoint)
        if getattr(checkpoint, "length_retry_status", {}).get("design") == "consumed":
            raise SystemExit("stopped after retry consumption")

    monkeypatch.setattr(main, "_save_planning_checkpoint", stop_after_consumed)
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda **_: (_ for _ in ()).throw(AssertionError("retry started before persistence")),
    )
    with pytest.raises(SystemExit, match="after retry consumption"):
        main.run_planning("DEV-40", "dev-40", pending)

    consumed = workflow.load_execution("DEV-40")
    consumed_digest = consumed.planning_checkpoint_sha256
    monkeypatch.setattr(main, "_save_planning_checkpoint", original_save)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda **_: calls.append(True),
    )

    result = main.run_planning("DEV-40", "dev-40", consumed)

    assert result.phase == "blocked"
    assert result.last_attempt == 1
    assert calls == []
    assert result.planning_checkpoint_sha256 == consumed_digest
    checkpoint = workflow.load_model(
        tmp_path / result.planning_checkpoint_path, PlanningCheckpoint
    )
    assert [unit.unit_key for unit in checkpoint.units] == ["proposal"]
    assert checkpoint.length_retry_status == {"design": "consumed"}
    assert workflow.file_sha256(tmp_path / result.planning_checkpoint_path) == consumed_digest


def test_outline_length_failure_is_not_retried(tmp_path, monkeypatch):
    prepare_planning_root(tmp_path, monkeypatch)

    class FakeLengthFinishReasonError(Exception):
        pass

    monkeypatch.setattr(main, "LengthFinishReasonError", FakeLengthFinishReasonError, raising=False)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: raw_output(contract()),
    )

    def outline_call(*, inputs):
        calls.append(inputs)
        raise FakeLengthFinishReasonError("length")

    monkeypatch.setattr(main, "kickoff_architect_outline", outline_call, raising=False)
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda **_: (_ for _ in ()).throw(AssertionError("artifact must not run")),
        raising=False,
    )

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert result.last_attempt == 1
    assert result.planning_checkpoint_path is None
    assert len(calls) == 1


def test_restart_reuses_outline_and_completed_units_in_the_same_attempt(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    first_calls = []

    def interrupted_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        first_calls.append(requested.unit_key)
        if requested.unit_key == "design":
            raise SystemExit("interrupted")
        return raw_output(artifact(requested), token_usage={"total_tokens": 5})

    install_staged_architect(monkeypatch, interrupted_artifact)
    initial = ExecutionState(ticket_id="DEV-40", change_id="dev-40")

    with pytest.raises(SystemExit, match="interrupted"):
        main.run_planning("DEV-40", "dev-40", initial)

    resumed = workflow.load_execution("DEV-40")
    assert resumed.phase == "planning"
    assert resumed.last_attempt == 1
    assert resumed.planning_checkpoint_sha256 == workflow.file_sha256(
        tmp_path / resumed.planning_checkpoint_path
    )
    assert first_calls == ["proposal", "design"]
    resumed_calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("analyst repeated")),
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: (_ for _ in ()).throw(AssertionError("outline repeated")),
        raising=False,
    )

    def resumed_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        resumed_calls.append(requested.unit_key)
        return raw_output(artifact(requested), token_usage={"total_tokens": 5})

    monkeypatch.setattr(main, "kickoff_architect_artifact", resumed_artifact, raising=False)

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "implementing"
    assert result.last_attempt == 1
    assert resumed_calls == ["design", "tasks", "spec:crew-supervision"]


def test_resume_blocks_when_checkpoint_file_is_replaced_by_stale_earlier_version(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    install_staged_architect(
        monkeypatch,
        lambda *, inputs, retry=False: raw_output(
            artifact(
                PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
            )
        ),
    )
    original_save = main._save_planning_checkpoint
    snapshots = []

    def stop_after_first_unit(ticket_id, state, path, checkpoint):
        original_save(ticket_id, state, path, checkpoint)
        snapshots.append(path.read_bytes())
        if len(checkpoint.units) == 1:
            raise SystemExit("stopped after first completed unit")

    monkeypatch.setattr(main, "_save_planning_checkpoint", stop_after_first_unit)
    with pytest.raises(SystemExit, match="first completed unit"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    checkpoint_path = tmp_path / resumed.planning_checkpoint_path
    expected_digest = resumed.planning_checkpoint_sha256
    assert len(snapshots) == 2
    checkpoint_path.write_bytes(snapshots[0])
    calls = []
    monkeypatch.setattr(main, "_save_planning_checkpoint", original_save)
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda **_: calls.append(True),
    )

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == []
    assert result.planning_checkpoint_sha256 == expected_digest
    assert "checkpoint" in result.phase_usage["blocked_reason"].lower()


def test_resume_blocks_instead_of_adopting_orphan_checkpoint_file(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)

    def interrupted_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        if requested.unit_key == "design":
            raise SystemExit("interrupted")
        return raw_output(artifact(requested))

    install_staged_architect(monkeypatch, interrupted_artifact)
    with pytest.raises(SystemExit, match="interrupted"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    checkpoint_path = tmp_path / resumed.planning_checkpoint_path
    assert checkpoint_path.is_file()
    resumed.planning_checkpoint_path = None
    resumed.planning_checkpoint_sha256 = None
    workflow.save_execution("DEV-40", resumed)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda **_: calls.append(True),
    )

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == []
    assert result.planning_checkpoint_path is None
    assert result.planning_checkpoint_sha256 is None
    assert "checkpoint" in result.phase_usage["blocked_reason"].lower()


def test_invalid_artifact_leaves_active_plan_unchanged(tmp_path, monkeypatch):
    change = prepare_planning_root(tmp_path, monkeypatch)

    def artifact_call(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        if requested.unit_key == "design":
            return raw_output(PlanArtifactUnit(artifact="tasks", content="wrong unit"))
        return raw_output(artifact(requested))

    install_staged_architect(monkeypatch, artifact_call)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert (change / "proposal.md").read_text(encoding="utf-8") == "old proposal"
    assert (change / "specs/old/spec.md").read_text(encoding="utf-8") == "old spec"
    assert not (change / "specs/crew-supervision/spec.md").exists()


def test_outline_empty_response_retries_once_without_using_length_budget(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    outline_calls = []

    def outline_call(*, inputs):
        outline_calls.append(inputs)
        if len(outline_calls) == 1:
            return SimpleNamespace(raw="")
        return raw_output(outline())

    install_staged_architect(
        monkeypatch,
        lambda *, inputs, retry=False: raw_output(
            artifact(
                PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
            )
        ),
    )
    monkeypatch.setattr(main, "kickoff_architect_outline", outline_call, raising=False)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "implementing"
    assert len(outline_calls) == 2
    assert result.contract_output_retry_state == {}
    assert result.planning_empty_response_retry_state == "consumed"
    assert result.planning_empty_response_retry_target == "outline"


def test_restart_after_outline_empty_retry_consumption_never_dispatches_it_again(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: raw_output(contract()),
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: SimpleNamespace(raw=""),
    )
    original_save = workflow.save_execution

    def stop_after_consumption(ticket_id, state):
        original_save(ticket_id, state)
        if state.planning_empty_response_retry_state == "consumed":
            raise SystemExit("stopped after outline retry consumption")

    monkeypatch.setattr(workflow, "save_execution", stop_after_consumption)
    with pytest.raises(SystemExit, match="outline retry consumption"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    assert resumed.planning_empty_response_retry_state == "consumed"
    assert resumed.planning_empty_response_retry_target == "outline"
    assert resumed.planning_checkpoint_path is None
    assert resumed.last_attempt == 1
    calls = []
    monkeypatch.setattr(workflow, "save_execution", original_save)
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: calls.append(True),
    )

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == []
    assert result.last_attempt == 1
    assert result.planning_empty_response_retry_state == "consumed"
    assert result.planning_empty_response_retry_target == "outline"


def test_restart_after_artifact_empty_retry_consumption_never_dispatches_it_again(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)

    def empty_artifact(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        if requested.unit_key == "proposal":
            return SimpleNamespace(raw="")
        return raw_output(artifact(requested))

    install_staged_architect(monkeypatch, empty_artifact)
    original_save = workflow.save_execution

    def stop_after_consumption(ticket_id, state):
        original_save(ticket_id, state)
        if state.planning_empty_response_retry_state == "consumed":
            raise SystemExit("stopped after artifact retry consumption")

    monkeypatch.setattr(workflow, "save_execution", stop_after_consumption)
    with pytest.raises(SystemExit, match="artifact retry consumption"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    checkpoint_path = tmp_path / resumed.planning_checkpoint_path
    checkpoint_digest = resumed.planning_checkpoint_sha256
    assert resumed.planning_empty_response_retry_state == "consumed"
    assert resumed.planning_empty_response_retry_target == "proposal"
    assert workflow.file_sha256(checkpoint_path) == checkpoint_digest
    assert resumed.last_attempt == 1
    calls = []
    monkeypatch.setattr(workflow, "save_execution", original_save)
    monkeypatch.setattr(
        main,
        "kickoff_architect_artifact",
        lambda **_: calls.append(True),
    )

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == []
    assert result.last_attempt == 1
    assert result.planning_checkpoint_sha256 == checkpoint_digest
    assert workflow.file_sha256(checkpoint_path) == checkpoint_digest


def test_empty_response_retry_budget_is_once_across_all_planning_units(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    counts = {"proposal": 0}

    def artifact_call(*, inputs, retry=False):
        requested = PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
        calls.append((requested.unit_key, retry))
        if requested.unit_key == "proposal":
            counts["proposal"] += 1
            return SimpleNamespace(raw="")
        pytest.fail("the consumed operation-wide retry must block before design")

    install_staged_architect(monkeypatch, artifact_call)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert calls == [
        ("proposal", False),
        ("proposal", False),
    ]
    assert result.contract_output_retry_state == {}
    assert result.planning_empty_response_retry_state == "consumed"
    assert result.planning_empty_response_retry_target == "proposal"
    assert result.last_attempt == 1


def test_empty_response_text_on_non_value_error_is_not_retried(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: raw_output(contract()),
    )

    def outline_call(*, inputs):
        calls.append(inputs)
        if len(calls) == 1:
            raise RuntimeError("empty contract output")
        return raw_output(outline())

    monkeypatch.setattr(main, "kickoff_architect_outline", outline_call)

    result = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )

    assert result.phase == "blocked"
    assert len(calls) == 1
    assert result.contract_output_retry_state == {}


def test_empty_response_retry_consumption_survives_outline_restart(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        main,
        "kickoff_role",
        lambda role, **_: raw_output(contract()),
    )

    def outline_call(*, inputs):
        calls.append(inputs)
        if len(calls) == 1:
            return SimpleNamespace(raw="")
        return raw_output(outline())

    monkeypatch.setattr(main, "kickoff_architect_outline", outline_call)
    original_save = workflow.save_execution

    def stop_after_pending(ticket_id, state):
        original_save(ticket_id, state)
        if state.planning_empty_response_retry_state == "pending":
            raise SystemExit("stopped after empty-response failure")

    monkeypatch.setattr(workflow, "save_execution", stop_after_pending)

    with pytest.raises(SystemExit, match="empty-response failure"):
        main.run_planning(
            "DEV-40",
            "dev-40",
            ExecutionState(ticket_id="DEV-40", change_id="dev-40"),
        )

    resumed = workflow.load_execution("DEV-40")
    assert resumed.planning_empty_response_retry_state == "pending"
    assert resumed.planning_empty_response_retry_target == "outline"
    assert resumed.last_attempt == 1

    monkeypatch.setattr(workflow, "save_execution", original_save)
    install_staged_architect(
        monkeypatch,
        lambda *, inputs, retry=False: raw_output(
            artifact(
                PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
            )
        ),
    )
    monkeypatch.setattr(main, "kickoff_architect_outline", outline_call)

    result = main.run_planning("DEV-40", "dev-40", resumed)

    assert result.phase == "implementing"
    assert result.planning_empty_response_retry_state == "consumed"
    assert result.planning_empty_response_retry_target == "outline"
    assert result.last_attempt == 1
    assert len(calls) == 2
    usage_dir = workflow.ticket_contract_path("dev-40", 1).parent
    usage = json.loads(
        (usage_dir / "phase-usage-planning-architect-outline-outline-1.json").read_text()
    )
    assert usage["status"] == "completed"


def test_resume_rejects_persisted_catalog_when_context_snapshot_changed(
    tmp_path, monkeypatch
):
    prepare_planning_root(tmp_path, monkeypatch)
    install_staged_architect(
        monkeypatch,
        lambda *, inputs, retry=False: raw_output(
            artifact(
                PlanUnitOutline.model_validate_json(inputs["plan_unit_outline_json"])
            )
        ),
    )
    state = main.run_planning(
        "DEV-40", "dev-40", ExecutionState(ticket_id="DEV-40", change_id="dev-40")
    )
    persisted = workflow.load_model(
        workflow.context_catalog_path("dev-40", 1), ProjectContextCatalog
    )
    (tmp_path / "CONTEXT.md").write_text(
        (tmp_path / "CONTEXT.md").read_text() + "\n## Changed\nNew context.\n"
    )
    monkeypatch.setattr(
        main,
        "kickoff_architect_outline",
        lambda **_: pytest.fail("stale context must block before Architect"),
    )

    result = main.run_planning("DEV-40", "dev-40", state)

    assert result.phase == "blocked"
    assert "context catalog" in result.phase_usage["blocked_reason"].lower()
    assert workflow.load_model(
        workflow.context_catalog_path("dev-40", 1), ProjectContextCatalog
    ) == persisted


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
    assert (
        tmp_path
        / "openspec/changes/dev-40/attempts/3/phase-usage-implementing-programmer-implementing-programmer-1.json"
    ).is_file()


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


def test_tester_invalid_contract_retry_does_not_block_the_next_browser_cycle(
    tmp_path, monkeypatch
):
    state = prepare_state(tmp_path, monkeypatch, phase="browser_testing", profile="browser")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "tester":
            tester_calls = calls.count("tester")
            if tester_calls == 1:
                return SimpleNamespace(raw="{invalid")
            if tester_calls == 2:
                return raw_output(TesterResult(status="failed", summary="repair needed"))
            return raw_output(TesterResult(status="passed", summary="repaired"))
        return SimpleNamespace(raw="fixed")

    monkeypatch.setattr(main, "kickoff_role", kickoff)
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())

    state = main.run_browser_testing("DEV-40", "dev-40", state)
    assert state.phase == "implementing"
    assert state.contract_output_retry_state == {}
    state = main.run_programmer("DEV-40", "dev-40", state)
    state = main.run_verification("DEV-40", "dev-40", state)
    result = main.run_browser_testing("DEV-40", "dev-40", state)

    assert result.phase == "reviewing"
    assert calls == ["tester", "tester", "programmer", "tester"]


def test_tester_retry_stays_consumed_until_browser_result_is_persisted(
    tmp_path, monkeypatch
):
    state = prepare_state(tmp_path, monkeypatch, phase="browser_testing", profile="browser")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if len(calls) == 1:
            return SimpleNamespace(raw="{invalid")
        return raw_output(TesterResult(status="passed", summary="passed"))

    monkeypatch.setattr(main, "kickoff_role", kickoff)
    original_save_model = workflow.save_model
    browser_path = workflow.browser_result_path("dev-40", state.last_attempt)

    def crash_after_browser_result(path, value):
        original_save_model(path, value)
        if path == browser_path:
            raise SystemExit("stopped after browser result persistence")

    monkeypatch.setattr(workflow, "save_model", crash_after_browser_result)
    with pytest.raises(SystemExit, match="browser result persistence"):
        main.run_browser_testing("DEV-40", "dev-40", state)

    resumed = workflow.load_execution("DEV-40")
    assert resumed.contract_output_retry_state == {"tester": "consumed"}
    monkeypatch.setattr(workflow, "save_model", original_save_model)

    result = main.run_browser_testing("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == ["tester", "tester"]


def test_failed_browser_tester_returns_only_to_programmer(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch, phase="browser_testing", profile="browser")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "tester":
            return raw_output(TesterResult(status="failed", summary="scenario failed"))
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
            return raw_output(
                ReviewVerdict(
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


def test_reviewer_invalid_contract_retry_does_not_block_the_next_repair_review(
    tmp_path, monkeypatch
):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if role == "reviewer":
            reviewer_calls = calls.count("reviewer")
            if reviewer_calls == 1:
                return SimpleNamespace(raw="{invalid")
            if reviewer_calls == 2:
                return raw_output(
                    ReviewVerdict(
                        ticket_id="DEV-40",
                        change_id="dev-40",
                        status="retryable_failure",
                        summary="repair needed",
                    )
                )
            return raw_output(
                ReviewVerdict(
                    ticket_id="DEV-40",
                    change_id="dev-40",
                    status="approved",
                    summary="approved",
                )
            )
        return SimpleNamespace(raw="fixed")

    monkeypatch.setattr(main, "kickoff_role", kickoff)
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")

    state = main.run_verification("DEV-40", "dev-40", state)
    state = main.run_review("DEV-40", "dev-40", state)
    assert state.phase == "implementing"
    assert state.contract_output_retry_state == {}
    state = main.run_programmer("DEV-40", "dev-40", state)
    state = main.run_verification("DEV-40", "dev-40", state)
    result = main.run_review("DEV-40", "dev-40", state)

    assert result.phase == "approved"
    assert calls == ["reviewer", "reviewer", "programmer", "reviewer"]


def test_reviewer_retry_stays_consumed_until_accepted_phase_is_persisted(
    tmp_path, monkeypatch
):
    state = prepare_state(tmp_path, monkeypatch, phase="verifying")
    calls = []

    def kickoff(role, **_):
        calls.append(role)
        if len(calls) == 1:
            return SimpleNamespace(raw="{invalid")
        return raw_output(
            ReviewVerdict(
                ticket_id="DEV-40",
                change_id="dev-40",
                status="approved",
                summary="approved",
            )
        )

    monkeypatch.setattr(main, "kickoff_role", kickoff)
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())
    monkeypatch.setattr(main, "_changed_paths", lambda: [])
    monkeypatch.setattr(main, "_diff_summary", lambda: "No changes.")
    state = main.run_verification("DEV-40", "dev-40", state)
    original_save_execution = workflow.save_execution

    def crash_before_reviewer_acknowledgement(ticket_id, value):
        original_save_execution(ticket_id, value)
        if (
            value.phase == "approved"
            and value.contract_output_retry_state == {"reviewer": "consumed"}
        ):
            raise SystemExit("stopped after accepted reviewer phase")

    monkeypatch.setattr(workflow, "save_execution", crash_before_reviewer_acknowledgement)
    with pytest.raises(SystemExit, match="accepted reviewer phase"):
        main.run_review("DEV-40", "dev-40", state)

    resumed = workflow.load_execution("DEV-40")
    assert resumed.contract_output_retry_state == {"reviewer": "consumed"}
    monkeypatch.setattr(workflow, "save_execution", original_save_execution)

    result = main.run_review("DEV-40", "dev-40", resumed)

    assert result.phase == "blocked"
    assert calls == ["reviewer", "reviewer"]


def test_replan_atomically_clears_current_contract_references_before_running(tmp_path, monkeypatch):
    state = prepare_state(tmp_path, monkeypatch)
    state.repair_pack_path = "openspec/changes/dev-40/attempts/2/repair-pack.json"
    state.review_pack_path = "openspec/changes/dev-40/attempts/2/review-pack.json"
    state.browser_result_path = "openspec/changes/dev-40/attempts/2/browser-result.json"
    state.planning_checkpoint_path = "openspec/changes/dev-40/attempts/2/planning-checkpoint.json"
    state.planning_checkpoint_sha256 = "c" * 64
    state.contract_output_retry_state = {"architect:artifact:proposal": "consumed"}
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
    assert saved[0].planning_checkpoint_path is None
    assert saved[0].planning_checkpoint_sha256 is None
    assert saved[0].contract_output_retry_state == {}
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
        lambda *_args, **_kwargs: raw_output(
            ReviewVerdict(
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
            return raw_output(
                ReviewVerdict(
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
