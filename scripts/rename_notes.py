from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.obsidian import extract_title, note_filename, unique_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    changed: list[tuple[str, str]] = []
    for path in sorted(args.directory.glob("*.md")):
        title = extract_title(path.read_text(encoding="utf-8")) or path.stem
        target = path.with_name(f"{note_filename(title)}.md")
        if path.name == target.name:
            continue
        if target.exists():
            target = unique_path(target)
        old_name = path.name
        path.rename(target)
        changed.append((old_name, target.name))

    if not changed:
        print("no changes")
        return
    for old_name, new_name in changed:
        print(f"{old_name} -> {new_name}")


if __name__ == "__main__":
    main()
