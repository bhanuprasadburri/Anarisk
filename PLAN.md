# Nimbus Ninjas — Digital Threat Intelligence & Investigation Platform

## Architecture Plan (v1)

Rebuild of the existing `Anarisk` project into the premium 12-page Nimbus Ninjas product.
Stack is preserved: **FastAPI + PostgreSQL + SQLAlchemy + Alembic** backend, **React + Vite +
TypeScript + Tailwind CSS + Recharts + React Flow** frontend. No second framework is introduced.

## Environment (local dev)

- PostgreSQL 18 (portable) at `C:\Users\bhanu\Desktop\AnaRisk\pg`, data dir `C:\Users\bhanu\Desktop\AnaRisk\pgdata`,
  user `postgres` (trust auth), databases: `nimbus`, `nimbus_test`, port 5432.
- Backend venv: `Anarisk/backend/.venv` (Python 3.11). Run: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`
- Frontend: `npm run dev` on port 3000 (proxies `/api` → :8000). API base: `http://localhost:8000/api/v1`.

## Routes

| Route | Page |
|---|---|
| `/login`, `/forgot-password`, `/reset-password` | Auth (split-screen) |
| `/dashboard` | Overview Dashboard |
| `/assets` | Digital Assets |
| `/entities/:id` | Entity Details |
| `/threat-intelligence` | Threat Intelligence / Detection Results |
| `/risk-graph` | Risk Graph |
| `/cases`, `/cases/:id` | Investigation Cases / Case Workspace |
| `/mobile-apps` | Mobile App Monitoring |
| `/evidence` | Evidence Center |
| `/reports` | Reports & Analytics |
| `/settings` (tabs: profile, workspace, team, brands, integrations, monitoring, notifications, security) | Settings & Integrations |
| `*` | 404 |

## Design system (light, premium)

- Background `#F5F8FF`, surfaces `#FFFFFF`, text `#10264F`, secondary text `#64748B`
- Primary `#4778F5`, violet `#8B5CF6`, cyan `#20C5D7`, success `#10B981`, warning `#F59E0B`, danger `#F04464`, borders `#DCE6F5`
- Inter font, 8–14px radii, soft shadows (`shadow-card`), subtle blue-violet gradients used sparingly
- Shared shell: persistent white sidebar (active item = light blue tint + blue icon), top bar with
  global search, notifications popover, profile menu; content header per page with title, subtitle, actions.

## Backend additions

New API modules under `app/api/v1`:

- `auth` extras: `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password`, `PATCH /auth/me` (+ per-user notification preferences)
- `notifications`: list / unread count / mark read
- `integrations`: provider catalog + connect / disconnect / test / sync, secrets encrypted (Fernet derived from SECRET_KEY)
- `monitoring`: mobile-app monitoring target CRUD + per-target sync (honest sample-connector data)
- `reports`: DB-aggregated overview + CSV export
- `detections` extras: `GET /detections` (flattened assessments w/ filters, date range, sort, pagination), `POST /detections/{id}/re-analyze`
- `evidence` extras: delete, download, link/unlink case+entity, verify (SHA-256 recheck), CSV export
- `cases` extras: `PATCH /cases/{id}`, `DELETE /cases/{id}` (admin)
- `entities` extras: `DELETE /entities/{id}` (admin)

New models: `Notification`, `IntegrationConfig`, `MonitoringTarget`, `PasswordResetToken`,
`users.preferences` (JSONB). One new Alembic migration; seed script massively expanded
(~40 entities, ~50 relationships, assessments spread over 30 days, 12+ cases, 20+ evidence records
with real files+hashes, notifications, monitoring targets, integrations in honest `not_configured` state).

## Security

- bcrypt passwords (existing), JWT bearer (existing), server-side RBAC via `core/permissions.py`
- Secrets encrypted at rest; no secrets in frontend; upload validation + SHA-256 integrity;
  rate limiting on auth + analyze; audit logging on all mutations; SSRF-guarded outbound fetch (off by default)

## Honesty rules

- Detection = rule-based heuristic engine (documented as such in UI)
- Sample data clearly labeled `synthetic` provenance everywhere
- Integrations never show fake "Connected"; unavailable providers show honest setup states

## Testing

- Backend: pytest (existing suite + new endpoint tests) — must stay green
- Frontend: `tsc && vite build` must pass; browser-based E2E verification of all 12 pages and
  every interactive control (console/network clean)
