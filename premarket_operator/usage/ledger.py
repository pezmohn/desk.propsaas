from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from premarket_operator.db.models import UsageLedger
from premarket_operator.db.repositories import require_user_id


def record_usage(
    session: Session,
    *,
    user_id: UUID,
    feature: str,
    daily_report_id: UUID | None = None,
    chat_message_id: UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    estimated_cost_cents: int | None = None,
    limit_name: str | None = None,
    limit_allowed: bool | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> UsageLedger:
    require_user_id(user_id)
    entry = UsageLedger(
        user_id=user_id,
        daily_report_id=daily_report_id,
        chat_message_id=chat_message_id,
        feature=feature,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_cents=estimated_cost_cents,
        limit_name=limit_name,
        limit_allowed=limit_allowed,
        metadata_json=metadata_json,
    )
    session.add(entry)
    session.flush()
    return entry
