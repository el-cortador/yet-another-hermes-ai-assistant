from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging

import discord

from app.config import Config
from app.hermes_agent import HermesAgent
from app.ingestion import ingest_message
from app.obsidian import ObsidianVault
from app.text_utils import split_discord_message


LOGGER = logging.getLogger(__name__)


class KnowledgeBot(discord.Client):
    def __init__(self, config: Config, agent: HermesAgent, vault: ObsidianVault) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._config = config
        self._agent = agent
        self._vault = vault

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not self._is_allowed(message):
            return
        LOGGER.info(
            "Received message in channel=%s author=%s length=%s attachments=%s",
            message.channel.id,
            message.author.id,
            len(message.content),
            len(message.attachments),
        )
        if message.channel.id == self._config.discord_ingest_channel_id:
            await self._handle_ingest(message)
        elif message.channel.id == self._config.discord_qa_channel_id:
            await self._handle_question(message)

    def _is_allowed(self, message: discord.Message) -> bool:
        if message.guild is None:
            return False
        return (
            message.guild.id in self._config.discord_allowed_guild_ids
            and message.author.id in self._config.discord_allowed_user_ids
        )

    async def _handle_ingest(self, message: discord.Message) -> None:
        content = message.content.strip()
        attachment_texts = await read_text_attachments(message)
        if attachment_texts:
            content = "\n\n".join([content, *attachment_texts]).strip()
        if not content:
            return
        async with safe_typing(message):
            try:
                ingested = await ingest_message(content)
                markdown = await self._agent.make_obsidian_note(ingested.text, ingested.source_url)
                path = self._vault.write_note(markdown)
            except Exception:
                LOGGER.exception("Failed to ingest message")
                await safe_reply(message, "Не смог обработать материал. Подробности в логах контейнера.")
                return

        rel_path = path.relative_to(self._vault.root).as_posix()
        await safe_reply(message, f"Сохранил заметку: `{rel_path}`")

    async def _handle_question(self, message: discord.Message) -> None:
        question = message.content.strip()
        if not question:
            return
        async with safe_typing(message):
            try:
                notes = self._vault.search(question)
                context = self._vault.build_context(notes)
                answer = self._empty_vault_answer() if not context else await self._agent.answer_from_notes(question, context)
            except Exception:
                LOGGER.exception("Failed to answer question")
                await safe_reply(message, "Не смог ответить по базе знаний. Подробности в логах контейнера.")
                return

        for chunk in split_discord_message(answer):
            await safe_reply(message, chunk)

    def _empty_vault_answer(self) -> str:
        return "Не нашел релевантных заметок в Obsidian vault по этому вопросу."


async def read_text_attachments(message: discord.Message) -> list[str]:
    texts: list[str] = []
    for attachment in message.attachments:
        content_type = attachment.content_type or ""
        filename = attachment.filename.lower()
        if not (
            content_type.startswith("text/")
            or filename.endswith((".txt", ".md", ".markdown"))
        ):
            continue
        data = await attachment.read()
        texts.append(data.decode("utf-8", errors="replace")[:30000])
    return texts


async def safe_reply(message: discord.Message, content: str, attempts: int = 3) -> None:
    for attempt in range(1, attempts + 1):
        try:
            await message.reply(content)
            return
        except Exception:
            LOGGER.exception("Failed to reply to Discord message, attempt %s/%s", attempt, attempts)
            if attempt < attempts:
                await asyncio.sleep(2 * attempt)


@asynccontextmanager
async def safe_typing(message: discord.Message):
    manager = message.channel.typing()
    entered = False
    try:
        await manager.__aenter__()
        entered = True
    except Exception:
        LOGGER.warning("Could not send Discord typing indicator", exc_info=True)
    try:
        yield
    finally:
        if entered:
            try:
                await manager.__aexit__(None, None, None)
            except Exception:
                LOGGER.warning("Could not stop Discord typing indicator", exc_info=True)
