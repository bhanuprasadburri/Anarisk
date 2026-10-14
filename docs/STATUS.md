# Nimbus Ninjas — Project Status & Verification

_Last updated: 2026-10-14. Everything marked ✅ below was verified by running the listed
command or live API check, not by inspection alone._

## 1. Infrastructure & database

| Item | Status | Evidence |
|---|---|---|
| PostgreSQL (portable, local) for tests | ✅ | `backend/.env` `TEST_DATABASE_URL` → local `nimbus_test` |
| Supabase PostgreSQL (dev database) | ✅ | `DATABASE_URL` → Supabase (PostgreSQL 17.11, SSL required) |
| Migrations 0001 + 0002 (24 tables) | ✅ | `alembic upgrade head` applied; notifications, integrations, monitoring targets, password-reset tokens, case↔evidence links included |
| Seed data | ✅ | `python -m scripts.seed` → 1 org, 6 users, 3 brands, 40 entities, 100 assessments, 60 relationships, 14 cases, 24 evidence, 88 notifications, 6 monitoring targets (synthetic, labeled as such) |

## 2. Backend API

| Item | Status | Evidence |
|---|---|---|
| Endpoint surface | ✅ | 97 endpoints / 16 tags generated from live `openapi.json` → [docs/API.md](API.md) |
| Test suite | ✅ | `pytest -q` exits 0 (auth, RBAC, detection, graph, cases, evidence, integrations, monitoring, reports) |
| Live smoke test | ✅ | login → dashboard stats (40 entities / 19 high-risk / 12 open cases), detections, notifications (57), integrations (7 providers), monitoring (6), reports overview (31-day trend), evidence (24), cases (14), graph (40 nodes / 60 edges) |
| CSV export | ✅ | `GET /reports/export/csv?report=entities` → HTTP 200 `text/csv` with real rows |
| Honest integration states | ✅ | All 7 providers report `not_configured` until real credentials are supplied; no fake "connected" status |
| Detection labeling | ✅ | Scores labeled heuristic / rule-based; `data_notes` returned by reports |

## 3. Frontend

| Item | Status | Evidence |
|---|---|---|
| Design system (tokens, UI kit) | ✅ | `src/index.css`, `tailwind.config.js`, `src/components/ui/*`; `npx tsc --noEmit` exit 0 |
| API client services (no mocks) | ✅ | All `src/services/*` are pure API clients; `mocks/` removed |
| Auth (login, registration, forgot/reset password, protected routes) | ✅ | `src/pages/LoginPage.tsx`, `ForgotPasswordPage.tsx`, `ResetPasswordPage.tsx`, `hooks/useAuth.tsx` |
| App shell (sidebar, global search, notifications, profile menu) | ✅ | `src/components/layout/AppShell.tsx`, `NotificationsPopover.tsx` |
| 12 product pages | ⏳ | Being implemented; finalized in section 5 |

## 4. Honesty rules enforced

- Synthetic/seed data is labeled (provenance badges: `manual` vs `synthetic`).
- Risk scores are described as explainable heuristics requiring analyst review.
- Integrations never display "Connected" unless a live check passed.
- Publisher identity for mobile apps is never claimed as verified.
- No mock login, no fake data layer, no dead controls (each control wired to a real endpoint).

## 5. Page implementation checklist

_Filled in as each interface is completed and verified:_

- [ ] Login / Register / Password recovery
- [ ] Overview Dashboard
- [ ] Digital Assets
- [ ] Entity Details
- [ ] Threat Intelligence
- [ ] Risk Graph
- [ ] Investigation Cases (list)
- [ ] Case workspace (detail)
- [ ] Mobile App Monitoring
- [ ] Evidence Center
- [ ] Reports & Analytics
- [ ] Settings & Integrations

## 6. Known limitations (deliberate, honest)

1. **Connectors are stubs by design.** X/Twitter, Instagram, Google Play, App Store, web
   scraping, DNS/WHOIS and URL scan providers accept configuration and return honest status,
   but only local/synthetic collection runs without real third-party API credentials.
2. **Detection is rule-based** (weighted brand similarity, impersonation, URL risk, behavior).
   It is unvalidated against labeled datasets — treat outputs as leads, not verdicts.
3. **Password reset emails are not delivered**; in development the API returns a
   `dev_reset_token` so the flow can be exercised end to end.
4. **PDF export** generates a print-ready HTML document (open it and use the browser's
   "Save as PDF"); CSV export is a true server-side CSV download.
5. **Seed data is synthetic** and intentionally regenerated; do not use it for real cases.
6. **Single-region dev deployment** — the Supabase dev database is one instance; no HA/DR
   configuration is in scope for this demo.
