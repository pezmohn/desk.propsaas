from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class TelegramUpdateParseError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramInboundMessage:
    update_id: int | None
    message_id: int
    chat_id: str
    text: str
    reply_to_message_id: int | None
    raw_update: dict[str, Any]


def parse_inbound_text_message(update: dict[str, Any]) -> TelegramInboundMessage:
    message = update.get("message")
    if not isinstance(message, dict):
        raise TelegramUpdateParseError("Telegram update does not contain a message.")

    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("id") is None:
        raise TelegramUpdateParseError("Telegram message does not contain chat.id.")

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        raise TelegramUpdateParseError("Telegram message does not contain text.")

    message_id = message.get("message_id")
    if not isinstance(message_id, int):
        raise TelegramUpdateParseError("Telegram message does not contain numeric message_id.")

    reply_to_message_id = None
    reply_to_message = message.get("reply_to_message")
    if isinstance(reply_to_message, dict):
        raw_reply_id = reply_to_message.get("message_id")
        if isinstance(raw_reply_id, int):
            reply_to_message_id = raw_reply_id

    update_id = update.get("update_id")
    if update_id is not None and not isinstance(update_id, int):
        update_id = None

    return TelegramInboundMessage(
        update_id=update_id,
        message_id=message_id,
        chat_id=str(chat["id"]),
        text=text.strip(),
        reply_to_message_id=reply_to_message_id,
        raw_update=update,
    )
