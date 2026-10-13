# Anarisk

Anarisk is a digital risk protection platform for identifying impersonation, lookalike websites, fake social profiles, and suspicious mobile apps. The project combines a FastAPI backend, a PostgreSQL data model, graph-based relationship analysis, and a React frontend to help investigators assess risk, review evidence, and manage response cases.

This repository implements the Nimbus Ninjas architecture for digital risk protection and case review:

- Digital Surface Collection
- Detection Engine
- Risk Graph
- Explainable Case Review
- Response & Resolution

## What this project does

Anarisk helps teams monitor and investigate brand abuse by:

- ingesting digital entities such as domains, profiles, apps, and websites
- scoring them using explainable signal families
- linking suspicious entities through relationship graphs
- managing investigation cases with status workflows and ownership
- reviewing evidence and risk assessments in a dashboard
- enforcing role-based access and organization-level isolation

## Key features

- Risk scoring with explainable signals
  - brand logo matching
  - impersonation detection
  - URL/domain risk analysis
  - behavioral and coordination analysis
- Graph-based investigation of related entities and suspicious clusters
- Case workflow with assignment, escalation, notes, and resolution tracking
- Evidence uploads and provenance-aware assessments
- Security controls including RBAC, tenancy scoping, SSRF protections, and upload validation
- Demo-ready synthetic dataset for local testing and walkthroughs

## Tech stack

Backend
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- NetworkX
- RapidFuzz
- Pillow + ImageHash

Frontend
- React
- Vite
- TypeScript
- Tailwind CSS
- Recharts
- React Flow / XYFlow

## Repository structure

```text
.
├── backend/              # FastAPI API, migrations, database models, services, tests
├── frontend/             # React + Vite dashboard application
├── README.md             # Project overview
├── .gitignore
└── ...
```

## Quick start

### Option 1: Run with Docker (recommended)

From the backend directory:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

This starts the API and PostgreSQL services. The app is available at:

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Optional demo data:

```bash
cd backend
docker compose run --rm api python -m scripts.seed
```

### Option 2: Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Then run the frontend separately:

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server:
- http://localhost:5173

## Demo accounts

The seed script creates development accounts for testing:

| Email | Role | Password |
|---|---|---|
| admin@nimbus.example | administrator | `BOOTSTRAP_ADMIN_PASSWORD` (default `ChangeMe-Admin-123`) |
| investigator@nimbus.example | investigator | `Demo-Passw0rd!` |
| owner@nimbus.example | brand_owner | `Demo-Passw0rd!` |
| partner@nimbus.example | partner | `Demo-Passw0rd!` |

## Important project note

This project is designed as a demo and research platform. By default:

- no live monitoring connectors are configured
- data is synthetic or manually submitted unless a real connector is enabled
- risk scoring is heuristic and meant for human review
- case actions do not contact external parties automatically

## Backend API summary

The API exposes endpoints for:

- authentication and users
- brands and official references
- digital entities and evidence
- detection and scoring
- graph analysis
- workflow-based case management
- dashboard metrics and audits

## Verification and tests

Backend tests are available:

```bash
cd backend
pytest
```

The project includes automated tests covering authentication, RBAC, detection logic, graph analysis, case workflows, and migration safety.

## License

This project is currently provided as a source repository for development and demonstration purposes. Add a license file if you plan to publish or distribute it.

## Next steps

If you want to extend the platform, the natural next areas are:

- adding real data connectors for social and app marketplaces
- improving signal quality with labeled datasets
- adding richer frontend workflows and analytics
- integrating automated notification and response actions

