from __future__ import annotations

import logging
import time

from app.config import Config
from app.discord_bot import KnowledgeBot
from app.hermes_agent import HermesAgent
from app.llm import OpenRouterClient
from app.obsidian import ObsidianVault


def main() -> None:
    config = Config.load()
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    llm = OpenRouterClient(config.openrouter_api_key, config.openrouter_model)
    agent = HermesAgent(llm)
    vault = ObsidianVault(config.obsidian_vault_path, config.obsidian_inbox_dir)
    while True:
        bot = KnowledgeBot(config, agent, vault)
        try:
            bot.run(config.discord_bot_token)
        except KeyboardInterrupt:
            raise
        except Exception:
            logging.exception("Discord client stopped unexpectedly; retrying in 15 seconds")
            time.sleep(15)


if __name__ == "__main__":
    main()
