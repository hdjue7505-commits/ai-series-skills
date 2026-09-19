#!/usr/bin/env python3
"""Validate live-action AI Series Art Director Markdown artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


VERSION = r"(?:v\d+\.\d+|draft-v0\.\d+)"
STYLE_ID_RE = re.compile(rf"STYLE-BASE-{VERSION}")
INDEX_ID_RE = re.compile(rf"ASSET-INDEX-{VERSION}")
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
STYLE_META_RE = re.compile(
    r"\b(?:live[- ]action|real actors?|animation|animated|anime|donghua|cartoon|2d|3d|"
    r"hand[- ]drawn|motion[- ]comic|manhua|manga[- ]drama|stop[- ]motion|cgi?|render(?:ing)?|"
    r"concept art|illustration|commercial advertising|plastic skin)\b",
    re.I,
)


@dataclass
class Result:
    path: Path
    kind: str
    errors: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text.strip()))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def metadata(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines()[1:]:
        if line.startswith("### "):
            break
        match = re.fullmatch(r"- ([a-z-]+): (.+)", line)
        if match:
            result[match.group(1)] = match.group(2).strip()
    return result


def required_metadata(result: Result, values: dict[str, str], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in values:
            result.errors.append(f"missing metadata: {key}")


def fenced_section(raw: str, heading: str) -> str | None:
    pattern = rf"^### {re.escape(heading)}\r?\n~~~text\r?\n(.+?)\r?\n~~~(?:\r?\n|\Z)"
    match = re.search(pattern, raw, re.M | re.S)
    return match.group(1).strip() if match else None


def require_english(result: Result, label: str, body: str) -> None:
    if CJK_RE.search(body):
        result.errors.append(f"{label} contains CJK characters")


def require_cues(result: Result, label: str, body: str, cues: tuple[str, ...]) -> None:
    lowered = body.lower()
    for cue in cues:
        if cue not in lowered:
            result.errors.append(f"{label} missing cue: {cue}")


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


def require_style_ontology(
    result: Result,
    label: str,
    body: str,
    style_traits: frozenset[str],
) -> None:
    if not style_traits:
        return
    prompt_traits = ontology_traits(body)
    required = style_traits & SPECIFIC_ONTOLOGY_TRAITS
    missing = sorted(required - prompt_traits)
    unsupported = sorted(prompt_traits - style_traits)
    if missing:
        result.errors.append(f"{label} does not inherit STYLE-BASE ontology: {', '.join(missing)}")
    if unsupported:
        result.errors.append(f"{label} adds unsupported visual ontology: {', '.join(unsupported)}")


def validate_style_file(path: Path | None) -> tuple[str | None, frozenset[str]]:
    if path is None:
        return None, frozenset()
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
    if traits != frozenset({"live-action"}):
        raise ValueError(
            "AI Series Art Director requires a live-action-only STYLE-BASE; "
            "animation, motion-comic and mixed-animation styles are not supported. "
            "Use cinematic VFX for film effects, not an animation or 3D medium label: "
            f"{path} (detected: {', '.join(sorted(traits))})"
        )
    return match.group("id"), traits


def validate_index_file(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.is_file():
        raise ValueError(f"missing ASSET-INDEX: {path}")
    raw = read(path)
    match = re.search(rf"^## (?P<id>ASSET-INDEX-{VERSION})$", raw, re.M)
    if not match or path.name != f"{match.group('id')}.md":
        raise ValueError(f"invalid ASSET-INDEX: {path}")
    values = metadata(raw)
    if values.get("status") not in {"confirmed-for-modeling", "approved"}:
        raise ValueError(f"ASSET-INDEX is neither legacy confirmed-for-modeling nor approved: {path}")
    return match.group("id")


def table_rows(raw: str, heading: str) -> list[list[str]]:
    match = re.search(
        rf"^### {re.escape(heading)}\r?\n(?P<table>(?:\|.*\r?\n?)+?)(?=\r?\n### |\Z)",
        raw,
        re.M,
    )
    if not match:
        return []
    rows: list[list[str]] = []
    for line in match.group("table").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] == "Asset ID" or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def validate_index(path: Path, raw: str, selected_style: str | None) -> Result:
    result = Result(path, "ASSET-INDEX")
    match = re.match(rf"\A## (?P<id>ASSET-INDEX-{VERSION})\r?\n", raw)
    if not match:
        result.errors.append("invalid ASSET-INDEX heading")
        return result
    artifact_id = match.group("id")
    if path.name != f"{artifact_id}.md":
        result.errors.append("filename does not match ASSET-INDEX ID")
    # Existing downstream readers require the final table to reach EOF.
    if re.search(r"\r?\n[ \t]*\r?\n[ \t\r\n]*\Z", raw):
        result.errors.append("ASSET-INDEX must end after the final table with no trailing blank lines")

    values = metadata(raw)
    required_metadata(result, values, ("inherits-style", "source", "coverage", "status"))
    if values.get("coverage") not in {"complete", "draft"}:
        result.errors.append("coverage must be complete or draft")
    status = values.get("status")
    if status not in {
        "awaiting-confirmation",
        "confirmed-for-modeling",
        "awaiting-asset-approval",
        "approved",
    }:
        result.errors.append("invalid index status")
    style = values.get("inherits-style", "")
    if not STYLE_ID_RE.fullmatch(style):
        result.errors.append("invalid inherits-style")
    elif selected_style and style != selected_style:
        result.errors.append(f"inherits {style} but selected STYLE-BASE is {selected_style}")

    all_ids: set[str] = set()
    all_labels: set[str] = set()
    counts: list[int] = []
    for heading, prefix, folder in (
        ("主要角色", "CHAR", "characters"),
        ("群众演员", "CROWD", "crowds"),
        ("核心场景", "SCN", "scenes"),
        ("重要道具", "PROP", "props"),
    ):
        rows = table_rows(raw, heading)
        counts.append(len(rows))
        for row in rows:
            if len(row) != 6:
                result.errors.append(f"{heading} row must contain 6 columns")
                continue
            asset_id, _, _, _, current_file, reference_label = row
            if not re.fullmatch(rf"{prefix}-\d{{3}}", asset_id):
                result.errors.append(f"invalid asset ID: {asset_id}")
            if asset_id in all_ids:
                result.errors.append(f"duplicate asset ID: {asset_id}")
            all_ids.add(asset_id)
            if status in {"awaiting-asset-approval", "approved"}:
                file_match = re.fullmatch(rf"{folder}/{asset_id}-(?P<version>{VERSION})\.md", current_file)
                if not file_match:
                    result.errors.append(f"invalid current file for {asset_id}")
                else:
                    expected_label = f"@{asset_id}-REF-{file_match.group('version')}"
                    if reference_label != expected_label:
                        result.errors.append(f"reference label mismatch for {asset_id}")
                if reference_label in all_labels:
                    result.errors.append(f"duplicate reference label: {reference_label}")
                all_labels.add(reference_label)
            elif current_file != "pending" or reference_label != "pending":
                result.errors.append(f"unconfirmed asset {asset_id} must remain pending")
    if not all_ids:
        result.errors.append("ASSET-INDEX must contain at least one asset")
    result.facts.extend(
        [
            f"characters={counts[0]}",
            f"crowds={counts[1]}",
            f"scenes={counts[2]}",
            f"props={counts[3]}",
            f"status={status}",
        ]
    )
    return result


def validate_entity_metadata(
    result: Result,
    values: dict[str, str],
    asset_id: str,
    version: str,
    selected_style: str | None,
    selected_index: str | None,
) -> None:
    required_metadata(
        result,
        values,
        ("inherits-style", "inherits-index", "source", "coverage", "reference-label", "reference-image"),
    )
    style = values.get("inherits-style", "")
    index = values.get("inherits-index", "")
    if not STYLE_ID_RE.fullmatch(style):
        result.errors.append("invalid inherits-style")
    elif selected_style and style != selected_style:
        result.errors.append(f"inherits {style} but selected STYLE-BASE is {selected_style}")
    if not INDEX_ID_RE.fullmatch(index):
        result.errors.append("invalid inherits-index")
    elif selected_index and index != selected_index:
        result.errors.append(f"inherits {index} but selected ASSET-INDEX is {selected_index}")
    if values.get("coverage") not in {"complete", "draft"}:
        result.errors.append("coverage must be complete or draft")
    expected_label = f"@{asset_id}-REF-{version}"
    if values.get("reference-label") != expected_label:
        result.errors.append(f"reference-label must be {expected_label}")
    image = values.get("reference-image", "")
    if image != "pending":
        expected_image = f"ART/references/{expected_label[1:]}.png"
        if image != expected_image:
            result.errors.append(f"reference-image must be pending or {expected_image}")


def require_plan_fields(result: Result, raw: str, labels: tuple[str, ...]) -> None:
    for number, label in enumerate(labels, 1):
        if not re.search(rf"^{number}\. {re.escape(label)}：\S", raw, re.M):
            result.errors.append(f"missing modeling field {number}: {label}")


def validate_character(
    path: Path,
    raw: str,
    selected_style: str | None,
    selected_index: str | None,
    style_traits: frozenset[str],
) -> Result:
    result = Result(path, "CHARACTER")
    match = re.match(rf"\A## (?P<asset>CHAR-\d{{3}})-(?P<version>{VERSION})｜(?P<name>[^\r\n]+)\r?\n", raw)
    if not match:
        result.errors.append("invalid character heading")
        return result
    asset_id, version = match.group("asset"), match.group("version")
    if path.name != f"{asset_id}-{version}.md":
        result.errors.append("filename does not match character ID")
    values = metadata(raw)
    validate_entity_metadata(result, values, asset_id, version, selected_style, selected_index)
    require_plan_fields(
        result,
        raw,
        (
            "角色定位",
            "叙事作用",
            "核心识别点",
            "年龄与外貌",
            "发型",
            "服装",
            "配色",
            "配饰、武器与道具",
            "气质关键词",
            "连续性锚点",
        ),
    )
    model = fenced_section(raw, "Character Model-Sheet Prompt")
    base = fenced_section(raw, "Character Base")
    if model is None:
        result.errors.append("missing Character Model-Sheet Prompt")
    else:
        require_english(result, "Character Model-Sheet Prompt", model)
        require_cues(
            result,
            "Character Model-Sheet Prompt",
            model,
            (
                "16:9",
                "pure white background",
                "upper-left",
                "lower-left",
                "right side",
                "front view",
                "profile view",
                "back view",
                "continuity anchors",
            ),
        )
        require_style_ontology(result, "Character Model-Sheet Prompt", model, style_traits)
        if word_count(model) < 80:
            result.errors.append("Character Model-Sheet Prompt is too short")
    if base is None:
        result.errors.append("missing Character Base")
    else:
        require_english(result, "Character Base", base)
        count = word_count(base)
        if not 35 <= count <= 100:
            result.errors.append(f"Character Base word count {count} is outside 35-100")
        if re.search(r"\b(?:background|scene|location|camera|lens|shot|16:9|cinematic|film grain|depth of field)\b", base, re.I):
            result.errors.append("Character Base contains spatial, camera, aspect-ratio, or global-style terms")
        if "STYLE-BASE" in base or STYLE_META_RE.search(base):
            result.errors.append("Character Base contains style or visual-ontology meta-text")
    result.facts.append(f"asset={asset_id}")
    return result


def validate_scene(
    path: Path,
    raw: str,
    selected_style: str | None,
    selected_index: str | None,
    style_traits: frozenset[str],
) -> Result:
    result = Result(path, "SCENE")
    match = re.match(rf"\A## (?P<asset>SCN-\d{{3}})-(?P<version>{VERSION})｜(?P<name>[^\r\n]+)\r?\n", raw)
    if not match:
        result.errors.append("invalid scene heading")
        return result
    asset_id, version = match.group("asset"), match.group("version")
    if path.name != f"{asset_id}-{version}.md":
        result.errors.append("filename does not match scene ID")
    values = metadata(raw)
    validate_entity_metadata(result, values, asset_id, version, selected_style, selected_index)
    require_plan_fields(
        result,
        raw,
        (
            "场景名称",
            "场景作用",
            "空间类型",
            "时代与世界观属性",
            "全景布局结构",
            "主视觉焦点",
            "关键道具",
            "色彩氛围",
            "光线逻辑",
            "可调度区域",
            "角色可站位区域",
            "连续性锚点",
        ),
    )
    model = fenced_section(raw, "Scene Model-Sheet Prompt")
    base = fenced_section(raw, "Scene Base")
    if model is None:
        result.errors.append("missing Scene Model-Sheet Prompt")
    else:
        require_english(result, "Scene Model-Sheet Prompt", model)
        require_cues(
            result,
            "Scene Model-Sheet Prompt",
            model,
            (
                "16:9",
                "2x2 four-panel grid",
                "same scene",
                "upper-left: full-scene overview",
                "upper-right: top-down view",
                "lower-left: side view",
                "lower-right: feature-focused panel",
                "defining scene features",
                "foreground",
                "midground",
                "background",
                "entrance",
                "exit",
                "key props",
                "light source",
                "blocking zones",
                "standing positions",
            ),
        )
        require_style_ontology(result, "Scene Model-Sheet Prompt", model, style_traits)
        if word_count(model) < 80:
            result.errors.append("Scene Model-Sheet Prompt is too short")
    if base is None:
        result.errors.append("missing Scene Base")
    else:
        require_english(result, "Scene Base", base)
        count = word_count(base)
        if not 40 <= count <= 120:
            result.errors.append(f"Scene Base word count {count} is outside 40-120")
        if re.search(
            r"\b(?:character|actor|protagonist|hero|dialogue|plot|story|camera|lens|shot|16:9|cinematic|film grain|depth of field)\b",
            base,
            re.I,
        ):
            result.errors.append("Scene Base contains character, story, camera, aspect-ratio, or global-style terms")
        if "STYLE-BASE" in base or STYLE_META_RE.search(base):
            result.errors.append("Scene Base contains style or visual-ontology meta-text")
    result.facts.append(f"asset={asset_id}")
    return result


def validate_crowd(
    path: Path,
    raw: str,
    selected_style: str | None,
    selected_index: str | None,
    style_traits: frozenset[str],
) -> Result:
    result = Result(path, "CROWD")
    match = re.match(rf"\A## (?P<asset>CROWD-\d{{3}})-(?P<version>{VERSION})｜(?P<name>[^\r\n]+)\r?\n", raw)
    if not match:
        result.errors.append("invalid crowd heading")
        return result
    asset_id, version = match.group("asset"), match.group("version")
    if path.name != f"{asset_id}-{version}.md":
        result.errors.append("filename does not match crowd ID")
    values = metadata(raw)
    validate_entity_metadata(result, values, asset_id, version, selected_style, selected_index)
    require_plan_fields(
        result,
        raw,
        (
            "群体定位",
            "叙事与空间作用",
            "组织与层级构成",
            "人口构成与差异范围",
            "体态与面貌分布",
            "发型与妆容系统",
            "服装与制服层级",
            "配色、配饰与携带物",
            "职业姿态与动作语汇",
            "连续性锚点与允许变化",
        ),
    )
    model = fenced_section(raw, "Crowd Model-Sheet Prompt")
    base = fenced_section(raw, "Crowd Base")
    if model is None:
        result.errors.append("missing Crowd Model-Sheet Prompt")
    else:
        require_english(result, "Crowd Model-Sheet Prompt", model)
        require_cues(
            result,
            "Crowd Model-Sheet Prompt",
            model,
            (
                "16:9",
                "pure white background",
                "group lineup",
                "rank variations",
                "front view",
                "profile view",
                "back view",
                "continuity anchors",
                "no duplicated faces",
            ),
        )
        require_style_ontology(result, "Crowd Model-Sheet Prompt", model, style_traits)
        if word_count(model) < 80:
            result.errors.append("Crowd Model-Sheet Prompt is too short")
    if base is None:
        result.errors.append("missing Crowd Base")
    else:
        require_english(result, "Crowd Base", base)
        count = word_count(base)
        if not 45 <= count <= 120:
            result.errors.append(f"Crowd Base word count {count} is outside 45-120")
        if re.search(
            r"\b(?:background|scene|location|camera|lens|shot|16:9|cinematic|film grain|depth of field|formation)\b",
            base,
            re.I,
        ):
            result.errors.append("Crowd Base contains spatial, fixed-formation, camera, aspect-ratio, or global-style terms")
        if "STYLE-BASE" in base or STYLE_META_RE.search(base):
            result.errors.append("Crowd Base contains style or visual-ontology meta-text")
    result.facts.append(f"asset={asset_id}")
    return result


def validate_prop(
    path: Path,
    raw: str,
    selected_style: str | None,
    selected_index: str | None,
    style_traits: frozenset[str],
) -> Result:
    result = Result(path, "PROP")
    match = re.match(rf"\A## (?P<asset>PROP-\d{{3}})-(?P<version>{VERSION})｜(?P<name>[^\r\n]+)\r?\n", raw)
    if not match:
        result.errors.append("invalid prop heading")
        return result
    asset_id, version = match.group("asset"), match.group("version")
    if path.name != f"{asset_id}-{version}.md":
        result.errors.append("filename does not match prop ID")
    values = metadata(raw)
    validate_entity_metadata(result, values, asset_id, version, selected_style, selected_index)
    require_plan_fields(
        result,
        raw,
        (
            "道具名称",
            "道具类别",
            "叙事功能",
            "归属与流转",
            "尺寸与人体尺度",
            "轮廓与核心识别点",
            "结构与构造",
            "材料与制造工艺",
            "配色与表面状态",
            "使用、握持与佩戴逻辑",
            "状态谱系与变化触发",
            "连续性锚点",
        ),
    )
    model = fenced_section(raw, "Prop Model-Sheet Prompt")
    base = fenced_section(raw, "Prop Base")
    if model is None:
        result.errors.append("missing Prop Model-Sheet Prompt")
    else:
        require_english(result, "Prop Model-Sheet Prompt", model)
        require_cues(
            result,
            "Prop Model-Sheet Prompt",
            model,
            (
                "16:9",
                "neutral background",
                "three-quarter view",
                "front view",
                "profile view",
                "back view",
                "top view",
                "scale reference",
                "material details",
                "continuity anchors",
            ),
        )
        require_style_ontology(result, "Prop Model-Sheet Prompt", model, style_traits)
        if word_count(model) < 80:
            result.errors.append("Prop Model-Sheet Prompt is too short")
    if base is None:
        result.errors.append("missing Prop Base")
    else:
        require_english(result, "Prop Base", base)
        count = word_count(base)
        if not 40 <= count <= 120:
            result.errors.append(f"Prop Base word count {count} is outside 40-120")
        if re.search(
            r"\b(?:background|scene|location|character|actor|protagonist|hero|dialogue|plot|story|camera|lens|shot|16:9|cinematic|film grain|depth of field)\b",
            base,
            re.I,
        ):
            result.errors.append("Prop Base contains holder, story, spatial, camera, aspect-ratio, or global-style terms")
        if "STYLE-BASE" in base or STYLE_META_RE.search(base):
            result.errors.append("Prop Base contains style or visual-ontology meta-text")
    result.facts.append(f"asset={asset_id}")
    return result


def validate(
    path: Path,
    selected_style: str | None,
    selected_index: str | None,
    style_traits: frozenset[str],
) -> Result:
    raw = read(path)
    name = path.name
    if name.startswith("ASSET-INDEX-"):
        return validate_index(path, raw, selected_style)
    if name.startswith("CHAR-"):
        return validate_character(path, raw, selected_style, selected_index, style_traits)
    if name.startswith("CROWD-"):
        return validate_crowd(path, raw, selected_style, selected_index, style_traits)
    if name.startswith("SCN-"):
        return validate_scene(path, raw, selected_style, selected_index, style_traits)
    if name.startswith("PROP-"):
        return validate_prop(path, raw, selected_style, selected_index, style_traits)
    result = Result(path, "UNKNOWN")
    result.errors.append("unrecognized artifact filename")
    return result


def collect_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            paths.extend(sorted(path.glob("ASSET-INDEX-*.md")))
            paths.extend(sorted(path.glob("characters/CHAR-*.md")))
            paths.extend(sorted(path.glob("crowds/CROWD-*.md")))
            paths.extend(sorted(path.glob("scenes/SCN-*.md")))
            paths.extend(sorted(path.glob("props/PROP-*.md")))
        else:
            paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="artifact file(s) or an ART directory")
    parser.add_argument("--style-base", type=Path, help="exact confirmed STYLE-BASE file")
    parser.add_argument("--index", type=Path, help="exact confirmed ASSET-INDEX file")
    args = parser.parse_args()

    try:
        selected_style, style_traits = validate_style_file(args.style_base)
        selected_index = validate_index_file(args.index)
    except ValueError as error:
        print(f"ERROR {error}")
        return 2

    paths = collect_paths(args.paths)
    if not paths:
        print("ERROR no art artifacts found")
        return 2

    failed = False
    for path in paths:
        if not path.is_file():
            print(f"ERROR missing artifact: {path}")
            failed = True
            continue
        result = validate(path, selected_style, selected_index, style_traits)
        status = "FAIL" if result.errors else "PASS"
        facts = "; ".join(result.facts)
        print(f"{status} {result.kind} {path}{'; ' + facts if facts else ''}")
        for error in result.errors:
            print(f"  ERROR {error}")
        failed = failed or bool(result.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
