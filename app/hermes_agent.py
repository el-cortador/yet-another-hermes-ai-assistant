from __future__ import annotations

import logging
from datetime import datetime

from app.llm import OpenRouterClient


LOGGER = logging.getLogger(__name__)


class HermesAgent:
    """Local Hermes-compatible agent layer for one-container deployment."""

    def __init__(self, llm: OpenRouterClient) -> None:
        self._llm = llm

    async def make_obsidian_note(self, source_text: str, source_url: str | None) -> str:
        system = (
            "Ты ИИ-ассистент для личной базы знаний Obsidian. "
            "Преобразуй входной материал в полезную Markdown-заметку на русском. "
            "Верни только Markdown. Используй YAML frontmatter с полями title, source, created, tags. "
            "Не оборачивай ответ в ```markdown или другие code fences. "
            "Не выдумывай факты, дату публикации или содержание, которого нет во входном материале. "
            "В теле заметки нужны разделы: Кратко, Ключевые идеи, Где пригодится, Связи. "
            "Связи оформляй как Obsidian wikilinks вида [[Тема]]."
        )
        user = f"Источник: {source_url or 'ручной ввод'}\n\nМатериал:\n{source_text}"
        try:
            return await self._llm.chat(system, user)
        except Exception:
            LOGGER.exception("LLM note generation failed; creating raw fallback note")
            return fallback_note(source_text, source_url)

    async def answer_from_notes(self, question: str, notes_context: str) -> str:
        system = (
            "Ты отвечаешь на вопросы по личной базе знаний Obsidian. "
            "Опирайся только на предоставленный контекст заметок. "
            "Если данных не хватает, скажи это прямо. "
            "В конце добавь короткий список заметок-источников, если они есть в контексте."
        )
        user = f"Вопрос:\n{question}\n\nКонтекст заметок:\n{notes_context}"
        return await self._llm.chat(system, user)


def fallback_note(source_text: str, source_url: str | None) -> str:
    created = datetime.now().strftime("%Y-%m-%d")
    title = fallback_title(source_text, source_url)
    source = source_url or "ручной ввод"
    excerpt = source_text.strip()[:30000] or "Контент не извлечен."
    return f"""---
title: "{escape_yaml(title)}"
source: "{escape_yaml(source)}"
created: {created}
tags:
  - inbox
  - needs-processing
---

# {title}

## Кратко

Материал сохранен в сыром виде, потому что LLM-сервис был временно недоступен во время обработки.

## Исходный материал

{excerpt}

## Связи

[[Inbox]]
"""


def fallback_title(source_text: str, source_url: str | None) -> str:
    for line in source_text.splitlines():
        line = line.strip()
        if line:
            return line[:80]
    if source_url:
        return f"Материал из {source_url}"
    return "Новая входящая заметка"


def escape_yaml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
