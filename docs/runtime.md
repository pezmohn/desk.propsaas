# Runtime

Use the normal Python 3.13 executable directly on this machine:

```powershell
$env:PYTHON_EXE = "C:\Users\leo\AppData\Local\Programs\Python\Python313\python.exe"
```

Do not use bare `py` for the app runtime here. The launcher currently defaults to the experimental free-threaded `python3.13t.exe`, where `pydantic_core` is not importable.

## Local Dry-Run Setup

From the repository root:

```powershell
$env:TELEGRAM_DRY_RUN = "true"
$env:DATABASE_URL = "sqlite:///./state/premarket_operator.sqlite"

& "C:\Users\leo\AppData\Local\Programs\Python\Python313\python.exe" -m premarket_operator.ops.admin_cli generate-report --email local@example.com --display-name "Local Test User" --telegram-chat-id 12345 --trading-day 2026-05-22
& "C:\Users\leo\AppData\Local\Programs\Python\Python313\python.exe" -m premarket_operator.ops.admin_cli deliver-report --email local@example.com --trading-day 2026-05-22 --dry-run
```

## Run FastAPI Locally

```powershell
$env:TELEGRAM_DRY_RUN = "true"
$env:DATABASE_URL = "sqlite:///./state/premarket_operator.sqlite"

& "C:\Users\leo\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn premarket_operator.app.main:app --host 127.0.0.1 --port 8000
```

## Dry-Run Webhook Request

In another PowerShell window:

```powershell
$body = @{
  update_id = 920401
  message = @{
    message_id = 920401
    chat = @{ id = 12345 }
    text = "What matters most on MU?"
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/telegram/webhook" -ContentType "application/json" -Body $body
```

Expected result: `ok` is `true`, `dry_run` is `true`, and the response includes `daily_report_id`, `outbound_telegram_message_id`, and a negative dry-run Telegram `message_id`.

## Live Telegram Checklist

1. Set `TELEGRAM_BOT_TOKEN` for the bot.
2. Set `TELEGRAM_DRY_RUN=false`.
3. Ensure the target user has `telegram_chat_id` stored.
4. Generate and deliver that user's report once.
5. Expose the local app through HTTPS or deploy it to the VPS.
6. Register Telegram webhook URL with `setWebhook`.
7. Reply to the delivered report message in Telegram.
8. Verify one inbound `telegram_messages` row, one assistant `chat_messages` row, one outbound `assistant_reply` row, and usage ledger entries.
