#!/usr/bin/env python3
"""Deterministic surface validation for STYLE-BASE artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


VERSION = r"(?:v\d+\.\d+|draft-v0\.\d+)"
CJK_RE = re.compile(r"[\u3400-\u9fff]")


@dataclass
class Result:
    path: Path
    errors: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text.strip()))


def validate_style(path: Path) -> Result:
    result = Result(path)
    raw = path.read_text(encoding="utf-8")
    pattern = (
        rf"\A## (?P<id>STYLE-BASE-{VERSION})\r?\n\r?\n"
        rf"~~~text\r?\n(?P<body>.+?)\r?\n~~~\s*\Z"
    )
    match = re.match(pattern, raw, re.S)
    if not match:
        result.errors.append("invalid STYLE-BASE file structure")
        return result

    artifact_id = match.group("id")
    body = match.group("body")
    if path.name != f"{artifact_id}.md":
        result.errors.append("filename does not match artifact ID")
    if CJK_RE.search(body):
        result.errors.append("prompt body contains CJK characters")
    if "16:9" not in body:
        result.errors.append("STYLE-BASE body must contain 16:9")
    result.facts.append(f"words={word_count(body)}")
    return result


def collect_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            paths.extend(sorted(path.glob("STYLE-BASE-*.md")))
        else:
            paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="STYLE-BASE file(s) or a DNA directory")
    args = parser.parse_args()

    paths = collect_paths(args.paths)
    if not paths:
        print("ERROR no STYLE-BASE artifacts found")
        return 2

    failed = False
    for path in paths:
        if not path.is_file():
            print(f"ERROR missing artifact: {path}")
            failed = True
            continue
        if not path.name.startswith("STYLE-BASE-"):
            print(f"FAIL STYLE-BASE {path}")
            print("  ERROR unrecognized artifact filename")
            failed = True
            continue
        result = validate_style(path)
        status = "FAIL" if result.errors else "PASS"
        details = "; ".join(result.facts)
        print(f"{status} STYLE-BASE {path}{'; ' + details if details else ''}")
        for error in result.errors:
            print(f"  ERROR {error}")
        failed = failed or bool(result.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
