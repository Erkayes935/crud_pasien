# CRUD Pasien (FastAPI + SQLAlchemy)

A small patient management web app using FastAPI (server-side rendered with
Jinja2), SQLAlchemy ORM and Auth0 for authentication.

This README was updated to reflect recent refactors: configuration is
environment-driven (dotenv support), inline docstrings were added to backend
modules, and a small developer helper script was removed to keep the package
clean.

## Quick facts
- Python: 3.10+
- Web framework: FastAPI
- DB: PostgreSQL via SQLAlchemy (sync)
- Auth: Auth0 (JWT from Auth0 stored as HttpOnly cookie)
- Templates: Jinja2 (files in `frontend/templates`)


## Repository layout
- `backend/` — application code
  - `main.py` — FastAPI app & routes
  - `models.py` — SQLAlchemy models (Patient, User)
  - `crud.py` — typed DB helpers
  - `database.py` — engine and `SessionLocal` (reads `DATABASE_URL`)
  - `auth.py` — Auth0/JWT helpers and authorization decorator
  - `config.py` — reads required Auth0 env vars and fails fast if missing
- `frontend/templates/` — Jinja2 HTML templates


## Setup (PowerShell)

1) Create and activate a venv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Configure environment

- Copy `.env.example` to `.env` and fill in values for `DATABASE_URL` and
  Auth0 (`AUTH0_DOMAIN`, `CLIENT_ID`, `CLIENT_SECRET`, `REDIRECT_URI`,
  `AUDIENCE`, `ALGORITHMS`). `backend/config.py` validates these at import
  time and the app will not start if any are missing.

Example .env (local dev):

```
DATABASE_URL=postgresql://postgres:root@localhost:5432/patients
AUTH0_DOMAIN=dev-yourdomain.auth0.com
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
REDIRECT_URI=http://localhost:8000/callback
AUDIENCE=your_audience
ALGORITHMS=RS256
```

4) Run the app (development)

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/welcome to start.


## Code reference (summary)

This project contains short module- and function-level docstrings inside the
`backend/` modules. Quick summary:

- `backend/main.py` — routes and view rendering
  - `/login` `/callback` `/logout` — Auth0 flows
  - `/` — patient list (supports `filter_tanggal` query)
  - `/add`, `/edit/{id}`, `/delete/{id}` — CRUD (requires `doctor` role)
  - `/export` — returns `patients.xlsx`
  - `/import` — accepts JSON array upload

- `backend/models.py` — ORM models
  - `Patient(id, nama, tanggal_lahir, tanggal_kunjungan, diagnosis, tindakan, dokter)`
  - `User(id, auth0_sub, email, role)`

- `backend/crud.py` — typed helpers with docstrings
  - `get_patients(db) -> List[Patient]`
  - `create_patient(db, data) -> Patient`
  - `update_patient(db, patient_id, data) -> Optional[Patient]`
  - `delete_patient(db, patient_id) -> bool`

- `backend/database.py` — creates SQLAlchemy engine and `SessionLocal`; reads `DATABASE_URL` from env
- `backend/auth.py` — `verify_jwt`, `get_current_user`, and `require_role`

### Auth / Security (recent changes)

- JWKS caching and async verification: `auth.py` now includes a cached JWKS
  client (`_JWKSCache`) and `verify_jwt_secure` which performs async token
  verification against Auth0. This reduces network calls and improves
  reliability.
- Two auth styles supported:
  - Token-based: endpoints can accept JWT via `id_token` HttpOnly cookie or
    `Authorization: Bearer ...` header. Use `get_token_from_request` and
    `get_current_user_secure` for async verification.
  - Session-based: the app contains session helpers (`current_user_session`,
    `require_roles_session`) for apps that maintain a server-side session.
- CSRF helpers: `issue_csrf_token` and `require_csrf_dep` provide a simple
  server-side CSRF token flow for form POSTs when using session-based auth.

### Migrations / Alembic

- The `alembic/` directory is present and `alembic/env.py` uses
  `DATABASE_URL` from the environment when running migrations. To run
  migrations, ensure `DATABASE_URL` is set and use `alembic` CLI normally.



## Important notes & troubleshooting

- `backend/config.py` intentionally fails fast when required Auth0 env vars are
  missing — this avoids running the app in a broken state.
- The app uses `Base.metadata.create_all(...)` at startup (in
  `backend/main.py`) — the DB user must have privileges to create tables.
- The `import` endpoint expects JSON (`application/json`). Browser upload
  content-types may vary; if import fails, inspect the upload content-type.
- `auth.py` fetches Auth0 JWKS to verify tokens; network errors will fail
  authentication. Consider caching JWKS in production.


## Suggested improvements

- Add input validation with Pydantic models for posted forms / import JSON.
- Cache JWKS in `auth.py` to avoid network calls per request.
```markdown
# CRUD Pasien (FastAPI + SQLAlchemy)

Lightweight patient & claims management app built with FastAPI, SQLAlchemy
and server-side Jinja2 templates. The codebase has grown and been refactored
— this README reflects the current structure, dependencies and developer
workflow (run, migrations, env vars, and useful notes).

## Quick facts
- Python: 3.10+ (developed/tested on 3.11+)
- Web framework: FastAPI
- DB: PostgreSQL via SQLAlchemy (synchronous usage)
- Auth: Auth0 (JWT) and session helpers
- Templates: Jinja2 (templates under `frontend/templates`)


## Repository layout
- `backend/` — application code and routers
  - `main.py` — FastAPI app, middleware, and router registration
  - `models.py` — comprehensive SQLAlchemy models (Hospital, Patient, Visit, Claim, MedicalRecord, User, etc.)
  - `database.py` — SQLAlchemy engine / Base and DB helpers
  - `config.py` — environment-driven configuration (dotenv support)
  - `routers/` — many routers (dashboard, auth, patients, users, hospitals, medical_records, claims, visits, ...)
  - `static/` — static assets served at `/static`
  - `services/` — business logic and domain services (e.g. `dashboard_service.py`, `services/claim/*` contains claim-specific logic like `core.py`, `ai.py`, `simulation.py`, `helper.py`)
  - `utils/` — small helpers used across the app (e.g. `form_utils.py`, `templates.py`, `flash.py`, `auth_utils.py`, `dummy_data.py`)
  - `crud/` — thin DB helper modules that encapsulate simple CRUD queries for each model (e.g. `crud/patient.py`, `crud/claim.py`, `crud/medical_record.py`, `crud/user.py`, `crud/visit.py`, `crud/hospital.py`).
    - These helpers keep routers thin; more complex domain logic has been moved to `services/` (for example heavy claim-creation workflows live under `services/claim`).
- `alembic/` — DB migrations (alembic env uses `DATABASE_URL` from environment)
- `frontend/templates/` — Jinja2 templates used by the app


## Prerequisites
- PostgreSQL running and reachable from your development machine
- Python 3.10+


## Setup (PowerShell)

1) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Configure environment

- Copy `.env.example` (if present) to `.env` and fill required variables.
  The important environment variables used by `backend/config.py` are:

  - DATABASE_URL — e.g. postgresql://postgres:password@localhost:5432/dbname
  - AUTH0_DOMAIN
  - CLIENT_ID
  - CLIENT_SECRET
  - REDIRECT_URI
  - AUDIENCE
  - ALGORITHMS — comma-separated (e.g. RS256)
  - SESSION_SECRET — optional; auto-generated if not provided

  The module `backend/config.py` validates presence of Auth0-related
  variables at import time and will raise an error if any required variable
  is missing.


## Running the app (development)

Start the app with uvicorn (auto-reload):

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The app serves static files at `/static` and exposes routers registered in
`backend/main.py`. A common entrypoint for the UI is a dashboard route (see
`routers/dashboard_router`).


## Database migrations (Alembic)

This repository includes `alembic/` with migration scripts. Alembic reads
`DATABASE_URL` from the environment (see `alembic/env.py`). Typical workflow:

```powershell
setx DATABASE_URL "postgresql://postgres:password@localhost:5432/dbname"; # (PowerShell)
alembic upgrade head
```

Creating a new migration after changing models:

```powershell
alembic revision --autogenerate -m "describe changes"
alembic upgrade head
```

Note: `backend/main.py` also calls `Base.metadata.create_all(bind=engine)` at
startup, so the DB user needs privileges to create tables when running the
app directly. For controlled schema changes prefer Alembic migrations.


## Key features & routes

- Auth: Auth0 integration and session helpers are available in `backend/auth.py`.
  - Token-based and session-based flows are supported. JWT verification
    uses Auth0 JWKS; network failures will affect token verification.
- Models: see `backend/models.py` — main entities include Hospital, Patient,
  Visit, MedicalRecord, Claim and related submodels (diagnoses, procedures,
  evaluations, tariffs, logs, etc.).
- Routers: The app registers multiple routers in `backend/main.py` including
  dashboard, auth, patients, users, hospitals, medical_records, claims and visits.


## Dependencies

Primary dependencies are listed in `requirements.txt` and include:

- fastapi, uvicorn, SQLAlchemy
- psycopg2-binary (Postgres driver)
- python-jose / httpx / requests (auth & HTTP)
- Jinja2, openpyxl (export), python-dotenv, alembic


## Developer notes & troubleshooting

- Configuration fails fast: missing critical Auth0 env vars cause a
  RuntimeError at import time (see `backend/config.py`). This prevents
  running the app in a misconfigured state.
- JWKS fetching: `auth.py` fetches Auth0 JWKS for token verification —
  consider caching JWKS or using a resilient HTTP client in production.
- DB initialization: The app calls `Base.metadata.create_all(...)` on
  startup; if you prefer migrations-only, remove or guard that call.
- File uploads / import: endpoints like import expect JSON; ensure the
  client sends `application/json`.


## Suggested next improvements (low-risk)

- Add Pydantic request models for endpoints that accept JSON or form data.
- Add unit tests for CRUD and auth helpers (use pytest + a test DB).
- Add a GitHub Actions workflow to run linting and tests on PRs.
- Add CONTRIBUTING.md with development setup and a small PowerShell helper
  script to bootstrap local DB and env.


## Contact / authors
Repo owner: Erkayes935

If you'd like, I can also implement any of the suggested improvements above
— tell me which one you want and I'll prepare a follow-up change.

```
