## CRUD Pasien (FastAPI + SQLAlchemy)

Simple patient CRUD web app using FastAPI for the backend and Jinja2 templates for the frontend.

Key features
- Patient create / read / update / delete from a PostgreSQL database
- Auth0-based login (id_token stored in cookie)
- Export to Excel and import from JSON

Stack
- Python 3.10+ (project used Python 3.13 in development)
- FastAPI
- Uvicorn
- SQLAlchemy (sync)
- PostgreSQL
- Jinja2 templates (in `frontend/templates`)
- Auth0 for authentication

Repository layout
- `backend/` - FastAPI app and data models
  - `main.py` - FastAPI app and routes
  - `models.py` - SQLAlchemy models
  - `crud.py` - DB helper functions
  - `database.py` - DB connection (edit DATABASE_URL as needed)
  - `auth.py` - Auth helper (Auth0 verification)
  - `config.py` - Auth0 config values (replace with your values or manage securely)
- `frontend/templates/` - Jinja2 HTML templates used by the app

Prerequisites
- PostgreSQL running and accessible. The project expects a database named `patients` by default.
- Python 3.10+ and pip

Quick setup (PowerShell)

1) Create a virtual environment and activate it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Configure the database

The app reads `DATABASE_URL` from the environment. Copy `.env.example` to `.env` and edit the `DATABASE_URL` line for local development. Example `.env` snippet:

```
DATABASE_URL=postgresql://postgres:root@localhost:5432/patients
```

Either create a database and user matching that URL, or change the connection string to use your Postgres credentials.

If you prefer to create the database manually, use psql (adjust to your installation):

```powershell
# CREATE DATABASE patients;
# CREATE USER postgres WITH PASSWORD 'root';
# -- or create a dedicated user and grant privileges
```

4) Configure Auth0

Copy `.env.example` to `.env` and fill the Auth0 values there. `backend/config.py`
will validate that the following variables are present at startup and will fail
fast with a helpful error if any are missing:

- AUTH0_DOMAIN
- CLIENT_ID
- CLIENT_SECRET
- REDIRECT_URI (e.g. http://localhost:8000/callback)
- AUDIENCE
- ALGORITHMS (e.g. `RS256`)

Example `.env` lines:

```
AUTH0_DOMAIN=dev-yourdomain.auth0.com
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
REDIRECT_URI=http://localhost:8000/callback
AUDIENCE=your_audience
ALGORITHMS=RS256
```

5) Run the app

```powershell
# from repository root
# start development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You can then open: http://localhost:8000/welcome to begin (or `/` for the patient list page once logged in).

Notes & troubleshooting
- The app uses SQLAlchemy's `Base.metadata.create_all(...)` (called in `backend/main.py`) so tables will be created automatically at startup if the DB user has the right privileges.
- If you see connection errors, double-check `DATABASE_URL` in `backend/database.py` and confirm Postgres is running and accessible from your machine.
- If login fails, verify the Auth0 values in `backend/config.py` and the redirect URI registered in your Auth0 application.
- Import endpoint expects a JSON file (application/json) with an array of patient objects.
- Export endpoint returns an Excel `.xlsx` file generated with openpyxl.

Suggested next steps
- Move secrets into environment variables and load them securely (for production). Replace hard-coded values in `backend/config.py`.
- Add a `requirements.txt` (already added) and consider using `pip-tools` or Poetry for dependency management.
- Add tests and CI for basic routes.

License
This repo has no license file. Add one if you plan to publish or share the code.

Contact / authors
Repo owner: Erkayes935

Environment file
- Copy `.env.example` to `.env` and fill your values for local development. The app uses `python-dotenv` (loaded in `backend/config.py`).

## Code reference (quick)

This project embeds short module docstrings in the `backend/` modules. Quick pointers:

- `backend/main.py` — HTTP routes and view rendering. Important routes:
  - `/login`, `/callback`, `/logout` — Auth0 flows
  - `/` — patient list (supports `filter_tanggal` query)
  - `/add`, `/edit/{id}`, `/delete/{id}` — CRUD operations (requires `doctor` role)
  - `/export` — returns patients.xlsx
  - `/import` — expects JSON array upload

- `backend/models.py` — ORM models:
  - `Patient(id, nama, tanggal_lahir, tanggal_kunjungan, diagnosis, tindakan, dokter)`
  - `User(id, auth0_sub, email, role)`

- `backend/crud.py` — typed helpers:
  - `get_patients(db) -> List[Patient]`
  - `create_patient(db, data) -> Patient`
  - `update_patient(db, patient_id, data) -> Optional[Patient]`
  - `delete_patient(db, patient_id) -> bool`

- `backend/database.py` — engine and `SessionLocal`. Reads `DATABASE_URL` from env.
- `backend/auth.py` — JWT verification helpers and `require_role` decorator. `get_current_user` returns the `User` ORM object for the logged-in token.

If you want more detailed inline docs for any specific function, tell me which ones and I'll expand their docstrings.
