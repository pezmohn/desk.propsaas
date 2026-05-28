from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from premarket_operator.auth.api import router as auth_router
from premarket_operator.core.config import get_settings
from premarket_operator.core.time import trading_day_for
from premarket_operator.dashboard.api import router as dashboard_router
from premarket_operator.db.session import SessionLocal
from premarket_operator.reports.api import router as reports_router
from premarket_operator.settings.api import router as settings_router
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.webhook import TelegramWebhookError, process_telegram_webhook_update

app = FastAPI(title="Premarket Operator")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(dashboard_router)


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
