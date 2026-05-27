# Project Status

Last updated: 2026-05-27

This is the current operating status of `desk-propsaas` as a live MVP, plus the short project-management list for what is still needed.

## Current State

### What is already working

- VPS deployment is live behind `desk.propsaas.app`
- `desk-propsaas` PM2 process is online
- Telegram webhook ingress is live
- Report-aware reply flow is live
- Snapshot-based report generation is implemented
- Daily scheduler tick is implemented
- Delivery repair/admin ops commands are implemented
- User-to-Telegram linking and user inspection flows exist
- Targeted hardening and scheduler tests were added during the latest round

### What has already been verified live

- Manual report generation works against the live runtime environment
- Manual Telegram delivery works
- Telegram reply-to-report flow works end-to-end
- Scheduler wrapper and cron wiring are in place on the VPS
- Scheduler instrumentation was added to make live-window diagnosis explicit

## Where We Are Actually Blocked

The main remaining gap is not core product logic. The main gap is a clean, observed, real production daily run in the actual New York delivery window.

On 2026-05-26, the stack was technically ready, but there was still no proof of a successful production scheduler send:

- `0` reports
- `0` sends
- no `scheduler_state.json`

Most likely causes narrowed so far:

- the narrow production window (`09:15-09:20 America/New_York`) was missed
- or the productive tick did not complete cleanly inside that window

Outside the report window, the scheduler behaves normally and logs expected `outside_report_window` skips.

## Priority List

### P0: Prove the first real live daily run

- Observe the scheduler during the real NY window
- Confirm same-day snapshots exist before the window
- Confirm `scheduler_state.json` is written
- Confirm report generation for the current trading day
- Confirm Telegram delivery for the intended linked user
- Record the result and blocker precisely if the run fails

Success criteria:

- productive scheduler tick is observed
- `generated_count > 0`
- `delivered_count > 0`
- no hidden skip due to snapshot availability, user eligibility, dedupe, or delivery mapping state

### P1: Tighten runbook-level operations

- keep `docs/live_day_runbook.md` as the canonical live-day procedure
- make sure the pre-window checks are run every trading day until the first stable production cycle is routine
- keep scheduler instrumentation in place until multiple real runs succeed

### P2: Clean repo state and checkpoint the hardening work

- review the current uncommitted scheduler/report/Telegram changes
- split them into sane commits
- push the implementation history instead of leaving the repo far ahead of `origin/main`

Right now the repo worktree contains substantial local implementation progress that is not yet reflected in the public commit history.

### P3: Auth boundary cleanup

After the live daily-run proof is done, the next recommended hardening focus is auth boundary cleanup rather than more delivery tweaks.

## Recommended Next Action

Run and monitor the live-day check during the next real New York send window, then classify the result into exactly one of these:

- success: scheduler generated and sent the report
- data blocker: same-day snapshots missing
- scheduler blocker: productive tick never actually executed in-window
- generation blocker: productive tick started but report generation failed
- delivery blocker: report exists but Telegram send failed
- state blocker: dedupe or prior state prevented the intended send

That result should drive the next engineering step. Until then, the product is close, but not yet operationally proven on the one path that matters most.

## Related Docs

- [Live Day Runbook](live_day_runbook.md)
- [Frontend Scope](frontend_scope.md)
