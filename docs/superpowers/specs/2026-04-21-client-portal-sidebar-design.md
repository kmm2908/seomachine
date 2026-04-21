# SEO Machine — Client Portal: Sidebar & Navigation Design

**Date:** 2026-04-21
**Status:** Approved
**Build target:** SiteBuilder monorepo (`apps/seomachine-portal/`)

---

## Context

SEO Machine is a multi-client SEO content pipeline. The UI lives in the SiteBuilder monorepo (Astro + Cloudflare Pages), with SEO Machine exposing a thin FastAPI wrapper. This spec covers the **client portal** — the first UI surface to build.

An operator/admin dashboard (multi-client view, batch controls, config management) is a separate spec, deferred.

---

## Architecture Decision

**Two separate layouts — client portal first, operator dashboard later.**

The operator workflow (triggering batch runs, monitoring 5 clients, managing configs, viewing logs) is fundamentally different from the client workflow (checking scores, approving content, downloading deliverables). A shared sidebar would compromise both. Building the client portal first delivers the polished, product-facing surface that makes SEO Machine look like a commercial product.

---

## User Roles

| Role | Access | Scope |
|------|--------|-------|
| **Client** | Client portal | Own data only |
| **Operator** | Admin dashboard (separate, deferred) | All clients |

---

## Client Capabilities

Clients can:
- View their SEO audit scores and reports
- See their content queue and published posts
- Request new content (submit a brief or topic)
- Approve/review content before it publishes
- Download citation packs and other deliverables
- View competitor analysis and keyword research
- Check social/video repurposing status
- Manage their account and billing

---

## Sidebar Structure

7 top-level groups, each collapsible. Labels are outcome-focused (not tool-focused).

```
Home
  └── Overview              ← audit score, recent activity, alerts

My Content
  └── Queue                 ← upcoming topics + status icons
  └── Published Posts
  └── Request Content       ← submit brief or topic
  └── Review & Approve      ← badge count for pending items

SEO Performance
  └── Audit Report
  └── Google Business Profile
  └── Crawler Issues
  └── Schema Check

Citations
  └── Listing Status
  └── Download Pack
  └── Competitor Gaps

Research
  └── Competitor Analysis
  └── Keywords & Topics

Social & Video
  └── Repurposing Status
  └── Scheduled Posts

Account
  └── Settings
  └── Billing / Credits
  └── Support
```

---

## Design Principles

1. **5–7 top-level items max** — more than 7 signals grouping is needed, not a longer list
2. **80/20 rule** — most-used items (Overview, My Content, SEO Performance) go at the top
3. **F-pattern** — most critical item top-left; that's Home/Overview
4. **Icon + text labels** in expanded state; icon-only acceptable when collapsed (with tooltips)
5. **220–260px** standard sidebar width; collapsed icon-only state 64–72px
6. **Outcome-focused labels** — "My Content" not "Queue"; "SEO Performance" not "Audit"
7. **Badge counts** on Review & Approve for actionable pending items
8. **Sticky/fixed** sidebar — always visible regardless of scroll position
9. **Dark sidebar** to differentiate clearly from main content area

---

## Build Order

1. Sidebar shell component — collapsed/expanded states, icon + label pairs, active state
2. Home / Overview page — audit score widget, recent activity feed, alert strip
3. My Content section — queue list with status badges, review/approve flow
4. Route guard — client login, session, scope to own data only

---

## File Location in SiteBuilder

`apps/seomachine-portal/` within the SiteBuilder monorepo, consuming `packages/tokens/` for brand styling.

---

## Research Sources

- [Best UX Practices for Designing a Sidebar — UX Planet](https://uxplanet.org/best-ux-practices-for-designing-a-sidebar-9174ee0ecaa2)
- [Sidebar Design for Web Apps: UX Best Practices — Alf Design Group](https://www.alfdesigngroup.com/post/improve-your-sidebar-design-for-web-apps)
- [Designing a layout structure for SaaS products — Medium/Bootcamp](https://medium.com/design-bootcamp/designing-a-layout-structure-for-saas-products-best-practices-d370211fb0d1)
- [Smart SaaS Dashboard Design Guide — F1Studioz](https://f1studioz.com/blog/smart-saas-dashboard-design/)
