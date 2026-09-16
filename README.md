# Data-to-Dashboard

An autonomous analyst that turns messy CSV or SQLite data into a cleaned dataset, an explainable baseline predictive model when appropriate, and a custom interactive React dashboard.

**Status: foundation implemented; full analyst application not yet implemented.** A local FastAPI service, executable contracts, React isolation lab, automated checks, and fail-closed runtime preflight are runnable. Uploads, analysis, and generated Python execution remain disabled.

Use [Getting started](docs/GETTING_STARTED.md) to run the foundation and [verification evidence](docs/evidence/2026-09-16-foundation.md) for tested behavior and blockers.

## Read first

1. [Project requirements](docs/PRD.md): scope, user stories, measurable acceptance criteria.
2. [Architecture](docs/ARCHITECTURE.md): services, boundaries, planned repository layout.
3. [Security and privacy](docs/SECURITY.md): execution isolation and release gates.
4. [Implementation roadmap](docs/ROADMAP.md): dependency-ordered backlog.
5. [Current project state](memory/STATE.md): completed work and exact next steps.

## Documentation index

| Document | Purpose |
| --- | --- |
| [UX specification](docs/UX.md) | Screens, interactions, accessibility, recovery |
| [Data and modeling](docs/DATA_AND_MODELING.md) | Ingestion, cleaning, evaluation, provenance |
| [Agent and generated UI](docs/AGENT_AND_UI.md) | Workflow, tool contracts, code generation |
| [API and persistence](docs/API_AND_DATA.md) | Endpoints, entities, events, artifacts |
| [Testing and acceptance](docs/TESTING.md) | Fixtures, security tests, release evidence |
| [Development process](docs/DEVELOPMENT.md) | Setup plan, coding workflow, definition of done |
| [Operations](docs/OPERATIONS.md) | Deployment, telemetry, retention, recovery |
| [Decisions](docs/DECISIONS.md) | Architecture decision records |
| [Risks and open questions](docs/RISKS.md) | Assumptions, risks, deferred choices |
| [References](docs/REFERENCES.md) | Primary technical sources |
| [Agent instructions](AGENTS.md) | Persistent implementation guidance |
| [Memory index](memory/README.md) | Session tracking protocol |

## Intended outcome

A user uploads data, reviews the detected schema, optionally chooses a prediction target, and starts an analysis. A bounded LangChain/LangGraph workflow writes and executes Pandas code, validates artifacts, evaluates a baseline, and generates a dashboard. The user can inspect transformations, filter charts, see model limitations, and download results. Invalid generated UI falls back to a validated dashboard specification.

The foundation uses React + TypeScript and FastAPI. LangChain/LangGraph, Pandas/scikit-learn, PostgreSQL, a durable queue, and S3-compatible storage remain planned. Foundation versions are locked; providers remain undecided. Public generated-code execution requires the documented security gates.
