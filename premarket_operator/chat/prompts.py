from __future__ import annotations

from dataclasses import dataclass


SYSTEM_PROMPT = """You are a report-aware trading support assistant for solo US daytraders.
Use only the provided daily report context and basic market mechanics.
Do not act as a general finance chatbot.
Do not provide order execution, autotrading, position sizing, or personalized buy/sell instructions.
If the question is outside the report context, say that clearly and narrow back to the report."""


@dataclass(frozen=True)
class ReportAwarePrompt:
    system: str
    context: str
    question: str

    def as_text(self) -> str:
        return f"{self.system}\n\nREPORT CONTEXT:\n{self.context}\n\nUSER QUESTION:\n{self.question}"


def build_report_aware_prompt(*, report_context: dict, question: str) -> ReportAwarePrompt:
    return ReportAwarePrompt(
        system=SYSTEM_PROMPT,
        context=_context_summary(report_context),
        question=question.strip(),
    )


def _context_summary(report_context: dict) -> str:
    lines = [
        f"Report type: {report_context.get('report_type', '-')}",
        f"Trading day: {report_context.get('trading_day', '-')}",
        f"Watchlist: {', '.join(report_context.get('watchlist', [])) or '-'}",
    ]

    for section in report_context.get("sections", []):
        if section.get("kind") != "gex_shock":
            continue
        lines.append(f"Section: {section.get('title', 'GEX Shock')} ({section.get('candidate_count', 0)} candidates)")
        for candidate in section.get("candidates", [])[:10]:
            lines.extend(
                [
                    (
                        f"- {candidate.get('ticker')} rank {candidate.get('rank')} "
                        f"score {candidate.get('shock_score')} label {candidate.get('label')}"
                    ),
                    (
                        f"  spot {candidate.get('spot_price')} flip {candidate.get('gamma_flip')} "
                        f"put wall {candidate.get('put_wall')} call wall {candidate.get('call_wall')} "
                        f"regime {candidate.get('regime')}"
                    ),
                    (
                        f"  supports {candidate.get('support_levels', [])} "
                        f"resistances {candidate.get('resistance_levels', [])} "
                        f"summary {candidate.get('summary')}"
                    ),
                ]
            )

    boundaries = report_context.get("chat_boundaries", {})
    if boundaries:
        lines.append(f"Allowed: {boundaries.get('allowed', '-')}")
        lines.append(f"Disallowed: {boundaries.get('disallowed', '-')}")
    return "\n".join(lines)
