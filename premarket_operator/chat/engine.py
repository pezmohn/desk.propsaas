from __future__ import annotations

import re
from dataclasses import dataclass

from premarket_operator.chat.guardrails import evaluate_question_scope
from premarket_operator.chat.prompts import ReportAwarePrompt, build_report_aware_prompt

LOCAL_MODEL_NAME = "local-report-aware-v1"


@dataclass(frozen=True)
class ChatEngineResult:
    response_text: str
    prompt: ReportAwarePrompt
    model: str
    guardrail_reason: str | None
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def answer_from_report_context(*, report_context: dict, question: str) -> ChatEngineResult:
    prompt = build_report_aware_prompt(report_context=report_context, question=question)
    guardrail = evaluate_question_scope(question=question, report_context=report_context)
    if guardrail.decision == "blocked":
        response = guardrail.response_text or "I can only answer from today's report context."
        return _result(response=response, prompt=prompt, guardrail_reason=guardrail.reason)

    response = _grounded_response(report_context=report_context, question=question)
    return _result(response=response, prompt=prompt, guardrail_reason=None)


def _grounded_response(*, report_context: dict, question: str) -> str:
    candidate = _select_candidate(report_context=report_context, question=question)
    if candidate is None:
        tickers = ", ".join(report_context.get("watchlist", [])[:8])
        return (
            f"From today's report, the active watchlist is {tickers or 'not available'}. "
            "Ask about one listed ticker or a specific report level and I will keep the answer tied to that context."
        )

    ticker = candidate.get("ticker", "-")
    label = candidate.get("label", "-")
    score = candidate.get("shock_score", "-")
    regime = candidate.get("regime") or "-"
    supports = _format_levels(candidate.get("support_levels", []))
    resistances = _format_levels(candidate.get("resistance_levels", []))
    flip = _format_level(candidate.get("gamma_flip"))
    put_wall = _format_level(candidate.get("put_wall"))
    call_wall = _format_level(candidate.get("call_wall"))
    max_neg = _format_level(candidate.get("max_negative_gex_strike"))
    summary = candidate.get("summary") or ""

    return (
        f"For {ticker}, today's report flags {label} with score {score} and regime {regime}. "
        f"Key report levels: gamma flip {flip}, max negative GEX zone {max_neg}, "
        f"put wall {put_wall}, call wall {call_wall}, supports {supports}, resistances {resistances}. "
        f"Read this as context for planning and risk awareness, not as an instruction to enter or exit a trade. "
        f"{summary}"
    ).strip()


def _select_candidate(*, report_context: dict, question: str) -> dict | None:
    candidates = [
        candidate
        for section in report_context.get("sections", [])
        if section.get("kind") == "gex_shock"
        for candidate in section.get("candidates", [])
    ]
    if not candidates:
        return None

    mentioned = set(re.findall(r"\b[A-Z]{1,5}\b", question.upper()))
    for candidate in candidates:
        if candidate.get("ticker") in mentioned:
            return candidate
    return candidates[0]


def _result(*, response: str, prompt: ReportAwarePrompt, guardrail_reason: str | None) -> ChatEngineResult:
    input_tokens = _estimate_tokens(prompt.as_text())
    output_tokens = _estimate_tokens(response)
    return ChatEngineResult(
        response_text=response,
        prompt=prompt,
        model=LOCAL_MODEL_NAME,
        guardrail_reason=guardrail_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _format_level(value) -> str:
    return f"{float(value):.2f}" if value is not None else "-"


def _format_levels(values) -> str:
    return ", ".join(f"{float(value):.2f}" for value in values) if values else "-"
