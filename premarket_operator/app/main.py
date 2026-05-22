from fastapi import FastAPI, Request

from premarket_operator.core.config import get_settings
from premarket_operator.core.time import trading_day_for
from premarket_operator.db.session import SessionLocal
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.webhook import TelegramWebhookError, process_telegram_webhook_update

app = FastAPI(title="Premarket Operator")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    update = await request.json()
    settings = get_settings()
    with SessionLocal() as session:
        try:
            result = process_telegram_webhook_update(
                session,
                update=update,
                trading_day=trading_day_for(),
                telegram_client=TelegramClient(dry_run=settings.telegram_dry_run),
            )
            session.commit()
            return {
                "ok": True,
                "user_id": str(result.user_id),
                "daily_report_id": str(result.daily_report_id),
                "outbound_telegram_message_id": str(result.outbound_telegram_message_id),
                "telegram_message_id": result.telegram_message_id,
                "dry_run": result.dry_run,
                "guardrail_reason": result.guardrail_reason,
            }
        except TelegramWebhookError as exc:
            session.commit()
            return {"ok": False, "error": str(exc)}
