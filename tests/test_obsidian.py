from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from app.obsidian import (
    ObsidianVault,
    extract_title,
    normalize_obsidian_markdown,
    normalize_tags,
    note_filename,
    slugify,
    strip_markdown_fence,
)


class ObsidianVaultTests(TestCase):
    def test_extract_title_prefers_frontmatter(self) -> None:
        markdown = '---\ntitle: "Frontmatter Title"\n---\n\n# Heading'
        self.assertEqual(extract_title(markdown), "Frontmatter Title")

    def test_write_note_creates_unique_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            vault = ObsidianVault(Path(temp_dir), "Inbox/AI")
            first = vault.write_note("# Test Note\n")
            second = vault.write_note("# Test Note\n")

        self.assertNotEqual(first.name, second.name)

    def test_write_note_uses_sentence_title_filename(self) -> None:
        with TemporaryDirectory() as temp_dir:
            vault = ObsidianVault(Path(temp_dir), "Inbox/AI")
            path = vault.write_note("# Как правильно организовывать работу в Claude Code и подобных\n")

        self.assertEqual(path.name, "Как правильно организовывать работу в Claude Code и подобных.md")

    def test_slugify_keeps_cyrillic_words(self) -> None:
        self.assertEqual(slugify("Тестовая заметка!"), "тестовая-заметка")

    def test_note_filename_keeps_sentence_but_removes_invalid_chars(self) -> None:
        self.assertEqual(
            note_filename("Как правильно: организовывать / работу в Claude Code?"),
            "Как правильно организовывать работу в Claude Code",
        )

    def test_strip_markdown_fence(self) -> None:
        self.assertEqual(strip_markdown_fence("```markdown\n# Title\n```"), "# Title")

    def test_normalize_obsidian_markdown_rewrites_frontmatter(self) -> None:
        markdown = dedent("""
        ---
        title: Test
        source: https://example.com
        created: 2026-06-05
        tags:
          - системный промпт
          - AI
        ---

        # Test
        """)

        normalized = normalize_obsidian_markdown(markdown)

        self.assertTrue(normalized.startswith("---\ntitle: \"Test\""))
        self.assertIn("  - системный-промпт", normalized)
        self.assertIn("  - ai", normalized)

    def test_normalize_tags_deduplicates_and_slugifies(self) -> None:
        self.assertEqual(normalize_tags(["AI", "системный промпт", "#AI"]), ["ai", "системный-промпт"])
