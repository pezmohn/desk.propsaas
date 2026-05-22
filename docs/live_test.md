# First Live Telegram Test

This checklist is intentionally narrow: one user, one report, one reply, one assistant response.

## Assumptions

- Run from the repository root.
- Use the normal Python runtime, not bare `py`:

```powershell
$python = "C:\Users\leo\AppData\Local\Programs\Python\Python313\python.exe"
```

- Runtime config is read from environment variables. `.env.example` is documentation only.
- `state/premarket_operator.sqlite` is the local test database.

## 0. Set Live-Test Environment

```powershell
$env:DATABASE_URL = "sqlite:///./state/premarket_operator.sqlite"
$env:TELEGRAM_DRY_RUN = "true"
$env:TELEGRAM_BOT_TOKEN = "<bot-token>"
$env:TEST_EMAIL = "local@example.com"
$env:TEST_CHAT_ID = "<your-telegram-chat-id>"
$env:TEST_DAY = "2026-05-22"
```

Verify token loading without printing the token:

```powershell
& $python -m premarket_operator.ops.admin_cli check-config
```

Expected:

- `telegram_dry_run` is `true`
- `telegram_bot_token_present` is `true`
- `telegram_bot_token_length` is greater than `20`
- `telegram_bot_token_source` is `TELEGRAM_BOT_TOKEN env var`

## 1. Create One User And One Report

```powershell
& $python -m premarket_operator.ops.admin_cli generate-report --email $env:TEST_EMAIL --display-name "Live Test User" --telegram-chat-id $env:TEST_CHAT_ID --trading-day $env:TEST_DAY
```

Verify database:

```powershell
& $python -c "import sqlite3, os; c=sqlite3.connect('state/premarket_operator.sqlite'); print(c.execute('select id,email,telegram_chat_id,status from users where email=?',(os.environ['TEST_EMAIL'],)).fetchall()); print(c.execute('select id,user_id,trading_day,status,length(body_text),json_extract(context_json,''$.watchlist[0]'') from daily_reports order by created_at desc limit 1').fetchall())"
```

Expected:

- one `users` row with the test email and chat id
- one `daily_reports` row for `TEST_DAY`
- `status` is `generated`
- `body_text` length is non-zero
- first watchlist item is present

## 2. Dry-Run Send The Report

```powershell
& $python -m premarket_operator.ops.admin_cli deliver-report --email $env:TEST_EMAIL --trading-day $env:TEST_DAY --dry-run
```

Verify database:

```powershell
& $python -c "import sqlite3; c=sqlite3.connect('state/premarket_operator.sqlite'); print(c.execute(\"select direction,message_type,telegram_chat_id,telegram_message_id,daily_report_id from telegram_messages order by created_at desc limit 3\").fetchall()); print(c.execute(\"select status,sent_at from daily_reports order by updated_at desc limit 1\").fetchall())"
```

Expected:

- latest `telegram_messages` row has `direction='outbound'`
- `message_type='daily_report'`
- `telegram_message_id` is negative because this is dry-run
- report `status='sent'`

## 3. Dry-Run Webhook Locally

Start the app:

```powershell
$env:TELEGRAM_DRY_RUN = "true"
& $python -m uvicorn premarket_operator.app.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell window:

```powershell
$body = @{
  update_id = 990001
  message = @{
    message_id = 990001
    chat = @{ id = [int64]$env:TEST_CHAT_ID }
    text = "What matters most on MU?"
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/telegram/webhook" -ContentType "application/json" -Body $body
```

Expected response:

- `ok=true`
- `dry_run=true`
- `guardrail_reason` is empty/null
- `daily_report_id` is present
- `telegram_message_id` is negative

Verify database:

```powershell
& $python -c "import sqlite3; c=sqlite3.connect('state/premarket_operator.sqlite'); print(c.execute(\"select role,substr(content,1,80),daily_report_id from chat_messages order by created_at desc limit 4\").fetchall()); print(c.execute(\"select direction,message_type,telegram_message_id,daily_report_id from telegram_messages order by created_at desc limit 4\").fetchall()); print(c.execute(\"select feature,limit_allowed,daily_report_id from usage_ledger order by created_at desc limit 6\").fetchall())"
```

Expected:

- one recent `chat_messages` row with `role='user'`
- one recent `chat_messages` row with `role='assistant'`
- one recent `telegram_messages` row with `message_type='user_reply'`
- one recent `telegram_messages` row with `message_type='assistant_reply'`
- usage includes `inbound_reply_attempt`, `assistant_report_reply`, `telegram_assistant_delivery`

## 4. Switch To One Real Telegram Send

Stop uvicorn if it is running.

Set live mode:

```powershell
$env:TELEGRAM_DRY_RUN = "false"
& $python -m premarket_operator.ops.admin_cli check-config
```

Expected:

- `telegram_dry_run` is `false`
- token is present

Send the already persisted report to the single test user:

```powershell
& $python -m premarket_operator.ops.admin_cli deliver-report --email $env:TEST_EMAIL --trading-day $env:TEST_DAY
```

Expected:

- exactly one Telegram message arrives in the test chat
- command output has a positive `telegram_message_id`

## 5. One Real Reply Test

Expose the app through HTTPS or deploy it.

Before registering anything, check for stale webhook configuration:

```powershell
Invoke-RestMethod -Method Get -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

Expected before the live test:

- `ok` is `true`
- `result.url` is empty, or it is the exact URL you intend to replace
- `result.pending_update_count` is `0` or understood before proceeding

Register the webhook:

```powershell
$webhookUrl = "https://<public-host>/telegram/webhook"
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/setWebhook" -Body @{ url = $webhookUrl }
```

Verify Telegram accepted the webhook:

```powershell
Invoke-RestMethod -Method Get -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

Expected after registration:

- `ok` is `true`
- `result.url` equals `$webhookUrl`
- `result.last_error_message` is empty/null

Start the app with live mode:

```powershell
$env:TELEGRAM_DRY_RUN = "false"
& $python -m uvicorn premarket_operator.app.main:app --host 0.0.0.0 --port 8000
```

Reply in Telegram to the delivered report:

```text
What matters most on MU?
```

Success criteria:

- exactly one assistant response appears in Telegram
- response references MU report levels/context
- no order execution or buy/sell instruction
- database has one inbound `user_reply`, one outbound `assistant_reply`, one user chat message, one assistant chat message
- usage ledger has successful delivery and assistant reply entries

After the reply, check Telegram webhook health:

```powershell
Invoke-RestMethod -Method Get -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

Expected after the reply:

- `result.url` still equals `$webhookUrl`
- `result.last_error_message` is empty/null
- `result.pending_update_count` is `0`

## Failure Checks

If no Telegram response arrives:

```powershell
& $python -c "import sqlite3; c=sqlite3.connect('state/premarket_operator.sqlite'); print(c.execute(\"select feature,limit_allowed,metadata_json from usage_ledger order by created_at desc limit 10\").fetchall())"
```

Look for `telegram_webhook_failed_attempt`.

If more than one response arrives:

```powershell
& $python -c "import sqlite3; c=sqlite3.connect('state/premarket_operator.sqlite'); print(c.execute(\"select direction,message_type,telegram_message_id,text from telegram_messages order by created_at desc limit 20\").fetchall())"
```

Stop the app immediately and remove the webhook.

## Rollback / Cleanup

Disable webhook:

```powershell
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/deleteWebhook"
```

Verify cleanup:

```powershell
Invoke-RestMethod -Method Get -Uri "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

Expected after cleanup:

- `ok` is `true`
- `result.url` is empty
- `result.pending_update_count` is `0` or no longer increasing

Stop local app:

```powershell
Get-Process | Where-Object { $_.ProcessName -like "python*" } | Stop-Process
```

Pause the test user locally:

```powershell
& $python -c "import sqlite3, os; c=sqlite3.connect('state/premarket_operator.sqlite'); c.execute('update users set status=''paused'' where email=?',(os.environ['TEST_EMAIL'],)); c.commit(); print('paused test user')"
```

For a clean local reset only:

```powershell
Remove-Item -LiteralPath .\state\premarket_operator.sqlite
```
