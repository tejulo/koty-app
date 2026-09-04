import hashlib
import json
import re
from pathlib import Path

from .models import (
    PlanArtifactUnit,
    PlanDraft,
    PlanDraftSpec,
    PlanOutline,
    ProjectContextCatalog,
    ProjectContextSection,
    TicketContract,
)


HEADING = re.compile(r"^(#{2,3})[ \t]+(.+?)[ \t]*(?:\r?\n)?$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _section_headings(content: str) -> list[tuple[int, int, str]]:
    headings = []
    fence: tuple[str, int] | None = None
    offset = 0
    for line in content.splitlines(keepends=True):
        if fence:
            marker, width = fence
            if re.fullmatch(
                rf" {{0,3}}{re.escape(marker)}{{{width},}}[ \t]*(?:\r?\n)?",
                line,
            ):
                fence = None
        else:
            opening = FENCE.match(line)
            if opening:
                fence = (opening.group(1)[0], len(opening.group(1)))
            else:
                heading = HEADING.match(line)
                if heading:
                    headings.append((offset, offset + len(line), line.strip()))
        offset += len(line)
    return headings


def build_context_catalog(path: Path) -> ProjectContextCatalog:
    snapshot = path.read_bytes()
    content = snapshot.decode("utf-8")
    headings = _section_headings(content)
    sections = []
    for index, (_, body_start, heading) in enumerate(headings, start=1):
        end = headings[index][0] if index < len(headings) else len(content)
        body = content[body_start:end].strip()
        sections.append(
            ProjectContextSection(
                ref=f"context-{index:03d}",
                heading=heading,
                body=body,
                size=len(body),
            )
        )
    return ProjectContextCatalog(
        source_path=str(path),
        source_sha256=hashlib.sha256(snapshot).hexdigest(),
        sections=sections,
    )


def render_context_index(catalog: ProjectContextCatalog) -> str:
    return json.dumps(
        {
            "source_path": catalog.source_path,
            "source_sha256": catalog.source_sha256,
            "sections": [
                {
                    "ref": section.ref,
                    "heading": section.heading,
                    "size": section.size,
                }
                for section in catalog.sections
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def render_context_bundle(
    catalog: ProjectContextCatalog,
    refs: list[str],
    max_refs: int,
    max_chars: int,
) -> str:
    if max_refs < 0 or max_chars < 0:
        raise ValueError("context limits cannot be negative")
    if len(refs) != len(set(refs)):
        raise ValueError("context selection contains duplicate refs")
    sections = {section.ref: section for section in catalog.sections}
    unknown = sorted(set(refs) - set(sections))
    if unknown:
        raise ValueError("context selection contains unknown refs: " + ", ".join(unknown))
    if len(refs) > max_refs:
        raise ValueError(f"context selection exceeds {max_refs} references")
    bundle = "\n\n".join(
        f"[{ref}] {sections[ref].heading}\n\n{sections[ref].body}".rstrip()
        for ref in refs
    )
    if len(bundle) > max_chars:
        raise ValueError(f"context selection exceeds {max_chars} characters")
    return bundle


def validate_plan_outline(
    outline: PlanOutline,
    contract: TicketContract,
    catalog: ProjectContextCatalog,
    max_refs: int,
    max_chars: int,
) -> PlanOutline:
    PlanOutline.model_validate(outline.model_dump())
    expected = {criterion.id for criterion in contract.acceptance_criteria}
    actual = set(outline.acceptance_map)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise ValueError("PlanOutline acceptance coverage is invalid: " + "; ".join(details))
    empty = sorted(
        criterion
        for criterion, tasks in outline.acceptance_map.items()
        if not tasks or any(not task.strip() for task in tasks)
    )
    if empty:
        raise ValueError("PlanOutline has empty acceptance mappings: " + ", ".join(empty))
    for unit in outline.units:
        render_context_bundle(catalog, unit.context_refs, max_refs, max_chars)
    return outline


def assemble_plan_draft(
    outline: PlanOutline,
    units: list[PlanArtifactUnit],
) -> PlanDraft:
    PlanOutline.model_validate(outline.model_dump())
    validated = [PlanArtifactUnit.model_validate(unit.model_dump()) for unit in units]
    keys = [unit.unit_key for unit in validated]
    if len(keys) != len(set(keys)):
        raise ValueError("artifact units contain duplicate units")
    by_key = {unit.unit_key: unit for unit in validated}
    expected = {unit.unit_key for unit in outline.units}
    missing = sorted(expected - set(by_key))
    unexpected = sorted(set(by_key) - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise ValueError("artifact unit set is invalid: " + "; ".join(details))
    specs = [
        PlanDraftSpec(
            capability=unit.capability,
            content=by_key[unit.unit_key].content,
        )
        for unit in outline.units
        if unit.artifact == "spec"
    ]
    return PlanDraft(
        profile=outline.profile,
        proposal=by_key["proposal"].content,
        design=by_key["design"].content,
        tasks=by_key["tasks"].content,
        specs=specs,
        acceptance_map=outline.acceptance_map,
    )
