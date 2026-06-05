from unittest import TestCase
from unittest import skipUnless

try:
    import bs4  # noqa: F401
except ImportError:
    HAS_BS4 = False
else:
    HAS_BS4 = True

from app.ingestion import extract_telegram_post_text, telegram_public_web_url


class TelegramIngestionTests(TestCase):
    def test_telegram_public_web_url_normalizes_post_link(self) -> None:
        self.assertEqual(
            telegram_public_web_url("https://t.me/vibecoding_tg/3197"),
            "https://t.me/s/vibecoding_tg/3197",
        )

    @skipUnless(HAS_BS4, "beautifulsoup4 is not installed in this Python environment")
    def test_extract_telegram_post_text(self) -> None:
        html = """
        <div class="tgme_widget_message" data-post="vibecoding_tg/3197">
          <a class="tgme_widget_message_author_name"><span>Vibe Coding</span></a>
          <div class="tgme_widget_message_text js-message_text" dir="auto">
            Первая строка<br/>Вторая строка <a href="https://example.com">ссылка</a>
          </div>
          <a class="tgme_widget_message_date"><time datetime="2026-06-05T12:00:00+00:00"></time></a>
        </div>
        """

        text = extract_telegram_post_text(html, "https://t.me/s/vibecoding_tg/3197")

        self.assertIn("Vibe Coding", text)
        self.assertIn("2026-06-05T12:00:00+00:00", text)
        self.assertIn("Первая строка", text)
        self.assertIn("https://example.com", text)
