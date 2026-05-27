# Frontend Scope

Last updated: 2026-05-27

This document defines the recommended first frontend scope for `desk-propsaas`.

The goal is not to build a broad trading platform yet. The goal is to create a thin trust-and-control layer on top of the live report engine.

## Product Principle

The first frontend should answer four user questions clearly:

- Am I connected correctly?
- Is my plan active?
- Did my report get generated and sent today?
- Can I review my recent reports and account status without asking support?

For admin and ops, it should answer:

- Which users are eligible today?
- Who is blocked and why?
- Was the report generated?
- Was Telegram delivery successful?

## V1 Scope

### 1. Auth

User-facing:

- email/password login
- logout
- forgot password / reset password

Admin-facing:

- same auth boundary as app users
- role-aware access for admin-only views

Why this belongs in V1:

- without auth, the frontend is not a real product surface
- users need a stable way to check their own state without Telegram-only support

### 2. User Home / Status Page

Core widgets:

- account status
- plan status
- Telegram link status
- today's report status
- last delivery timestamp
- current blocker state, if any

Examples of blocker states:

- Telegram not linked
- plan inactive
- no same-day snapshot available
- report generated but not sent
- delivery failed

Why this belongs in V1:

- this is the main trust screen
- it reduces support load immediately

### 3. Report History

User-facing list:

- recent reports
- trading day
- delivery status
- sent timestamp

User-facing detail page:

- full rendered report text
- structured context if needed for future UI improvements

Why this belongs in V1:

- users need proof and continuity
- the product starts with daily reports, so history is core, not optional

### 4. Telegram Connection Management

Minimum scope:

- show whether Telegram is linked
- show linked username/chat identity when available
- clear instructions for linking if missing

Optional if already easy from current backend:

- regenerate link token / connection flow

Why this belongs in V1:

- delivery trust depends on Telegram state
- this is one of the most common operational blockers

### 5. Admin / Ops Live-Day View

This should be simple and operational, not fancy.

Core admin data:

- eligible users for the day
- linked vs unlinked users
- report generation status by user
- delivery status by user
- blocker reason by user
- last scheduler result

Good enough V1 presentation:

- one table
- one summary row
- one detail drawer or page

Why this belongs in V1:

- it directly supports live operations
- it turns today's CLI-only visibility into a usable control surface

## Explicitly Out of Scope for V1

Do not frontload these:

- advanced charting dashboards
- browser-based chat client
- signal heatmaps
- watchlist editing studio
- billing complexity beyond basic plan status
- mobile app
- multi-broker portfolio views
- marketing-heavy landing work inside this repo
- polished trader workstation UX

Reason:

- none of these solve the current proof-of-operation problem
- they add product surface before the daily report loop is routine

## Recommended V1 Navigation

Keep it very small:

- Dashboard
- Reports
- Settings
- Admin

Settings should include:

- profile basics
- Telegram connection state
- plan/account status readout

Admin should be hidden for non-admin users.

## Backend/API Expectations for V1

The frontend should lean on stable, boring backend surfaces.

Needed API capabilities:

- auth session endpoints
- current user profile
- current plan/status
- Telegram link status
- today's report status
- report history list
- report detail
- admin live-day overview

If an endpoint is missing, prefer adding a narrow read-only endpoint instead of overloading existing chat or report generation paths.

## Delivery Order

Recommended build order:

1. auth shell
2. user dashboard/status page
3. report history + report detail
4. Telegram settings/status
5. admin live-day page

This order matches trust first, operations second, and polish later.

## Definition of Done for Frontend V1

Frontend V1 is done when:

- a normal user can log in
- a normal user can verify whether Telegram is linked
- a normal user can see whether today's report was generated and delivered
- a normal user can open prior reports
- an admin can see who is blocked today and why
- the UI reduces the need to use CLI commands for routine status checks

## Recommendation

Build the frontend soon, but keep it thin.

The right V1 is a control panel for trust, delivery visibility, and operational clarity. It is not yet a full trading product interface.

## Related Docs

- [Project Status](project_status.md)
- [Frontend V1 Tickets](frontend_v1_tickets.md)
