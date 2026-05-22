from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass

from premarket_operator.core.config import get_settings


class TelegramClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramSendResult:
    chat_id: str
    message_id: int
    text: str
    dry_run: bool
    raw_response: dict


class TelegramClient:
    def __init__(self, *, bot_token: str | None = None, dry_run: bool = False) -> None:
        self.bot_token = bot_token or get_settings().telegram_bot_token
        self.dry_run = dry_run

    def send_message(self, *, chat_id: str, text: str) -> TelegramSendResult:
        if not chat_id:
            raise TelegramClientError("Telegram chat_id is required.")
        if not text:
            raise TelegramClientError("Telegram message text is required.")

        if self.dry_run:
            message_id = -time.time_ns()
            return TelegramSendResult(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                dry_run=True,
                raw_response={
                    "ok": True,
                    "dry_run": True,
                    "result": {"message_id": message_id, "chat": {"id": chat_id}},
                },
            )

        if not self.bot_token:
            raise TelegramClientError("TELEGRAM_BOT_TOKEN is required unless dry_run=True.")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise TelegramClientError(
                f"Telegram send failed: HTTP {exc.code} {exc.reason}: {error_body}"
            ) from exc
        except OSError as exc:
            raise TelegramClientError(f"Telegram send failed: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TelegramClientError(f"Invalid Telegram response: {raw}") from exc

        if not payload.get("ok"):
            raise TelegramClientError(f"Telegram send failed: {payload}")

        result = payload.get("result")
        if not isinstance(result, dict) or "message_id" not in result:
            raise TelegramClientError(f"Telegram response missing result.message_id: {payload}")

        return TelegramSendResult(
            chat_id=chat_id,
            message_id=int(result["message_id"]),
            text=text,
            dry_run=False,
            raw_response=payload,
        )
