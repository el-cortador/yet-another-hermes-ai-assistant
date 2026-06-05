from __future__ import annotations

import asyncio
import logging

import aiohttp


LOGGER = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def chat(self, system: str, user: str, attempts: int = 3) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.hermes-assistant",
            "X-Title": "Hermes Obsidian Assistant",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=120, connect=30)
                connector = aiohttp.TCPConnector(force_close=True, ttl_dns_cache=60)
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as error:
                last_error = error
                LOGGER.warning("OpenRouter request failed, attempt %s/%s: %r", attempt, attempts, error)
                if attempt < attempts:
                    await asyncio.sleep(3 * attempt)
        raise RuntimeError("OpenRouter request failed after retries") from last_error
