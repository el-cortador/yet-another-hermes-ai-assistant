from types import SimpleNamespace
from unittest import TestCase
from unittest import skipUnless
from unittest.mock import patch

try:
    from discord.errors import LoginFailure
    from app.main import main
except ModuleNotFoundError:
    HAS_DISCORD = False
    LoginFailure = None
    main = None
else:
    HAS_DISCORD = True

@skipUnless(HAS_DISCORD, "discord.py is not installed in this Python environment")
class MainTests(TestCase):
    @patch("app.main.time.sleep")
    @patch("app.main.KnowledgeBot")
    @patch("app.main.ObsidianVault")
    @patch("app.main.HermesAgent")
    @patch("app.main.OpenRouterClient")
    @patch("app.main.Config.load")
    def test_main_exits_on_discord_login_failure(
        self,
        load_config,
        openrouter_client,
        hermes_agent,
        obsidian_vault,
        knowledge_bot,
        sleep,
    ) -> None:
        load_config.return_value = SimpleNamespace(
            openrouter_api_key="key",
            openrouter_model="model",
            discord_bot_token="token",
            obsidian_vault_path="vault",
            obsidian_inbox_dir="Inbox/AI",
            log_level="INFO",
        )
        knowledge_bot.return_value.run.side_effect = LoginFailure("Improper token has been passed.")

        with self.assertRaises(SystemExit) as error:
            main()

        self.assertEqual(error.exception.code, 1)
        sleep.assert_not_called()
