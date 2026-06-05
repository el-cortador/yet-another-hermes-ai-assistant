from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
TELEGRAM_POST_RE = re.compile(
    r"^/(?:s/)?(?P<channel>[A-Za-z0-9_]+)/(?P<post_id>\d+)/?$"
)


@dataclass(frozen=True)
class IngestedContent:
    text: str
    source_url: str | None


async def ingest_message(content: str) -> IngestedContent:
    urls = URL_RE.findall(content)
    if not urls:
        return IngestedContent(text=content.strip(), source_url=None)

    source_url = urls[0].rstrip(").,]")
    fetched = await fetch_readable_text(source_url)
    surrounding_text = URL_RE.sub("", content).strip()
    parts = [part for part in [surrounding_text, fetched] if part]
    return IngestedContent(text="\n\n".join(parts) or source_url, source_url=source_url)


async def fetch_readable_text(url: str) -> str:
    import aiohttp
    from bs4 import BeautifulSoup

    telegram_web_url = telegram_public_web_url(url)
    if telegram_web_url:
        telegram_text = await fetch_telegram_post_text(telegram_web_url)
        if telegram_text:
            return telegram_text

    headers = {"User-Agent": "Mozilla/5.0 HermesObsidianAssistant/0.1"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                html = await response.text(errors="ignore")
    except Exception:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    body = soup.get_text("\n", strip=True)
    text = "\n".join(part for part in [title, body] if part)
    return text[:30000]


def telegram_public_web_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"t.me", "telegram.me"}:
        return None
    match = TELEGRAM_POST_RE.match(parsed.path)
    if not match:
        return None
    channel = match.group("channel")
    post_id = match.group("post_id")
    return f"https://t.me/s/{channel}/{post_id}"


async def fetch_telegram_post_text(url: str) -> str:
    import aiohttp

    headers = {"User-Agent": "Mozilla/5.0 HermesObsidianAssistant/0.1"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                html = await response.text(errors="ignore")
    except Exception:
        return ""
    return extract_telegram_post_text(html, url)


def extract_telegram_post_text(html: str, url: str) -> str:
    from bs4 import BeautifulSoup

    parsed = urlparse(url)
    match = TELEGRAM_POST_RE.match(parsed.path)
    post_key = None
    if match:
        post_key = f"{match.group('channel')}/{match.group('post_id')}"

    soup = BeautifulSoup(html, "html.parser")
    message = None
    if post_key:
        message = soup.select_one(f'.tgme_widget_message[data-post="{post_key}"]')
    if message is None:
        message = soup.select_one(".tgme_widget_message")
    if message is None:
        return extract_meta_description(soup)

    parts: list[str] = []
    author = text_from_selector(message, ".tgme_widget_message_author_name")
    published_at = None
    time_el = message.select_one("time[datetime]")
    if time_el:
        published_at = time_el.get("datetime")
    if author:
        parts.append(f"Telegram channel: {author}")
    if published_at:
        parts.append(f"Published at: {published_at}")

    text_el = message.select_one(".tgme_widget_message_text")
    if text_el:
        parts.append(clean_text(text_el.get_text("\n", strip=True)))

    preview_title = text_from_selector(message, ".tgme_widget_message_link_preview_title")
    preview_description = text_from_selector(message, ".tgme_widget_message_link_preview_description")
    if preview_title or preview_description:
        parts.append("Link preview:\n" + "\n".join(
            item for item in [preview_title, preview_description] if item
        ))

    links = []
    for link in message.select("a[href]"):
        href = link.get("href", "").strip()
        label = clean_text(link.get_text(" ", strip=True))
        if href and href.startswith(("http://", "https://")):
            links.append(f"- {label or href}: {href}")
    if links:
        parts.append("Links:\n" + "\n".join(dict.fromkeys(links)))

    return "\n\n".join(part for part in parts if part)[:30000]


def extract_meta_description(soup) -> str:
    for selector in [
        'meta[property="og:description"]',
        'meta[name="description"]',
        'meta[property="twitter:description"]',
    ]:
        element = soup.select_one(selector)
        if element and element.get("content"):
            return clean_text(element["content"])
    return ""


def text_from_selector(soup, selector: str) -> str:
    element = soup.select_one(selector)
    if element is None:
        return ""
    return clean_text(element.get_text(" ", strip=True))


def clean_text(value: str) -> str:
    value = unescape(value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()
