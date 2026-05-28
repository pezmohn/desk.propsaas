from __future__ import annotations

import argparse
import getpass
import json
import os
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from premarket_operator.auth.service import set_user_password
from premarket_operator.core.config import get_settings
from premarket_operator.core.time import now_utc
from premarket_operator.chat.service import answer_inbound_report_reply
from premarket_operator.db.models import User
from premarket_operator.db.session import SessionLocal, create_all_tables
from premarket_operator.jobs.daily_reports import deliver_reports_for_all_eligible_users
from premarket_operator.plans.service import ensure_default_plan_for_user
from premarket_operator.reports.generator import generate_premarket_report_from_gex_rows
from premarket_operator.reports.service import save_generated_report
from premarket_operator.telegram.webhook import handle_telegram_update, process_telegram_webhook_update
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.service import deliver_daily_report_to_user
from premarket_operator.users.service import get_or_create_user


def _default_stub_rows(trading_day: date) -> list[dict]:
    day = trading_day.isoformat()
    captured_at = f"{day}T13:15:00+00:00"
    return [
        {
            "ticker": "MU",
            "trading_day": day,
            "captured_at": captured_at,
            "session_phase": "premarket",
            "spot_price": 100.0,
            "gamma_flip": 101.0,
            "call_wall": 104.0,
            "put_wall": 96.0,
            "dist_to_flip_pct": -1.0,
            "dist_to_call_wall_pct": -4.0,
            "dist_to_put_wall_pct": 4.0,
            "regime": "VOLATIL",
            "near_support_levels_json": [96.0, 98.0],
            "near_resistance_levels_json": [102.0, 104.0],
            "extra": {"signed_gex_by_strike": {97.0: -20_000.0, 99.0: -15_000.0}},
        },
        {
            "ticker": "PLTR",
            "trading_day": day,
            "captured_at": captured_at,
            "session_phase": "premarket",
            "spot_price": 100.0,
            "gamma_flip": 99.0,
            "call_wall": 104.0,
            "put_wall": 96.0,
            "dist_to_flip_pct": 1.0,
            "dist_to_call_wall_pct": -4.0,
            "dist_to_put_wall_pct": 4.0,
            "regime": "STABIL",
            "near_support_levels_json": [96.0, 98.0],
            "near_resistance_levels_json": [102.0, 104.0],
            "extra": {"signed_gex_by_strike": {98.0: -4_000.0, 102.0: 500.0}},
        },
    ]


def _load_rows(path: str | None, trading_day: date) -> list[dict]:
    if path is None:
        return _default_stub_rows(trading_day)
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input rows JSON must be a list of row objects.")
    return payload


def _get_or_create_user(
    *,
    email: str | None,
    display_name: str | None,
    telegram_chat_id: str | None,
) -> User:
    with SessionLocal() as session:
        user = get_or_create_user(
            session,
            email=email,
            display_name=display_name,
            telegram_chat_id=telegram_chat_id,
        )
        ensure_default_plan_for_user(session, user_id=user.id)
        session.commit()
        session.refresh(user)
        return user


def generate_one_report(args: argparse.Namespace) -> int:
    create_all_tables()
    trading_day = date.fromisoformat(args.trading_day) if args.trading_day else now_utc().date()
    user = _get_or_create_user(
        email=args.email,
        display_name=args.display_name,
        telegram_chat_id=args.telegram_chat_id,
    )
    rows = _load_rows(args.rows_json, trading_day)
    generated = generate_premarket_report_from_gex_rows(
        user_id=user.id,
        trading_day=trading_day,
        rows=rows,
        history_by_ticker={
            "MU": [1_000.0, 2_000.0, 3_000.0, 4_000.0, 5_000.0],
            "PLTR": [1_000.0, 1_200.0, 1_300.0, 1_400.0, 1_500.0],
        },
        limit=args.limit,
    )

    with SessionLocal() as session:
        report = save_generated_report(session, generated)
        session.commit()
        session.refresh(report)
        print(
            json.dumps(
                {
                    "user_id": str(report.user_id),
                    "daily_report_id": str(report.id),
                    "trading_day": report.trading_day.isoformat(),
                    "report_type": report.report_type,
                    "status": report.status,
                    "watchlist": report.context_json.get("watchlist", []),
                },
                indent=2,
            )
        )
    return 0


def deliver_one_report(args: argparse.Namespace) -> int:
    create_all_tables()
    trading_day = date.fromisoformat(args.trading_day) if args.trading_day else now_utc().date()
    with SessionLocal() as session:
        user = _resolve_user(session, user_id=args.user_id, email=args.email)
        result = deliver_daily_report_to_user(
            session,
            user_id=user.id,
            trading_day=trading_day,
            telegram_client=TelegramClient(dry_run=args.dry_run),
        )
        session.commit()
        print(
            json.dumps(
                {
                    "user_id": str(result.user_id),
                    "daily_report_id": str(result.daily_report_id),
                    "telegram_message_id": result.telegram_message_id,
                    "dry_run": result.dry_run,
                },
                indent=2,
            )
        )
    return 0


def deliver_all_reports(args: argparse.Namespace) -> int:
    create_all_tables()
    trading_day = date.fromisoformat(args.trading_day) if args.trading_day else now_utc().date()
    with SessionLocal() as session:
        result = deliver_reports_for_all_eligible_users(
            session,
            trading_day=trading_day,
            telegram_client=TelegramClient(dry_run=args.dry_run),
        )
        session.commit()
        print(
            json.dumps(
                {
                    "delivered": [
                        {
                            "user_id": str(item.user_id),
                            "daily_report_id": str(item.daily_report_id),
                            "telegram_message_id": item.telegram_message_id,
                            "dry_run": item.dry_run,
                        }
                        for item in result.delivered
                    ],
                    "skipped": result.skipped,
                },
                indent=2,
            )
        )
    return 0


def simulate_inbound_reply(args: argparse.Namespace) -> int:
    create_all_tables()
    trading_day = date.fromisoformat(args.trading_day) if args.trading_day else now_utc().date()
    with SessionLocal() as session:
        user = _resolve_user(session, user_id=args.user_id, email=args.email)
        if not user.telegram_chat_id:
            raise ValueError("User must have telegram_chat_id to simulate an inbound Telegram reply.")
        update = _build_simulated_update(
            chat_id=user.telegram_chat_id,
            message_id=args.message_id,
            text=args.text,
            reply_to_message_id=args.reply_to_message_id,
        )
        route = handle_telegram_update(session, update=update, trading_day=trading_day)
        session.commit()
        print(
            json.dumps(
                {
                    "user_id": str(route.user_id),
                    "daily_report_id": str(route.daily_report_id),
                    "telegram_message_id": str(route.telegram_message_id),
                    "chat_message_id": str(route.chat_message_id),
                    "resolution_method": route.resolution_method,
                    "text": route.text,
                },
                indent=2,
            )
        )
    return 0


def simulate_answer_reply(args: argparse.Namespace) -> int:
    create_all_tables()
    trading_day = date.fromisoformat(args.trading_day) if args.trading_day else now_utc().date()
    with SessionLocal() as session:
        user = _resolve_user(session, user_id=args.user_id, email=args.email)
        if not user.telegram_chat_id:
            raise ValueError("User must have telegram_chat_id to simulate an inbound Telegram reply.")
        update = _build_simulated_update(
            chat_id=user.telegram_chat_id,
            message_id=args.message_id,
            text=args.text,
            reply_to_message_id=args.reply_to_message_id,
        )
        result = answer_inbound_report_reply(session, update=update, trading_day=trading_day)
        session.commit()
        print(
            json.dumps(
                {
                    "user_id": str(result.route.user_id),
                    "daily_report_id": str(result.route.daily_report_id),
                    "user_chat_message_id": str(result.route.chat_message_id),
                    "assistant_chat_message_id": str(result.assistant_chat_message_id),
                    "resolution_method": result.route.resolution_method,
                    "model": result.model,
                    "guardrail_reason": result.guardrail_reason,
                    "response_text": result.response_text,
                },
                indent=2,
            )
        )
    return 0


def simulate_webhook(args: argparse.Namespace) -> int:
    create_all_tables()
    trading_day = date.fromisoformat(args.trading_day) if args.trading_day else now_utc().date()
    with SessionLocal() as session:
        user = _resolve_user(session, user_id=args.user_id, email=args.email)
        if not user.telegram_chat_id:
            raise ValueError("User must have telegram_chat_id to simulate a Telegram webhook.")
        update = _build_simulated_update(
            chat_id=user.telegram_chat_id,
            message_id=args.message_id,
            text=args.text,
            reply_to_message_id=args.reply_to_message_id,
        )
        result = process_telegram_webhook_update(
            session,
            update=update,
            trading_day=trading_day,
            telegram_client=TelegramClient(dry_run=args.dry_run),
        )
        session.commit()
        print(
            json.dumps(
                {
                    "user_id": str(result.user_id),
                    "daily_report_id": str(result.daily_report_id),
                    "inbound_telegram_message_id": str(result.inbound_telegram_message_id),
                    "user_chat_message_id": str(result.user_chat_message_id),
                    "assistant_chat_message_id": str(result.assistant_chat_message_id),
                    "outbound_telegram_message_id": str(result.outbound_telegram_message_id),
                    "telegram_message_id": result.telegram_message_id,
                    "dry_run": result.dry_run,
                    "guardrail_reason": result.guardrail_reason,
                    "response_text": result.response_text,
                },
                indent=2,
            )
        )
    return 0


def check_config(args: argparse.Namespace) -> int:
    settings = get_settings()
    token = settings.telegram_bot_token or ""
    print(
        json.dumps(
            {
                "database_url": settings.database_url,
                "app_timezone": settings.app_timezone,
                "telegram_dry_run": settings.telegram_dry_run,
                "telegram_bot_token_present": bool(token),
                "telegram_bot_token_length": len(token),
                "telegram_bot_token_source": "TELEGRAM_BOT_TOKEN env var"
                if os.getenv("TELEGRAM_BOT_TOKEN")
                else None,
            },
            indent=2,
        )
    )
    return 0


def set_password(args: argparse.Namespace) -> int:
    create_all_tables()
    password = args.password or getpass.getpass("Password: ")
    with SessionLocal() as session:
        user = _resolve_user(session, user_id=args.user_id, email=args.email)
        set_user_password(session, user=user, password=password)
        session.commit()
        print(
            json.dumps(
                {
                    "user_id": str(user.id),
                    "email": user.email,
                    "password_set": True,
                },
                indent=2,
            )
        )
    return 0


def _build_simulated_update(
    *,
    chat_id: str,
    message_id: int,
    text: str,
    reply_to_message_id: int | None,
) -> dict:
    message = {
        "message_id": message_id,
        "date": int(now_utc().timestamp()),
        "chat": {"id": chat_id},
        "text": text,
    }
    if reply_to_message_id is not None:
        message["reply_to_message"] = {"message_id": reply_to_message_id}
    return {
        "update_id": message_id,
        "message": message,
    }


def _resolve_user(session, *, user_id: str | None, email: str | None) -> User:
    if user_id:
        user = session.get(User, UUID(user_id))
    elif email:
        user = session.scalars(select(User).where(User.email == email)).one_or_none()
    else:
        raise ValueError("Either --user-id or --email is required.")

    if user is None:
        raise ValueError("User not found.")
    return user


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Premarket Operator admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate-report", help="Generate and store one report for one user")
    generate.add_argument("--email", default="local@example.com")
    generate.add_argument("--display-name", default="Local Test User")
    generate.add_argument("--telegram-chat-id", default=None)
    generate.add_argument("--trading-day", default=None)
    generate.add_argument("--rows-json", default=None)
    generate.add_argument("--limit", type=int, default=10)
    generate.set_defaults(func=generate_one_report)

    deliver = sub.add_parser("deliver-report", help="Send one persisted report to one user")
    deliver.add_argument("--user-id", default=None)
    deliver.add_argument("--email", default=None)
    deliver.add_argument("--trading-day", default=None)
    deliver.add_argument("--dry-run", action="store_true")
    deliver.set_defaults(func=deliver_one_report)

    deliver_all = sub.add_parser(
        "deliver-all-reports",
        help="Send persisted reports to all active eligible users",
    )
    deliver_all.add_argument("--trading-day", default=None)
    deliver_all.add_argument("--dry-run", action="store_true")
    deliver_all.set_defaults(func=deliver_all_reports)

    simulate = sub.add_parser(
        "simulate-reply",
        help="Persist and route a simulated inbound Telegram text reply",
    )
    simulate.add_argument("--user-id", default=None)
    simulate.add_argument("--email", default=None)
    simulate.add_argument("--trading-day", default=None)
    simulate.add_argument("--text", required=True)
    simulate.add_argument("--message-id", type=int, default=900001)
    simulate.add_argument("--reply-to-message-id", type=int, default=None)
    simulate.set_defaults(func=simulate_inbound_reply)

    simulate_answer = sub.add_parser(
        "simulate-answer",
        help="Route a simulated inbound reply and persist a report-aware assistant reply",
    )
    simulate_answer.add_argument("--user-id", default=None)
    simulate_answer.add_argument("--email", default=None)
    simulate_answer.add_argument("--trading-day", default=None)
    simulate_answer.add_argument("--text", required=True)
    simulate_answer.add_argument("--message-id", type=int, default=910001)
    simulate_answer.add_argument("--reply-to-message-id", type=int, default=None)
    simulate_answer.set_defaults(func=simulate_answer_reply)

    webhook = sub.add_parser(
        "simulate-webhook",
        help="Run the full Telegram webhook loop with a simulated inbound update",
    )
    webhook.add_argument("--user-id", default=None)
    webhook.add_argument("--email", default=None)
    webhook.add_argument("--trading-day", default=None)
    webhook.add_argument("--text", required=True)
    webhook.add_argument("--message-id", type=int, default=920001)
    webhook.add_argument("--reply-to-message-id", type=int, default=None)
    webhook.add_argument("--dry-run", action="store_true")
    webhook.set_defaults(func=simulate_webhook)

    config = sub.add_parser("check-config", help="Show runtime config without printing secrets")
    config.set_defaults(func=check_config)

    password = sub.add_parser("set-password", help="Set a browser login password for one user")
    password.add_argument("--user-id", default=None)
    password.add_argument("--email", default=None)
    password.add_argument("--password", default=None)
    password.set_defaults(func=set_password)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
