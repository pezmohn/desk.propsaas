# Project

Build a new paid product for US daytraders: a report-aware trading support service delivered primarily through Telegram.

Users receive a daily premarket report and can directly reply to it. The agent should answer in the same market context using that day's report, watchlist, levels, and event context.

## Product Positioning

We are not building a signal spam service, a general finance chatbot, or an autotrading product.

We are building:
- daily premarket clarity
- prioritized watchlists
- key levels and event context
- direct contextual follow-up via chat
- a focused trading support experience for solo daytraders

Working framing:
`An AI-powered trading desk for solo daytraders: report first, then direct chat in the same market context.`

## Scope

The product must support:
- multi-user report delivery
- Telegram as the first user channel
- per-user daily report context
- reply-to-report chat
- internal usage and cost tracking
- basic plan / tier logic
- strict tenant isolation

## MVP

The MVP must do the following:
1. manage multiple users
2. generate a daily premarket report per user
3. send that report automatically via Telegram
4. store the report as the user's daily context
5. allow the user to reply directly to the report
6. answer based on report context, not as a generic chatbot
7. track usage internally
8. apply simple plan / tier / limit rules

## Non-Goals

For MVP 1, do not build:
- autotrading
- order execution
- open-ended all-purpose market chat
- long-horizon unlimited memory
- a complex web app as the primary experience
- full billing automation
- advanced premium alert systems unless they directly unblock MVP validation

## Architecture Direction

Use a shared engine with isolated user context.

Do not create one permanently running agent per customer unless later evidence proves it is needed.

Preferred pattern:
- central orchestrator
- isolated per-user report context
- isolated per-user session data
- isolated per-user usage tracking

Short version:
`shared engine, isolated user context`

## Codex-First vs Classical Build

### Codex-first

Use Codex-first for:
- report-aware chat logic
- prompt design
- guardrails
- context assembly
- response patterns
- fast iteration on real user questions

### Classical product engineering

Build classically:
- user / plan layer
- database schema
- report pipeline
- Telegram plumbing
- scheduler / jobs
- usage ledger
- admin / ops basics

Rule:
`Classical code builds the rails. Codex builds the intelligence on the rails.`

## Reuse Policy

We may selectively reuse technical pieces from prior work, including:
- Telegram delivery infrastructure
- scheduling / cron logic
- report-generation components
- watchlist / level / GEX-related logic
- VPS / PM2 / logging / healthcheck operating knowledge

We should not inherit by default:
- old PropSaaS messaging
- old business framing
- Guardian-specific product assumptions
- irrelevant legacy modules

Rule:
`Reuse infrastructure, not legacy positioning baggage.`

## Working Principles

1. Build the smallest useful version first.
2. Reuse before rebuild.
3. Outcome beats architecture vanity.
4. Work in tight feedback loops.
5. Scope discipline is mandatory.
6. Manual early steps are acceptable.
7. User questions are product data.
8. Separate new product direction from old product baggage.
9. Keep pricing simple externally and track usage rigorously internally.
10. Reliability matters because trust matters.

Core principle:
`Ship the smallest useful version, learn from real user behavior, and only then expand.`

## Recommended Build Order

1. user / plan model
2. multi-user report generation
3. Telegram delivery
4. daily report context storage
5. reply-to-report chat
6. usage / limits / fair use
7. admin / ops / audit hardening
8. later: premium layers such as intraday alerts or review workflows

## Decision Filter

When making build decisions, prefer:
- faster validation over theoretical completeness
- focused user value over broad capability
- product clarity over technical cleverness
- real usage feedback over internal speculation

If a feature does not directly improve the report + context chat experience or help validate willingness to pay, deprioritize it.
