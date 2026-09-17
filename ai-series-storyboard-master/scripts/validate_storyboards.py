#!/usr/bin/env python3
"""Validate AI Series Storyboard Master scene plans and segment prompts."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


VERSION = r"(?:v\d+\.\d+|draft-v0\.\d+)"
STYLE_RE = re.compile(rf"STYLE-BASE-{VERSION}")
INDEX_RE = re.compile(rf"ASSET-INDEX-{VERSION}")
PLAN_RE = re.compile(rf"(?P<scene>EP\d{{3}}-SC\d{{3}})-PLAN-(?P<version>{VERSION})")
SEGMENT_RE = re.compile(rf"(?P<scene>EP\d{{3}}-SC\d{{3}})-SEG(?P<number>\d{{3}})-(?P<version>{VERSION})")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
ONTOLOGY_PATTERNS = {
    "live-action": re.compile(r"\b(?:live[- ]action|real actors?)\b", re.I),
    "animation": re.compile(r"\b(?:animation|animated|anime|donghua|cartoon)\b", re.I),
    "2d": re.compile(
        r"\b(?:2d|two[- ]dimensional|hand[- ]drawn|cel animation|ink(?:-wash)? animation)\b",
        re.I,
    ),
    "3d": re.compile(r"\b(?:3d|three[- ]dimensional|cg animation|cgi animation)\b", re.I),
    "motion-comic": re.compile(r"\b(?:motion[- ]comic|manhua|manga[- ]drama)\b", re.I),
    "stop-motion": re.compile(r"\bstop[- ]motion\b", re.I),
    "hybrid": re.compile(r"\b(?:hybrid animation|mixed[- ]media animation)\b", re.I),
}
SPECIFIC_ONTOLOGY_TRAITS = frozenset(
    {"live-action", "2d", "3d", "motion-comic", "stop-motion", "hybrid"}
)
NEGATED_ONTOLOGY_PREFIX_RE = re.compile(
    r"(?:\b(?:no|not|never|without|avoid(?:s|ed|ing)?|exclude(?:s|d|ing)?|"
    r"reject(?:s|ed|ing)?)\b|anti[- ])(?:(?!\b(?:but|instead)\b|[,.;:]).){0,80}$",
    re.I | re.S,
)
DISALLOWED_OUTPUT_MODE_RE = re.compile(
    r"\b(?:game ui|character selection screen|skill icon sheet|key art|concept art sheet|"
    r"commercial advertising|product advertising)\b",
    re.I,
)
HIGH_IMPACT_TERMS = (
    "noir",
    "horror",
    "surreal",
    "pastel",
    "neon",
    "teal and orange",
    "teal-orange",
    "glossy",
    "premium",
    "cyberpunk",
    "atompunk",
)


@dataclass
class Result:
    path: Path
    kind: str
    errors: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


@dataclass
class Asset:
    asset_id: str
    kind: str
    relative_file: str
    reference_label: str
    base: str


@dataclass
class CatalogEntry:
    segment_id: str
    duration: float
    characters: tuple[str, ...]
    crowds: tuple[str, ...]
    scene: str
    props: tuple[str, ...]
    source_ids: tuple[str, ...]


@dataclass
class PlanContext:
    path: Path
    plan_id: str
    scene_id: str
    metadata: dict[str, str]
    registry: dict[str, tuple[str, str]]
    catalog: dict[str, CatalogEntry]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ontology_traits(text: str) -> frozenset[str]:
    traits: set[str] = set()
    for name, pattern in ONTOLOGY_PATTERNS.items():
        for match in pattern.finditer(text):
            prefix = text[max(0, match.start() - 100) : match.start()]
            if not NEGATED_ONTOLOGY_PREFIX_RE.search(prefix):
                traits.add(name)
                break
    return frozenset(traits)


def style_ontology_text(body: str) -> str:
    labeled = re.search(
        r"Visual ontology:\s*(?P<body>.+?)(?=(?:World and period|World and cultivation system|"
        r"Production design|Shape language):)",
        body,
        re.I | re.S,
    )
    if labeled:
        return labeled.group("body").strip()
    return " ".join(body.split()[:60])


def metadata(raw: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in raw.splitlines()[1:]:
        if line.startswith("### "):
            break
        match = re.fullmatch(r"- ([a-z-]+): (.+)", line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def required_metadata(result: Result, values: dict[str, str], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in values:
            result.errors.append(f"missing metadata: {key}")


def fenced_section(raw: str, heading: str) -> str | None:
    pattern = rf"^### {re.escape(heading)}\r?\n~~~text\r?\n(.+?)\r?\n~~~(?:\r?\n|\Z)"
    match = re.search(pattern, raw, re.M | re.S)
    return match.group(1).strip() if match else None


def table_rows(raw: str, heading: str) -> list[list[str]]:
    match = re.search(
        rf"^### {re.escape(heading)}\r?\n(?P<table>(?:\|.*\r?\n?)+?)(?=\r?\n(?:\r?\n)*### |\Z)",
        raw,
        re.M,
    )
    if not match:
        return []
    rows: list[list[str]] = []
    for line in match.group("table").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"Asset ID", "Segment ID"}:
            continue
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def parse_id_list(value: str, prefix: str | None = None) -> tuple[str, ...]:
    if value == "none":
        return ()
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    if prefix:
        for item in items:
            if not re.fullmatch(rf"{prefix}-\d{{3}}", item):
                raise ValueError(f"invalid {prefix} asset ID: {item}")
    if len(items) != len(set(items)):
        raise ValueError(f"duplicate IDs: {value}")
    return items


def parse_asset_files(value: str) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"invalid asset-files binding: {part}")
        asset_id, relative_file = (piece.strip() for piece in part.split("=", 1))
        if not re.fullmatch(r"(?:CHAR|CROWD|SCN|PROP)-\d{3}", asset_id):
            raise ValueError(f"invalid asset-files ID: {asset_id}")
        if asset_id in bindings:
            raise ValueError(f"duplicate asset-files ID: {asset_id}")
        bindings[asset_id] = relative_file
    return bindings


def parse_duration(value: str) -> float:
    match = re.fullmatch(r"(?P<value>\d+(?:\.\d+)?)s", value)
    if not match:
        raise ValueError(f"invalid duration: {value}")
    duration = float(match.group("value"))
    if not 0 < duration <= 10:
        raise ValueError(f"duration {duration:g}s is outside >0 and <=10s")
    return duration


def validate_style(path: Path) -> tuple[str, str, frozenset[str]]:
    if not path.is_file():
        raise ValueError(f"missing STYLE-BASE: {path}")
    raw = read(path)
    match = re.search(rf"^## (?P<id>STYLE-BASE-{VERSION})$", raw, re.M)
    if not match or path.name != f"{match.group('id')}.md":
        raise ValueError(f"invalid STYLE-BASE: {path}")
    body_match = re.search(r"~~~text\r?\n(?P<body>.+?)\r?\n~~~", raw, re.S)
    if not body_match:
        raise ValueError(f"STYLE-BASE has no text prompt: {path}")
    traits = ontology_traits(style_ontology_text(body_match.group("body")))
    if not traits & SPECIFIC_ONTOLOGY_TRAITS:
        raise ValueError(f"STYLE-BASE has no recognizable visual ontology: {path}")
    return match.group("id"), raw, traits


def load_entity(
    art_root: Path,
    asset_id: str,
    kind: str,
    relative_file: str,
    reference_label: str,
    style_id: str,
) -> Asset:
    path = art_root / Path(relative_file)
    if not path.is_file():
        raise ValueError(f"missing asset file for {asset_id}: {path}")
    if path.name != Path(relative_file).name:
        raise ValueError(f"invalid asset path for {asset_id}")
    raw = read(path)
    kind_contracts = {
        "character": ("CHAR", "Character Base"),
        "crowd": ("CROWD", "Crowd Base"),
        "scene": ("SCN", "Scene Base"),
        "prop": ("PROP", "Prop Base"),
    }
    prefix, base_heading = kind_contracts[kind]
    heading = re.match(rf"\A## (?P<id>{prefix}-\d{{3}})-(?P<version>{VERSION})｜[^\r\n]+\r?\n", raw)
    if not heading or heading.group("id") != asset_id:
        raise ValueError(f"asset heading mismatch for {asset_id}")
    expected_name = f"{asset_id}-{heading.group('version')}.md"
    if path.name != expected_name:
        raise ValueError(f"asset filename mismatch for {asset_id}")
    values = metadata(raw)
    if values.get("inherits-style") != style_id:
        raise ValueError(f"asset {asset_id} does not inherit {style_id}")
    if values.get("reference-label") != reference_label:
        raise ValueError(f"asset reference label mismatch for {asset_id}")
    base = fenced_section(raw, base_heading)
    if base is None:
        raise ValueError(f"missing {base_heading} for {asset_id}")
    return Asset(asset_id, kind, relative_file, reference_label, base)


def load_approved_index(path: Path, style_id: str) -> tuple[str, dict[str, Asset]]:
    if not path.is_file():
        raise ValueError(f"missing ASSET-INDEX: {path}")
    raw = read(path)
    heading = re.match(rf"\A## (?P<id>ASSET-INDEX-{VERSION})\r?\n", raw)
    if not heading or path.name != f"{heading.group('id')}.md":
        raise ValueError(f"invalid ASSET-INDEX: {path}")
    values = metadata(raw)
    if values.get("status") != "approved":
        raise ValueError(f"ASSET-INDEX is not approved: {path}")
    if values.get("inherits-style") != style_id:
        raise ValueError(f"ASSET-INDEX does not inherit {style_id}")

    assets: dict[str, Asset] = {}
    art_root = path.parent
    for table_heading, prefix, kind, folder in (
        ("主要角色", "CHAR", "character", "characters"),
        ("群众演员", "CROWD", "crowd", "crowds"),
        ("核心场景", "SCN", "scene", "scenes"),
        ("重要道具", "PROP", "prop", "props"),
    ):
        rows = table_rows(raw, table_heading)
        for row in rows:
            if len(row) != 6:
                raise ValueError(f"invalid row in {table_heading}")
            asset_id, _, _, _, relative_file, reference_label = row
            if not re.fullmatch(rf"{prefix}-\d{{3}}", asset_id):
                raise ValueError(f"invalid asset ID in index: {asset_id}")
            if asset_id in assets:
                raise ValueError(f"duplicate asset ID in index: {asset_id}")
            if not re.fullmatch(rf"{folder}/{asset_id}-{VERSION}\.md", relative_file):
                raise ValueError(f"invalid current file for {asset_id}")
            file_version = relative_file.removesuffix(".md").split(f"{asset_id}-", 1)[1]
            if reference_label != f"@{asset_id}-REF-{file_version}":
                raise ValueError(f"invalid reference label for {asset_id}")
            assets[asset_id] = load_entity(
                art_root,
                asset_id,
                kind,
                relative_file,
                reference_label,
                style_id,
            )
    if not any(asset.kind == "scene" for asset in assets.values()):
        raise ValueError("approved ASSET-INDEX has no core scene assets")
    return heading.group("id"), assets


def validate_common_metadata(
    result: Result,
    values: dict[str, str],
    style_id: str,
    scene_id: str,
    script_path: Path,
) -> None:
    required_metadata(
        result,
        values,
        (
            "inherits-style",
            "asset-index-snapshot",
            "source",
            "source-scene",
            "coverage",
            "status",
            "scene-asset",
            "asset-files",
            "reference-calls",
        ),
    )
    if values.get("inherits-style") != style_id:
        result.errors.append(f"inherits-style must be {style_id}")
    if not INDEX_RE.fullmatch(values.get("asset-index-snapshot", "")):
        result.errors.append("invalid asset-index-snapshot")
    if Path(values.get("source", "")).name != script_path.name:
        result.errors.append("source does not identify the selected script")
    if values.get("source-scene") != scene_id:
        result.errors.append(f"source-scene must be {scene_id}")
    if values.get("coverage") not in {"complete", "draft"}:
        result.errors.append("coverage must be complete or draft")
    if values.get("status") not in {"ready-for-review", "approved"}:
        result.errors.append("status must be ready-for-review or approved")


def validate_asset_bindings(
    result: Result,
    values: dict[str, str],
    assets: dict[str, Asset],
    raw: str,
) -> tuple[tuple[str, ...], tuple[str, ...], str, tuple[str, ...]] | None:
    try:
        characters = parse_id_list(values.get("character-assets", "none"), "CHAR")
        crowds = parse_id_list(values.get("crowd-assets", "none"), "CROWD")
        scene_ids = parse_id_list(values.get("scene-asset", ""), "SCN")
        props = parse_id_list(values.get("prop-assets", "none"), "PROP")
        bindings = parse_asset_files(values.get("asset-files", ""))
        references = parse_id_list(values.get("reference-calls", ""))
    except ValueError as error:
        result.errors.append(str(error))
        return None
    if len(scene_ids) != 1:
        result.errors.append("scene-asset must contain exactly one SCN ID")
        return None
    scene_id = scene_ids[0]
    used_ids = (*characters, *crowds, scene_id, *props)
    if set(bindings) != set(used_ids):
        result.errors.append("asset-files does not match the used asset IDs")
    unknown = sorted(set(used_ids) - set(assets))
    if unknown:
        result.errors.append(f"assets missing from approved index: {', '.join(unknown)}")
    for asset_id in used_ids:
        if asset_id in assets and bindings.get(asset_id) != assets[asset_id].relative_file:
            result.errors.append(f"stale asset file for {asset_id}")
    expected_refs = {assets[item].reference_label for item in used_ids if item in assets}
    if set(references) != expected_refs:
        result.errors.append("reference-calls does not match approved asset labels")
    raw_asset_ids = set(re.findall(r"(?<![A-Z])(?:CHAR|CROWD|SCN|PROP)-\d{3}(?!\d)", raw))
    raw_unknown = sorted(raw_asset_ids - set(assets))
    if raw_unknown:
        result.errors.append(f"unapproved asset IDs appear in artifact: {', '.join(raw_unknown)}")
    return characters, crowds, scene_id, props


def require_numbered_fields(result: Result, raw: str, labels: tuple[str, ...]) -> None:
    for number, label in enumerate(labels, 1):
        if not re.search(rf"^{number}\. {re.escape(label)}：\S", raw, re.M):
            result.errors.append(f"missing field {number}: {label}")


def parse_registry(result: Result, raw: str, script_raw: str) -> dict[str, tuple[str, str]]:
    body = fenced_section(raw, "Source Text Registry")
    if body is None:
        result.errors.append("missing Source Text Registry")
        return {}
    if body == "none":
        return {}
    registry: dict[str, tuple[str, str]] = {}
    allowed_kinds = {"Dialogue", "Voice-over", "On-screen text"}
    for expected, line in enumerate(body.splitlines(), 1):
        parts = [part.strip() for part in line.split("|", 3)]
        if len(parts) != 4:
            result.errors.append(f"invalid Source Text Registry line: {line}")
            continue
        source_id, kind, speaker, text = parts
        expected_id = f"D{expected:03d}"
        if source_id != expected_id:
            result.errors.append(f"source text IDs must be contiguous; expected {expected_id}")
        if kind not in allowed_kinds:
            result.errors.append(f"invalid source text type: {kind}")
        if not speaker or not text:
            result.errors.append(f"incomplete Source Text Registry line: {line}")
        if source_id in registry:
            result.errors.append(f"duplicate source text ID: {source_id}")
        if text not in script_raw:
            result.errors.append(f"source text is not verbatim in script: {source_id}")
        registry[source_id] = (kind, text)
    return registry


def parse_catalog(
    result: Result,
    raw: str,
    scene_id: str,
    registry: dict[str, tuple[str, str]],
    characters: tuple[str, ...],
    crowds: tuple[str, ...],
    scene_asset: str,
    props: tuple[str, ...],
    segment_count: int,
) -> dict[str, CatalogEntry]:
    rows = table_rows(raw, "Segment Catalog")
    if len(rows) != segment_count:
        result.errors.append(f"segment-count is {segment_count} but catalog has {len(rows)} rows")
    catalog: dict[str, CatalogEntry] = {}
    assigned_sources: list[str] = []
    assigned_characters: set[str] = set()
    assigned_crowds: set[str] = set()
    assigned_props: set[str] = set()
    for expected, row in enumerate(rows, 1):
        if len(row) == 7:
            segment_id, duration_raw, _, _, chars_raw, scene_raw, source_raw = row
            crowds_raw, props_raw = "none", "none"
        elif len(row) == 9:
            segment_id, duration_raw, _, _, chars_raw, crowds_raw, scene_raw, props_raw, source_raw = row
        else:
            result.errors.append("Segment Catalog row must contain 7 legacy columns or 9 current columns")
            continue
        expected_id = f"{scene_id}-SEG{expected:03d}"
        if segment_id != expected_id:
            result.errors.append(f"segment IDs must be contiguous; expected {expected_id}")
        try:
            duration = parse_duration(duration_raw)
            row_characters = parse_id_list(chars_raw, "CHAR")
            row_crowds = parse_id_list(crowds_raw, "CROWD")
            row_props = parse_id_list(props_raw, "PROP")
            row_sources = parse_id_list(source_raw)
        except ValueError as error:
            result.errors.append(str(error))
            continue
        if not set(row_characters).issubset(set(characters)):
            result.errors.append(f"catalog uses undeclared character assets in {segment_id}")
        if not set(row_crowds).issubset(set(crowds)):
            result.errors.append(f"catalog uses undeclared crowd assets in {segment_id}")
        if not set(row_props).issubset(set(props)):
            result.errors.append(f"catalog uses undeclared prop assets in {segment_id}")
        if scene_raw != scene_asset:
            result.errors.append(f"catalog scene asset mismatch in {segment_id}")
        unknown_sources = sorted(set(row_sources) - set(registry))
        if unknown_sources:
            result.errors.append(f"catalog uses unknown source IDs in {segment_id}: {', '.join(unknown_sources)}")
        assigned_sources.extend(row_sources)
        assigned_characters.update(row_characters)
        assigned_crowds.update(row_crowds)
        assigned_props.update(row_props)
        catalog[segment_id] = CatalogEntry(
            segment_id,
            duration,
            row_characters,
            row_crowds,
            scene_raw,
            row_props,
            row_sources,
        )
    repeated_sources = sorted(
        source_id for source_id in set(assigned_sources) if assigned_sources.count(source_id) > 1
    )
    if repeated_sources:
        result.errors.append(f"source IDs assigned to multiple segments: {', '.join(repeated_sources)}")
    if set(assigned_sources) != set(registry):
        missing = sorted(set(registry) - set(assigned_sources))
        if missing:
            result.errors.append(f"registered source IDs are not assigned: {', '.join(missing)}")
    if assigned_characters != set(characters):
        result.errors.append("scene-level character-assets do not match the union of segment characters")
    if assigned_crowds != set(crowds):
        result.errors.append("scene-level crowd-assets do not match the union of segment crowds")
    if assigned_props != set(props):
        result.errors.append("scene-level prop-assets do not match the union of segment props")
    return catalog


def validate_plan(
    path: Path,
    style_id: str,
    assets: dict[str, Asset],
    script_path: Path,
    script_raw: str,
) -> tuple[Result, PlanContext | None]:
    result = Result(path, "SCENE-PLAN")
    raw = read(path)
    heading = re.match(
        rf"\A## (?P<id>(?P<scene>EP\d{{3}}-SC\d{{3}})-PLAN-(?P<version>{VERSION}))｜[^\r\n]+\r?\n",
        raw,
    )
    if not heading:
        result.errors.append("invalid scene-plan heading")
        return result, None
    plan_id, scene_id = heading.group("id"), heading.group("scene")
    if path.name != f"{plan_id}.md":
        result.errors.append("filename does not match scene-plan ID")
    values = metadata(raw)
    validate_common_metadata(result, values, style_id, scene_id, script_path)
    required_metadata(result, values, ("source-heading", "segment-count"))
    source_heading = values.get("source-heading", "")
    if not source_heading or source_heading not in script_raw:
        result.errors.append("source-heading is not present verbatim in selected script")
    bound = validate_asset_bindings(result, values, assets, raw)
    if bound is None:
        characters, crowds, scene_asset, props = (), (), "", ()
    else:
        characters, crowds, scene_asset, props = bound
    require_numbered_fields(
        result,
        raw,
        (
            "场戏叙事功能",
            "核心戏剧目标",
            "起始状态",
            "结束状态",
            "空间任务",
            "连续性入口",
            "连续性出口",
        ),
    )
    registry = parse_registry(result, raw, script_raw)
    try:
        segment_count = int(values.get("segment-count", ""))
        if segment_count < 1:
            raise ValueError
    except ValueError:
        result.errors.append("segment-count must be a positive integer")
        segment_count = 0
    catalog = parse_catalog(
        result,
        raw,
        scene_id,
        registry,
        characters,
        crowds,
        scene_asset,
        props,
        segment_count,
    )
    result.facts.extend([f"scene={scene_id}", f"segments={len(catalog)}", f"source_texts={len(registry)}"])
    context = PlanContext(path, plan_id, scene_id, values, registry, catalog)
    return result, context


def source_token(kind: str, source_id: str, text: str) -> str:
    return f'{kind} [{source_id}]: "{text}"'


def dramatic_execution_matches(prompt: str) -> list[re.Match[str]]:
    return list(re.finditer(r"^Dramatic execution: (?P<body>\S.*)$", prompt, re.M))


def validate_prompt_language(
    result: Result,
    prompt: str,
    registry: dict[str, tuple[str, str]],
) -> None:
    tokens = [source_token(kind, source_id, text) for source_id, (kind, text) in registry.items()]
    for line in prompt.splitlines():
        stripped = line
        for token in tokens:
            stripped = stripped.replace(token, "")
        if CJK_RE.search(stripped):
            result.errors.append("CJK is allowed only inside exact registered source-text calls")
            break


def validate_prompt_ontology(
    result: Result,
    atmosphere: str,
    style_traits: frozenset[str],
) -> None:
    prompt_traits = ontology_traits(atmosphere)
    required = style_traits & SPECIFIC_ONTOLOGY_TRAITS
    missing = sorted(required - prompt_traits)
    unsupported = sorted(prompt_traits - style_traits)
    if missing:
        result.errors.append(f"atmosphere does not inherit STYLE-BASE ontology: {', '.join(missing)}")
    if unsupported:
        result.errors.append(f"atmosphere adds unsupported visual ontology: {', '.join(unsupported)}")


def validate_source_lines(
    result: Result,
    prompt: str,
    declared_ids: tuple[str, ...],
    registry: dict[str, tuple[str, str]],
) -> None:
    header_re = re.compile(r"(?P<kind>Dialogue|Voice-over|On-screen text) \[(?P<id>D\d{3})\]:")
    headers = list(header_re.finditer(prompt))
    header_ids = [match.group("id") for match in headers]
    unknown_ids = sorted(set(header_ids) - set(registry))
    if unknown_ids:
        result.errors.append(f"unregistered source text used: {', '.join(unknown_ids)}")
    if set(header_ids) != set(declared_ids):
        result.errors.append("prompt source-text calls do not match source-text-ids metadata")
    repeated_ids = sorted(source_id for source_id in set(header_ids) if header_ids.count(source_id) > 1)
    if repeated_ids:
        result.errors.append(f"source text ID repeated in segment prompt: {', '.join(repeated_ids)}")

    executions = dramatic_execution_matches(prompt)
    for source_id in declared_ids:
        expected = registry.get(source_id)
        if expected is None:
            continue
        kind, text = expected
        token = source_token(kind, source_id, text)
        if prompt.count(token) != 1:
            result.errors.append(f"source text altered, type changed, or not used exactly once: {source_id}")
            continue
        position = prompt.find(token)
        execution = next(
            (
                match
                for match in executions
                if match.start("body") <= position and position + len(token) <= match.end("body")
            ),
            None,
        )
        if execution is None:
            result.errors.append(f"source text call must be inline inside Dramatic execution: {source_id}")
            continue
        body = execution.group("body")
        local_position = position - execution.start("body")
        before = body[:local_position]
        after = body[local_position + len(token) :]
        before_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", before)
        after_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", after)
        if len(before_words) < 3 or len(after_words) < 3:
            result.errors.append(
                f"source text call needs action/performance context before and reaction context after it: {source_id}"
            )

    if re.search(r"^(?:Dialogue|Voice-over|On-screen text) \[D\d{3}\]:", prompt, re.M):
        result.errors.append("source text calls must not appear as standalone lines")


def validate_shots(result: Result, prompt: str, duration: float) -> None:
    visual_marker = "[VISUAL CONTENT]"
    if visual_marker not in prompt:
        result.errors.append("missing [VISUAL CONTENT]")
        return
    visual = prompt.split(visual_marker, 1)[1]
    shot_re = re.compile(
        r"^Shot (?P<number>\d+) \[(?P<start>\d+(?:\.\d+)?)s-(?P<end>\d+(?:\.\d+)?)s\]$",
        re.M,
    )
    shots = list(shot_re.finditer(visual))
    if not 2 <= len(shots) <= 4:
        result.errors.append(f"segment must contain 2-4 shots, found {len(shots)}")
    previous_end = 0.0
    required = (
        "Shot scale:",
        "Composition:",
        "Camera angle:",
        "Camera movement:",
        "Dramatic execution:",
    )
    for position, match in enumerate(shots):
        number = int(match.group("number"))
        start = float(match.group("start"))
        end = float(match.group("end"))
        if number != position + 1:
            result.errors.append("shot numbers must be contiguous from 1")
        if abs(start - previous_end) > 1e-6:
            result.errors.append(f"shot {number} starts at {start:g}s, expected {previous_end:g}s")
        if end <= start:
            result.errors.append(f"shot {number} has a non-positive interval")
        block_end = shots[position + 1].start() if position + 1 < len(shots) else len(visual)
        block = visual[match.end() : block_end]
        for label in required:
            if not re.search(rf"^{re.escape(label)}\s*\S", block, re.M):
                result.errors.append(f"shot {number} missing {label}")
        if re.search(r"^(?:Subject and action|Performance):", block, re.M):
            result.errors.append(f"shot {number} uses split action/performance fields")
        execution_lines = re.findall(r"^Dramatic execution: (?P<body>\S.*)$", block, re.M)
        if len(execution_lines) != 1:
            result.errors.append(
                f"shot {number} must contain exactly one single-line Dramatic execution paragraph"
            )
        else:
            execution = execution_lines[0]
            if len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", execution)) < 20:
                result.errors.append(f"shot {number} Dramatic execution is too thin to fuse action and performance")
            if not re.search(
                r"\b(?:as|while|when|before|after|then|once|until|so that|which|triggering|causing)\b",
                execution,
                re.I,
            ):
                result.errors.append(
                    f"shot {number} Dramatic execution lacks temporal or causal linkage"
                )
        previous_end = end
    if shots and abs(previous_end - duration) > 1e-6:
        result.errors.append(f"last shot ends at {previous_end:g}s, segment duration is {duration:g}s")
    if not re.search(r"^Segment transition:\s*\S", visual, re.M):
        result.errors.append("missing Segment transition")
    if not re.search(r"^Continuity into next segment:\s*\S", visual, re.M):
        result.errors.append("missing Continuity into next segment")


def validate_prompt(
    result: Result,
    prompt: str,
    values: dict[str, str],
    characters: tuple[str, ...],
    crowds: tuple[str, ...],
    scene_asset: str,
    props: tuple[str, ...],
    assets: dict[str, Asset],
    duration: float,
    source_ids: tuple[str, ...],
    registry: dict[str, tuple[str, str]],
    style_raw: str,
    style_traits: frozenset[str],
) -> None:
    required_markers = (
        "[FOUNDATION]",
        "[ATMOSPHERE AND IMAGE QUALITY]",
        "[VISUAL CONTENT]",
    )
    positions = [prompt.find(marker) for marker in required_markers]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        result.errors.append("prompt sections are missing or out of order")
    if prompt.count("[FOUNDATION]") != 1 or prompt.count("[ATMOSPHERE AND IMAGE QUALITY]") != 1:
        result.errors.append("prompt section markers must appear exactly once")
    if f"Duration: {values.get('duration')}" not in prompt:
        result.errors.append("prompt duration does not match metadata")
    if "Frame: 16:9" not in prompt:
        result.errors.append("missing Frame: 16:9")
    refs = values.get("reference-calls", "")
    if f"References: {refs}" not in prompt:
        result.errors.append("prompt References line does not match metadata")
    for asset_id in characters:
        expected = f"Character {asset_id}: {assets[asset_id].base}"
        if expected not in prompt:
            result.errors.append(f"Character Base is missing or altered for {asset_id}")
    for asset_id in crowds:
        expected = f"Crowd {asset_id}: {assets[asset_id].base}"
        if expected not in prompt:
            result.errors.append(f"Crowd Base is missing or altered for {asset_id}")
    expected_scene = f"Scene {scene_asset}: {assets[scene_asset].base}"
    if expected_scene not in prompt:
        result.errors.append(f"Scene Base is missing or altered for {scene_asset}")
    for asset_id in props:
        expected = f"Prop {asset_id}: {assets[asset_id].base}"
        if expected not in prompt:
            result.errors.append(f"Prop Base is missing or altered for {asset_id}")
    prompt_character_ids = set(re.findall(r"^Character (CHAR-\d{3}):", prompt, re.M))
    if prompt_character_ids != set(characters):
        result.errors.append("prompt Character Base lines do not match character-assets")
    prompt_crowd_ids = set(re.findall(r"^Crowd (CROWD-\d{3}):", prompt, re.M))
    if prompt_crowd_ids != set(crowds):
        result.errors.append("prompt Crowd Base lines do not match crowd-assets")
    prompt_scene_ids = set(re.findall(r"^Scene (SCN-\d{3}):", prompt, re.M))
    if prompt_scene_ids != {scene_asset}:
        result.errors.append("prompt Scene Base line does not match scene-asset")
    prompt_prop_ids = set(re.findall(r"^Prop (PROP-\d{3}):", prompt, re.M))
    if prompt_prop_ids != set(props):
        result.errors.append("prompt Prop Base lines do not match prop-assets")
    for label in ("Style Core:", "Visual Baseline:", "Color and Tonality:"):
        if not re.search(rf"^{re.escape(label)}\s*\S", prompt, re.M):
            result.errors.append(f"missing atmosphere field: {label}")
    if DISALLOWED_OUTPUT_MODE_RE.search(prompt):
        result.errors.append("prompt uses a non-narrative game, concept-sheet, or advertising output mode")
    atmosphere = ""
    if "[ATMOSPHERE AND IMAGE QUALITY]" in prompt and "[VISUAL CONTENT]" in prompt:
        atmosphere = prompt.split("[ATMOSPHERE AND IMAGE QUALITY]", 1)[1].split("[VISUAL CONTENT]", 1)[0]
    validate_prompt_ontology(result, atmosphere, style_traits)
    style_lower = style_raw.lower()
    atmosphere_lower = atmosphere.lower()
    for term in HIGH_IMPACT_TERMS:
        if term in atmosphere_lower and term not in style_lower:
            result.errors.append(f"high-impact atmosphere term lacks STYLE-BASE support: {term}")
    validate_prompt_language(result, prompt, registry)
    validate_source_lines(result, prompt, source_ids, registry)
    validate_shots(result, prompt, duration)
    if len(re.findall(r"\S+", prompt)) < 100:
        result.errors.append("Seedance prompt is too short to carry the required controls")


def validate_segment(
    path: Path,
    style_id: str,
    style_raw: str,
    assets: dict[str, Asset],
    script_path: Path,
    plan: PlanContext,
    style_traits: frozenset[str],
) -> Result:
    result = Result(path, "SEGMENT")
    raw = read(path)
    heading = re.match(
        rf"\A## (?P<id>(?P<scene>EP\d{{3}}-SC\d{{3}})-SEG(?P<number>\d{{3}})-(?P<version>{VERSION}))｜[^\r\n]+\r?\n",
        raw,
    )
    if not heading:
        result.errors.append("invalid segment heading")
        return result
    artifact_id = heading.group("id")
    scene_id = heading.group("scene")
    segment_key = f"{scene_id}-SEG{heading.group('number')}"
    if path.name != f"{artifact_id}.md":
        result.errors.append("filename does not match segment ID")
    values = metadata(raw)
    validate_common_metadata(result, values, style_id, scene_id, script_path)
    required_metadata(result, values, ("inherits-plan", "duration", "source-text-ids"))
    if values.get("inherits-plan") != plan.plan_id:
        result.errors.append(f"inherits-plan must be {plan.plan_id}")
    for key in ("asset-index-snapshot", "source", "coverage", "status"):
        if values.get(key) != plan.metadata.get(key):
            result.errors.append(f"segment {key} does not match scene plan")
    bound = validate_asset_bindings(result, values, assets, raw)
    if bound is None:
        characters, crowds, scene_asset, props = (), (), "", ()
    else:
        characters, crowds, scene_asset, props = bound
    require_numbered_fields(
        result,
        raw,
        (
            "片段编号",
            "片段名称",
            "核心场景",
            "登场主要角色",
            "叙事功能",
            "戏剧目标",
            "情绪推进",
            "关键动作",
            "关键台词、旁白与屏幕文字",
            "转场方式",
            "与前后片段衔接",
            "参考调用",
        ),
    )
    try:
        duration = parse_duration(values.get("duration", ""))
        source_ids = parse_id_list(values.get("source-text-ids", ""))
    except ValueError as error:
        result.errors.append(str(error))
        duration = 0.0
        source_ids = ()
    catalog = plan.catalog.get(segment_key)
    if catalog is None:
        result.errors.append(f"segment is missing from scene plan catalog: {segment_key}")
    else:
        if abs(duration - catalog.duration) > 1e-6:
            result.errors.append("segment duration does not match scene plan catalog")
        if characters != catalog.characters:
            result.errors.append("segment character-assets do not match scene plan catalog")
        if crowds != catalog.crowds:
            result.errors.append("segment crowd-assets do not match scene plan catalog")
        if scene_asset != catalog.scene:
            result.errors.append("segment scene-asset does not match scene plan catalog")
        if props != catalog.props:
            result.errors.append("segment prop-assets do not match scene plan catalog")
        if source_ids != catalog.source_ids:
            result.errors.append("segment source-text-ids do not match scene plan catalog")
    prompt = fenced_section(raw, "Seedance 2.0 Prompt")
    if prompt is None:
        result.errors.append("missing Seedance 2.0 Prompt")
    elif (
        duration > 0
        and scene_asset in assets
        and all(item in assets for item in (*characters, *crowds, *props))
    ):
        validate_prompt(
            result,
            prompt,
            values,
            characters,
            crowds,
            scene_asset,
            props,
            assets,
            duration,
            source_ids,
            plan.registry,
            style_raw,
            style_traits,
        )
    result.facts.extend(
        [
            f"segment={segment_key}",
            f"duration={duration:g}s",
            f"characters={len(characters)}",
            f"crowds={len(crowds)}",
            f"props={len(props)}",
        ]
    )
    return result


def collect_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*-PLAN-*.md")))
            paths.extend(sorted(path.rglob("*-SEG*.md")))
        else:
            paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="scene-plan/segment files or a STORYBOARD directory")
    parser.add_argument("--script", type=Path, required=True, help="source script file")
    parser.add_argument("--style-base", type=Path, required=True, help="exact confirmed STYLE-BASE file")
    parser.add_argument("--asset-index", type=Path, required=True, help="exact approved ASSET-INDEX file")
    parser.add_argument("--plan", type=Path, help="scene plan required when validating segment-only inputs")
    args = parser.parse_args()

    try:
        style_id, style_raw, style_traits = validate_style(args.style_base)
        if not args.script.is_file():
            raise ValueError(f"missing script: {args.script}")
        script_raw = read(args.script)
        _, assets = load_approved_index(args.asset_index, style_id)
    except ValueError as error:
        print(f"ERROR {error}")
        return 2

    paths = collect_paths(args.paths)
    if not paths:
        print("ERROR no storyboard artifacts found")
        return 2

    plan_path = args.plan
    plan_candidates = [path for path in paths if "-PLAN-" in path.name]
    if plan_path is None and len(plan_candidates) == 1:
        plan_path = plan_candidates[0]
    segment_paths = [path for path in paths if "-SEG" in path.name]
    if segment_paths and plan_path is None:
        print("ERROR segment validation requires --plan or exactly one scene plan in inputs")
        return 2

    plan_result: Result | None = None
    plan_context: PlanContext | None = None
    if plan_path is not None:
        if not plan_path.is_file():
            print(f"ERROR missing scene plan: {plan_path}")
            return 2
        plan_result, plan_context = validate_plan(
            plan_path,
            style_id,
            assets,
            args.script,
            script_raw,
        )

    results: list[Result] = []
    if plan_result is not None and plan_path not in paths:
        results.append(plan_result)
    for path in paths:
        if not path.is_file():
            result = Result(path, "MISSING")
            result.errors.append("artifact file does not exist")
            results.append(result)
        elif "-PLAN-" in path.name:
            if plan_path == path and plan_result is not None:
                results.append(plan_result)
            else:
                result, _ = validate_plan(path, style_id, assets, args.script, script_raw)
                results.append(result)
        elif "-SEG" in path.name:
            if plan_context is None:
                result = Result(path, "SEGMENT")
                result.errors.append("valid scene plan is required")
                results.append(result)
            else:
                results.append(
                    validate_segment(
                        path,
                        style_id,
                        style_raw,
                        assets,
                        args.script,
                        plan_context,
                        style_traits,
                    )
                )
        else:
            result = Result(path, "UNKNOWN")
            result.errors.append("unrecognized storyboard artifact filename")
            results.append(result)

    failed = False
    for result in results:
        status = "FAIL" if result.errors else "PASS"
        facts = "; ".join(result.facts)
        print(f"{status} {result.kind} {result.path}{'; ' + facts if facts else ''}")
        for error in result.errors:
            print(f"  ERROR {error}")
        failed = failed or bool(result.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
