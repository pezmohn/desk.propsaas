# Frontend V1 Tickets

Last updated: 2026-05-27

This is the recommended first implementation sequence for the `desk-propsaas` frontend.

These tickets are intentionally scoped around stable product structure first, and operational nuance second.

## Ticket 1: App Shell and Auth

### Goal

Create the basic authenticated app surface.

### Scope

- app layout
- navigation
- protected routes
- login
- logout
- forgot password / reset password

### Explicitly not in scope

- advanced onboarding
- role management UI
- profile editing depth beyond what is needed to support login flows

### Done when

- unauthenticated users are redirected to login
- authenticated users can access the app shell
- auth flows work end-to-end against the intended backend contract
- the app has a stable page structure for later tickets

## Ticket 2: User Dashboard Skeleton

### Goal

Create the main trust screen for a normal user.

### Scope

- dashboard route
- layout and cards for:
  - plan status
  - Telegram link status
  - today's report status
  - last delivery timestamp
  - current blocker placeholder
- loading, empty, and error states

### Explicitly not in scope

- final blocker taxonomy
- polished delivery state wording
- complex visual analytics

### Done when

- a logged-in user lands on a meaningful dashboard
- the page structure clearly supports the real operational fields
- placeholder or read-only data states are handled cleanly

## Ticket 3: Report History and Report Detail

### Goal

Expose the core product artifact in the frontend.

### Scope

- reports list page
- report detail page
- recent reports table or cards
- delivery status and trading day display
- loading, empty, and error states

### Explicitly not in scope

- rich report composer
- annotations/workflow editing
- browser chat tied to a report

### Done when

- users can see prior reports
- users can open a report detail page
- the daily-report product value is visible in the UI without using CLI tools

## Ticket 4: Settings and Telegram Status

### Goal

Make the most important delivery dependency visible to the user.

### Scope

- settings route
- profile basics readout
- Telegram connected / not connected state
- clear guidance when Telegram is missing or incomplete
- basic account/plan status placement if it fits the page structure

### Explicitly not in scope

- full account management suite
- billing portal UX
- deep preference management

### Done when

- users can verify whether Telegram is linked
- missing-link state is obvious
- support does not need to answer simple “am I connected?” questions manually

## Ticket 5: Admin and Ops Live-Day View

### Goal

Turn today’s CLI-only operational visibility into a usable control page.

### Scope

- admin route
- read-only live-day table
- per-user columns for:
  - eligible
  - Telegram linked
  - report generated
  - report sent
  - blocker
- lightweight summary row or counters

### Explicitly not in scope

- admin write actions
- retry buttons
- workflow orchestration
- bulk operations

### Done when

- admin can understand today’s live delivery state without dropping to CLI
- blocked users are visible
- generated vs sent distinction is visible

## Build Order Recommendation

Build in this order:

1. Ticket 1
2. Ticket 2
3. Ticket 3
4. Ticket 4
5. Ticket 5

Recommended implementation strategy:

- start Tickets 1 to 3 immediately
- follow with Ticket 4
- build Ticket 5 once the read-only data contract is clear enough

## Why This Order

- Ticket 1 creates the real app boundary
- Ticket 2 creates the trust surface
- Ticket 3 exposes the product’s core value
- Ticket 4 reduces delivery confusion
- Ticket 5 gives admin operational visibility without overcommitting to unstable workflow details

## What Should Wait Until After Live Proof

These should not block the first frontend build, but they also should not be finalized too early:

- final delivery-state UX
- blocker taxonomy wording
- admin write actions
- retry flows
- automation-heavy ops workflows
- browser-based chat surfaces
- advanced analytics screens

## Recommendation

Start frontend work now, but do it in this order and keep V1 honest.

The first frontend should be a control and trust layer for the live report system, not a full trading workstation.
