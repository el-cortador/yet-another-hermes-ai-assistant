from unittest import TestCase

from app.text_utils import split_discord_message


class DiscordBotTests(TestCase):
    def test_split_discord_message_keeps_short_text(self) -> None:
        self.assertEqual(split_discord_message("short", max_len=10), ["short"])

    def test_split_discord_message_splits_long_paragraphs(self) -> None:
        chunks = split_discord_message("one\n\ntwo\n\nthree", max_len=10)
        self.assertEqual(chunks, ["one\n\ntwo", "three"])
