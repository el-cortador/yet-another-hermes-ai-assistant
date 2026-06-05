from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
FRONTMATTER_TITLE_RE = re.compile(r"^title:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)(?:\n---\s*)(?P<rest>\n.*|\Z)", re.DOTALL)
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{3,}")


@dataclass(frozen=True)
class Note:
    path: Path
    title: str
    text: str


class ObsidianVault:
    def __init__(self, root: Path, inbox_dir: str) -> None:
        self.root = root
        self.inbox = root / inbox_dir

    def write_note(self, markdown: str) -> Path:
        self.inbox.mkdir(parents=True, exist_ok=True)
        markdown = strip_markdown_fence(markdown)
        markdown = normalize_obsidian_markdown(markdown)
        title = extract_title(markdown) or "Новая заметка"
        filename = f"{note_filename(title)}.md"
        path = unique_path(self.inbox / filename)
        path.write_text(markdown.strip() + "\n", encoding="utf-8")
        return path

    def search(self, query: str, limit: int = 8) -> list[Note]:
        query_words = set(words(query))
        if not query_words:
            return []

        scored: list[tuple[int, Note]] = []
        for path in self.root.rglob("*.md"):
            if any(part.startswith(".") for part in path.relative_to(self.root).parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            note_words = set(words(text))
            score = len(query_words & note_words)
            if score:
                scored.append((score, Note(path=path, title=extract_title(text) or path.stem, text=text)))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [note for _, note in scored[:limit]]

    def build_context(self, notes: list[Note], max_chars: int = 24000) -> str:
        chunks: list[str] = []
        used = 0
        for note in notes:
            rel_path = note.path.relative_to(self.root).as_posix()
            chunk = f"---\nЗаметка: {note.title}\nПуть: {rel_path}\n\n{note.text[:4000]}"
            if used + len(chunk) > max_chars:
                break
            chunks.append(chunk)
            used += len(chunk)
        return "\n\n".join(chunks)


def extract_title(markdown: str) -> str | None:
    fm_match = FRONTMATTER_TITLE_RE.search(markdown)
    if fm_match:
        return fm_match.group(1).strip()
    title_match = TITLE_RE.search(markdown)
    if title_match:
        return title_match.group(1).strip()
    return None


def strip_markdown_fence(markdown: str) -> str:
    markdown = markdown.strip()
    match = re.match(r"^```(?:markdown|md)?\s*\n(?P<body>.*)\n```$", markdown, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group("body").strip()
    return markdown


def normalize_obsidian_markdown(markdown: str) -> str:
    markdown = strip_invisible_prefix(markdown)
    metadata, body = split_frontmatter(markdown)
    title = metadata.get("title") or extract_title(body) or "Новая заметка"
    source = metadata.get("source", "")
    created = metadata.get("created") or datetime.now().strftime("%Y-%m-%d")
    tags = normalize_tags(metadata.get("tags", []))

    frontmatter = [
        "---",
        f'title: "{escape_yaml_scalar(title)}"',
    ]
    if source:
        frontmatter.append(f'source: "{escape_yaml_scalar(source)}"')
    frontmatter.append(f'created: "{escape_yaml_scalar(created)}"')
    frontmatter.append("tags:")
    if tags:
        frontmatter.extend(f"  - {tag}" for tag in tags)
    else:
        frontmatter.append("  - inbox")
    frontmatter.append("---")
    return "\n".join(frontmatter) + "\n\n" + body.strip() + "\n"


def split_frontmatter(markdown: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    return parse_simple_frontmatter(match.group("body")), match.group("rest").strip()


def parse_simple_frontmatter(body: str) -> dict[str, object]:
    result: dict[str, object] = {}
    lines = body.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if key == "tags" and raw_value == "":
            tags: list[str] = []
            index += 1
            while index < len(lines) and lines[index].startswith((" ", "\t")):
                item = lines[index].strip()
                if item.startswith("- "):
                    tags.append(unquote_yaml_scalar(item[2:].strip()))
                index += 1
            result[key] = tags
            continue
        if key == "tags":
            result[key] = parse_inline_tags(raw_value)
        else:
            result[key] = unquote_yaml_scalar(raw_value)
        index += 1
    return result


def parse_inline_tags(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [unquote_yaml_scalar(item.strip()) for item in value.split(",") if item.strip()]


def normalize_tags(value: object) -> list[str]:
    raw_tags = value if isinstance(value, list) else parse_inline_tags(str(value)) if value else []
    tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in raw_tags:
        tag = slugify(str(raw_tag).lstrip("#"))
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def strip_invisible_prefix(value: str) -> str:
    return value.lstrip("\ufeff\u200b\u200c\u200d\r\n\t ")


def unquote_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\\\", "\\").strip()


def escape_yaml_scalar(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    value = re.sub(r"[-\s]+", "-", value, flags=re.UNICODE)
    return value[:80] or "note"


def note_filename(value: str, max_length: int = 160) -> str:
    value = strip_invisible_prefix(value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", value)
    value = re.sub(r"\s+", " ", value, flags=re.UNICODE).strip(" .")
    return value[:max_length].rstrip(" .") or "Новая заметка"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique path for {path}")


def words(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]
