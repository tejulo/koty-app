import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from crew.models import (
    AcceptanceCriterion,
    PlanArtifactUnit,
    PlanningCheckpoint,
    PlanOutline,
    PlanUnitOutline,
    ProjectContextSection,
    TicketContract,
)
from crew.planning import (
    assemble_plan_draft,
    build_context_catalog,
    render_context_bundle,
    render_context_index,
    validate_plan_outline,
)


def contract(*criteria: str) -> TicketContract:
    return TicketContract(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256="a" * 64,
        acceptance_criteria=[
            AcceptanceCriterion(id=criterion, text=f"Cover {criterion}")
            for criterion in criteria
        ],
        objective="Generate a staged plan.",
        in_scope=["crewai"],
        constraints=[],
        dependencies=[],
        ambiguities=[],
    )


def write_context(path: Path) -> Path:
    path.write_text(
        "# Project\n\nPreamble that is not a selectable section.\n\n"
        "## Alpha\n\nALPHA_BODY\n\n"
        "### Alpha detail\n\nALPHA_DETAIL_BODY\n\n"
        "## Beta\n\nBETA_BODY\n",
        encoding="utf-8",
    )
    return path


def outline(*, refs: list[str] | None = None) -> PlanOutline:
    selected = refs or []
    return PlanOutline(
        profile="operational",
        units=[
            PlanUnitOutline(
                artifact="proposal",
                objective="Explain the change.",
                context_refs=selected,
            ),
            PlanUnitOutline(
                artifact="design",
                objective="Describe the design.",
                context_refs=[],
            ),
            PlanUnitOutline(
                artifact="tasks",
                objective="List implementation tasks.",
                context_refs=[],
            ),
            PlanUnitOutline(
                artifact="spec",
                capability="crew-supervision",
                objective="Specify supervision behavior.",
                context_refs=[],
            ),
        ],
        acceptance_map={"AC-001": ["T-001"], "AC-002": ["T-002"]},
    )


def canonical_digest(model) -> str:
    content = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_context_catalog_parses_h2_h3_boundaries_and_index_omits_bodies(tmp_path):
    catalog = build_context_catalog(write_context(tmp_path / "CONTEXT.md"))

    assert [section.ref for section in catalog.sections] == [
        "context-001",
        "context-002",
        "context-003",
    ]
    assert [section.heading for section in catalog.sections] == [
        "## Alpha",
        "### Alpha detail",
        "## Beta",
    ]
    assert [section.body for section in catalog.sections] == [
        "ALPHA_BODY",
        "ALPHA_DETAIL_BODY",
        "BETA_BODY",
    ]

    index = render_context_index(catalog)
    assert "context-001" in index
    assert "## Alpha" in index
    assert '"size":10' in index
    assert "ALPHA_BODY" not in index
    assert "ALPHA_DETAIL_BODY" not in index
    assert "BETA_BODY" not in index


def test_context_catalog_hashes_and_decodes_one_byte_snapshot():
    snapshot = b"## Snapshot\n\nBYTE_BODY\n"

    class ChangingPath:
        byte_reads = 0
        text_reads = 0

        def read_bytes(self):
            self.byte_reads += 1
            return snapshot

        def read_text(self, *, encoding):
            self.text_reads += 1
            return "## Stale\n\nSTALE_BODY\n"

        def __str__(self):
            return "CONTEXT.md"

    path = ChangingPath()
    catalog = build_context_catalog(path)

    assert catalog.source_sha256 == hashlib.sha256(snapshot).hexdigest()
    assert catalog.sections[0].heading == "## Snapshot"
    assert catalog.sections[0].body == "BYTE_BODY"
    assert path.byte_reads == 1
    assert path.text_reads == 0


def test_context_catalog_ignores_headings_inside_backtick_and_tilde_fences(tmp_path):
    path = tmp_path / "CONTEXT.md"
    path.write_text(
        "## Real\n\nBEFORE\n\n"
        "```markdown\n## Backtick example\n```\n\n"
        "~~~text\n### Tilde example\n~~~\n\n"
        "### Child\n\nCHILD_BODY\n",
        encoding="utf-8",
    )

    catalog = build_context_catalog(path)

    assert [section.heading for section in catalog.sections] == [
        "## Real",
        "### Child",
    ]
    assert "## Backtick example" in catalog.sections[0].body
    assert "### Tilde example" in catalog.sections[0].body
    assert catalog.sections[1].body == "CHILD_BODY"


def test_context_bundle_contains_only_selected_sections(tmp_path):
    catalog = build_context_catalog(write_context(tmp_path / "CONTEXT.md"))

    bundle = render_context_bundle(
        catalog,
        ["context-003", "context-001"],
        max_refs=2,
        max_chars=1_000,
    )

    assert "## Beta" in bundle
    assert "BETA_BODY" in bundle
    assert "## Alpha" in bundle
    assert "ALPHA_BODY" in bundle
    assert bundle.index("BETA_BODY") < bundle.index("ALPHA_BODY")
    assert "ALPHA_DETAIL_BODY" not in bundle


@pytest.mark.parametrize(
    ("refs", "max_refs", "max_chars", "message"),
    [
        (["missing"], 1, 1_000, "unknown"),
        (["context-001", "context-001"], 2, 1_000, "duplicate"),
        (["context-001", "context-002"], 1, 1_000, "references"),
        (["context-001"], 1, 5, "characters"),
    ],
)
def test_context_bundle_rejects_invalid_or_oversized_selections(
    tmp_path, refs, max_refs, max_chars, message
):
    catalog = build_context_catalog(write_context(tmp_path / "CONTEXT.md"))

    with pytest.raises(ValueError, match=message):
        render_context_bundle(catalog, refs, max_refs, max_chars)


def test_plan_outline_requires_exactly_one_of_each_core_unit_and_valid_specs():
    valid = outline()
    proposal = valid.units[0]

    with pytest.raises(ValidationError, match="duplicate"):
        PlanOutline(
            profile=valid.profile,
            units=[*valid.units, proposal],
            acceptance_map=valid.acceptance_map,
        )

    with pytest.raises(ValidationError, match="design"):
        PlanOutline(
            profile=valid.profile,
            units=[unit for unit in valid.units if unit.artifact != "design"],
            acceptance_map=valid.acceptance_map,
        )

    with pytest.raises(ValidationError, match="capability"):
        PlanUnitOutline(
            artifact="spec",
            objective="Missing capability.",
            context_refs=[],
        )

    with pytest.raises(ValidationError, match="capability"):
        PlanUnitOutline(
            artifact="proposal",
            capability="not-allowed",
            objective="Core unit with capability.",
            context_refs=[],
        )

    with pytest.raises(ValidationError, match="extra"):
        PlanUnitOutline(
            artifact="proposal",
            objective="No uncontracted data.",
            context_refs=[],
            extra="forbidden",
        )


def test_planning_contract_identifiers_require_full_pattern_matches():
    with pytest.raises(ValidationError, match="ref"):
        ProjectContextSection(
            ref="context-001-extra",
            heading="## Heading",
            body="",
            size=0,
        )

    with pytest.raises(ValidationError, match="capability"):
        PlanArtifactUnit(
            artifact="spec",
            capability="crew-supervision!",
            content="spec",
        )


@pytest.mark.parametrize(
    ("model", "values", "field"),
    [
        (
            ProjectContextSection,
            {"ref": "context-001", "heading": "## Heading", "body": "body", "size": "4"},
            "size",
        ),
        (
            PlanUnitOutline,
            {"artifact": "proposal", "objective": "Propose", "context_refs": ()},
            "context_refs",
        ),
        (
            PlanArtifactUnit,
            {"schema_version": "1", "artifact": "proposal", "content": "proposal"},
            "schema_version",
        ),
    ],
)
def test_strict_planning_contracts_reject_coercion(model, values, field):
    with pytest.raises(ValidationError, match=field):
        model(**values)


@pytest.mark.parametrize(
    ("model", "values", "field"),
    [
        (
            PlanUnitOutline,
            {"artifact": "proposal", "objective": " \n\t", "context_refs": []},
            "objective",
        ),
        (
            PlanArtifactUnit,
            {"artifact": "proposal", "content": " \n\t"},
            "content",
        ),
    ],
)
def test_planning_units_reject_whitespace_only_text(model, values, field):
    with pytest.raises(ValidationError, match=field):
        model(**values)


def test_validate_plan_outline_requires_exact_ac_coverage_and_bounded_known_refs(
    tmp_path,
):
    catalog = build_context_catalog(write_context(tmp_path / "CONTEXT.md"))
    valid = outline(refs=["context-001"])

    assert (
        validate_plan_outline(
            valid,
            contract("AC-001", "AC-002"),
            catalog,
            max_refs=1,
            max_chars=1_000,
        )
        is valid
    )

    for acceptance_map, message in [
        ({"AC-001": ["T-001"]}, "AC-002"),
        (
            {
                "AC-001": ["T-001"],
                "AC-002": ["T-002"],
                "AC-003": ["T-003"],
            },
            "AC-003",
        ),
        ({"AC-001": [], "AC-002": ["T-002"]}, "empty"),
    ]:
        invalid = valid.model_copy(update={"acceptance_map": acceptance_map})
        with pytest.raises(ValueError, match=message):
            validate_plan_outline(invalid, contract("AC-001", "AC-002"), catalog, 1, 1_000)

    unknown = valid.model_copy(
        update={
            "units": [
                valid.units[0].model_copy(update={"context_refs": ["missing"]}),
                *valid.units[1:],
            ]
        }
    )
    with pytest.raises(ValueError, match="unknown"):
        validate_plan_outline(unknown, contract("AC-001", "AC-002"), catalog, 1, 1_000)

    oversized = valid.model_copy(
        update={
            "units": [
                valid.units[0].model_copy(
                    update={"context_refs": ["context-001", "context-002"]}
                ),
                *valid.units[1:],
            ]
        }
    )
    with pytest.raises(ValueError, match="references"):
        validate_plan_outline(oversized, contract("AC-001", "AC-002"), catalog, 1, 1_000)


def test_assemble_plan_draft_preserves_existing_compatibility_shape():
    plan = outline()
    units = [
        PlanArtifactUnit(artifact="proposal", content="# Proposal"),
        PlanArtifactUnit(
            artifact="design",
            content="verification_profile: operational",
        ),
        PlanArtifactUnit(artifact="tasks", content="- [ ] T-001"),
        PlanArtifactUnit(
            artifact="spec",
            capability="crew-supervision",
            content="## ADDED Requirements",
        ),
    ]

    draft = assemble_plan_draft(plan, units)

    assert draft.model_dump() == {
        "profile": "operational",
        "proposal": "# Proposal",
        "design": "verification_profile: operational",
        "tasks": "- [ ] T-001",
        "specs": [
            {
                "capability": "crew-supervision",
                "content": "## ADDED Requirements",
            }
        ],
        "acceptance_map": {"AC-001": ["T-001"], "AC-002": ["T-002"]},
    }

    with pytest.raises(ValueError, match="missing"):
        assemble_plan_draft(plan, units[:-1])


def test_planning_checkpoint_verifies_embedded_outline_and_unit_hashes():
    plan = outline()
    unit = PlanArtifactUnit(artifact="proposal", content="# Proposal")
    values = {
        "ticket_contract_sha256": "a" * 64,
        "context_catalog_sha256": "b" * 64,
        "outline_sha256": canonical_digest(plan),
        "outline": plan,
        "units": [unit],
        "unit_sha256": {"proposal": canonical_digest(unit)},
        "invocation_status": {"proposal": "completed"},
    }

    checkpoint = PlanningCheckpoint(**values)

    assert checkpoint.units == [unit]
    with pytest.raises(ValidationError, match="outline hash"):
        PlanningCheckpoint(**{**values, "outline_sha256": "c" * 64})
    with pytest.raises(ValidationError, match="unit hash"):
        PlanningCheckpoint(
            **{**values, "unit_sha256": {"proposal": "d" * 64}}
        )


def test_planning_checkpoint_requires_completed_status_to_have_a_stored_unit():
    plan = outline()
    values = {
        "ticket_contract_sha256": "a" * 64,
        "context_catalog_sha256": "b" * 64,
        "outline_sha256": canonical_digest(plan),
        "outline": plan,
        "invocation_status": {"proposal": "pending", "design": "failed"},
    }

    PlanningCheckpoint(**values)
    with pytest.raises(ValidationError, match="completed"):
        PlanningCheckpoint(
            **{**values, "invocation_status": {"proposal": "completed"}}
        )


@pytest.mark.parametrize("status", [None, "pending", "failed"])
def test_planning_checkpoint_requires_stored_unit_status_to_be_completed(status):
    plan = outline()
    unit = PlanArtifactUnit(artifact="proposal", content="# Proposal")
    invocation_status = {} if status is None else {"proposal": status}

    with pytest.raises(ValidationError, match="completed"):
        PlanningCheckpoint(
            ticket_contract_sha256="a" * 64,
            context_catalog_sha256="b" * 64,
            outline_sha256=canonical_digest(plan),
            outline=plan,
            units=[unit],
            unit_sha256={"proposal": canonical_digest(unit)},
            invocation_status=invocation_status,
        )
