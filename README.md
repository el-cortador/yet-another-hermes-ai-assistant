# yet-another-hermes-ai-assistant

Discord-ассистент для пополнения Obsidian vault и вопросов по базе знаний.

## Каналы

- `DISCORD_INGEST_CHANNEL_ID`: канал для ссылок, постов, статей и текстов, которые нужно сохранить.
- `DISCORD_QA_CHANNEL_ID`: канал для вопросов по Obsidian vault.

## Запуск

1. Проверь `.env`: токены Discord/OpenRouter, ID сервера, ID пользователя и двух каналов.
2. Убедись, что Obsidian vault доступен на хосте по `HOST_OBSIDIAN_VAULT_PATH`.
3. Собери и запусти контейнер:

```powershell
docker compose up -d --build
```

Логи:

```powershell
docker compose logs -f hermes-assistant
```

## Как работает

Сообщения в ingest-канале превращаются в Markdown-заметки в папку `OBSIDIAN_INBOX_DIR` внутри vault.
Сообщения в QA-канале ищут релевантные `.md` файлы в vault и отправляют найденный контекст в локальный Hermes-слой, который использует OpenRouter.
