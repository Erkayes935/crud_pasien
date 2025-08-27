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
- Add unit tests for CRUD operations and auth helpers.
- Add CI workflow (GitHub Actions) that runs linters and basic tests.


## Contact / authors
Repo owner: Erkayes935

If you'd like, I can also:
- Add Pydantic request models and update routes to use them
- Add JWKS caching and tests for token verification
- Add a small PowerShell helper to initialize the DB locally

Tell me which you'd like next and I will implement it.
