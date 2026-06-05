from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _parse_int_set(value: str) -> set[int]:
    return {int(item.strip()) for item in value.split(",") if item.strip()}


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str
    openrouter_model: str
    discord_bot_token: str
    discord_allowed_guild_ids: set[int]
    discord_allowed_user_ids: set[int]
    discord_ingest_channel_id: int
    discord_qa_channel_id: int
    obsidian_vault_path: Path
    obsidian_inbox_dir: str
    log_level: str

    @classmethod
    def load(cls) -> "Config":
        load_dotenv()
        return cls(
            openrouter_api_key=_required("OPENROUTER_API_KEY"),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash"),
            discord_bot_token=_required("DISCORD_BOT_TOKEN"),
            discord_allowed_guild_ids=_parse_int_set(_required("DISCORD_ALLOWED_GUILD_IDS")),
            discord_allowed_user_ids=_parse_int_set(_required("DISCORD_ALLOWED_USER_IDS")),
            discord_ingest_channel_id=int(_required("DISCORD_INGEST_CHANNEL_ID")),
            discord_qa_channel_id=int(_required("DISCORD_QA_CHANNEL_ID")),
            obsidian_vault_path=Path(os.getenv("OBSIDIAN_VAULT_PATH", "/vault")),
            obsidian_inbox_dir=os.getenv("OBSIDIAN_INBOX_DIR", "Inbox/AI"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
