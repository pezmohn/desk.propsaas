# Premarket Operator

MVP foundation for a paid report-aware trading support service delivered through Telegram.

The product boundary is strict: daily premarket report first, reply-to-report chat second. It is not a general trading chatbot, signal spam service, autotrading system, or order execution product.

## Week 1 Focus

- Multi-user database foundation
- Per-user daily reports with `body_text` and `context_json`
- Adapted GEX shock ranking as a report input
- Minimal plans and usage tables
- Telegram and chat plumbing in later steps

## Runtime

See [docs/runtime.md](docs/runtime.md) for the local Python runtime and dry-run webhook verification.
See [docs/live_test.md](docs/live_test.md) for the first one-user live Telegram test checklist.
See [docs/project_status.md](docs/project_status.md) for the current MVP status and next-priority checklist.
