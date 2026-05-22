from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

GuardrailDecision = Literal["allowed", "blocked"]

AUTOTRADING_PATTERNS = (
    r"\bplace (an? )?order\b",
    r"\bexecute\b",
    r"\bauto[- ]?trade\b",
    r"\bbuy\b.*\bnow\b",
    r"\bsell\b.*\bnow\b",
    r"\benter\b.*\btrade\b",
    r"\bexit\b.*\btrade\b",
    r"\bposition size\b",
    r"\bhow many shares\b",
)

CONTEXT_TERMS = {
    "report",
    "watchlist",
    "level",
    "levels",
    "support",
    "resistance",
    "flip",
    "gamma",
    "gex",
    "wall",
    "put",
    "call",
    "regime",
    "risk",
    "setup",
    "candidate",
    "candidates",
    "matter",
    "important",
    "focus",
    "zone",
    "premarket",
}

TICKER_STOPWORDS = {
    "A",
    "AN",
    "AND",
    "ANY",
    "ARE",
    "AS",
    "AT",
    "BEST",
    "CAN",
    "DO",
    "FOR",
    "HOW",
    "I",
    "IN",
    "IS",
    "IT",
    "LONG",
    "ME",
    "MY",
    "NOW",
    "OF",
    "ON",
    "OR",
    "SEE",
    "TERM",
    "THE",
    "THAT",
    "THIS",
    "TO",
    "WHAT",
    "WITH",
}


@dataclass(frozen=True)
class GuardrailResult:
    decision: GuardrailDecision
    reason: str | None = None
    response_text: str | None = None


def evaluate_question_scope(*, question: str, report_context: dict) -> GuardrailResult:
    normalized = question.strip().lower()
    if not normalized:
        return _blocked("empty_question", "I need a specific question about today's report.")

    if _matches_any(normalized, AUTOTRADING_PATTERNS):
        return _blocked(
            "autotrading_or_order_request",
            "I can discuss the report context, levels, and risk areas, but I cannot place orders, "
            "give execution instructions, or tell you what to buy or sell.",
        )

    watchlist = {ticker.upper() for ticker in report_context.get("watchlist", [])}
    if not watchlist:
        return _blocked(
            "missing_report_context",
            "I do not have a usable report context for this reply.",
        )

    mentioned_tickers = {
        token
        for token in re.findall(r"\b[A-Z]{1,5}\b", question.upper())
        if token not in TICKER_STOPWORDS
    }
    unknown_tickers = mentioned_tickers - watchlist - {"GEX", "ETF", "USD", "NY"}
    if mentioned_tickers and mentioned_tickers.isdisjoint(watchlist):
        return _blocked(
            "ticker_outside_report",
            "That ticker is not in today's report context. Reply with a question about the report watchlist "
            "or one of its listed levels.",
        )
    if unknown_tickers and not (mentioned_tickers & watchlist):
        return _blocked(
            "ticker_outside_report",
            "That ticker is not in today's report context. I can only answer from today's report.",
        )

    if mentioned_tickers & watchlist:
        return GuardrailResult(decision="allowed")

    words = set(re.findall(r"[a-z]+", normalized))
    if words & CONTEXT_TERMS:
        return GuardrailResult(decision="allowed")

    return _blocked(
        "unrelated_or_too_broad",
        "I can only answer questions grounded in today's premarket report, watchlist, levels, and event context.",
    )


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def _blocked(reason: str, response_text: str) -> GuardrailResult:
    return GuardrailResult(decision="blocked", reason=reason, response_text=response_text)
