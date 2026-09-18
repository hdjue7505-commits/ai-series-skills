#!/usr/bin/env python3
"""Install the four oh-my-director skills locally without replacing existing files."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

SKILLS = (
    "manga-screenwriter",
    "ai-series-visual-dna",
    "ai-series-art-director",
    "ai-series-storyboard-master",
)


def install(root: Path, destination: Path, dry_run: bool = False) -> list[Path]:
    """Preflight the entire bundle, then copy it; roll back newly reserved folders on failure."""
    root = root.resolve()
    destination = destination.expanduser().resolve()
    sources = [root / name for name in SKILLS]
    targets = [destination / name for name in SKILLS]
    for source in sources:
        for required in ("SKILL.md", "agents/openai.yaml"):
            if not (source / required).is_file():
                raise FileNotFoundError(f"Incomplete repository: {source / required}")
        if destination == source or source in destination.parents:
            raise ValueError("The destination must not be inside a source skill.")
    conflicts = [p for p in targets if p.exists() or p.is_symlink()]
    if conflicts:
        raise FileExistsError(
            "Nothing installed; existing skills will not be overwritten:\n"
            + "\n".join(str(p) for p in conflicts)
            + "\nBack them up or choose a different --dest."
        )
    if dry_run:
        return targets
    destination.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        # Reserve every target first. Never adopt or remove an existing directory.
        for target in targets:
            target.mkdir()
            created.append(target)
        for source, target in zip(sources, targets):
            shutil.copytree(
                source, target, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
    except Exception:
        for target in reversed(created):
            shutil.rmtree(target)
        raise
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest", type=Path, default=Path.home() / ".agents" / "skills",
        help="Skill directory (default: ~/.agents/skills). Existing skills are never replaced.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Check and print paths without writing.")
    args = parser.parse_args()
    try:
        targets = install(Path(__file__).resolve().parents[1], args.dest, args.dry_run)
    except (OSError, ValueError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    prefix = "Would install" if args.dry_run else "Installed"
    for target in targets:
        print(f"{prefix}: {target}")
    if not args.dry_run:
        print("Open Codex and invoke $manga-screenwriter. Restart Codex if the skills do not appear.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
