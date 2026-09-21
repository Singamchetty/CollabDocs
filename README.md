# CollabDocs

Backend API for CollabDocs — a platform where users can create workspaces, invite
collaborators, write and version documents, leave comments, and control access with
role-based permissions. Think of it as a simplified Notion or Google Docs, API-only.
Postman is the client; there is no frontend in this repository.

## Stack

- Python 3.14, Django 6.1, Django REST Framework
- PostgreSQL 16 (via Docker Compose)
- [uv](https://docs.astral.sh/uv/) for dependency management

## Project layout

Domain logic is split into one Django app per area, mirroring the model groups in the brief:

- `users` — `User`
- `workspaces` — `Workspace`, `WorkspaceMember`
- `documents` — `Document`, `DocumentVersion`
- `comments` — `Comment`
- `tags` — `Tag`
- `audit_log` — `AuditLog`

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/):
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Docker (any daemon works — Docker Desktop, Rancher Desktop, Colima, etc.) for Postgres via `docker compose`

## Setup

1. Copy the environment template and adjust if needed:

   macOS/Linux:

   ```bash
   cp .env.example .env
   ```

   Windows (PowerShell):

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start PostgreSQL:

   ```bash
   docker compose up -d
   ```

3. Create a virtual environment and install dependencies with `uv`:

   macOS/Linux:

   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

   Windows (PowerShell):

   ```powershell
   uv venv
   .venv\Scripts\Activate.ps1
   uv pip install -r requirements.txt
   ```

   Windows (cmd.exe):

   ```bat
   uv venv
   .venv\Scripts\activate.bat
   uv pip install -r requirements.txt
   ```

4. Apply migrations:

   ```bash
   python manage.py migrate
   ```

5. Run the server:

   ```bash
   python manage.py runserver
   ```

   Commands in steps 4–5 are the same on every OS once the virtual environment is activated.

The API is served at `http://localhost:8000/api/`. A Postman collection covering all
endpoints will be added to the repository root before submission.

You can also connect a database client (DBeaver, JDBC, `psql`, etc.) directly to
Postgres using the `POSTGRES_*` values from `.env` — host `localhost`, port `5432`.

## Running tests

```bash
python manage.py test
```

## Demo

_Link to the demo video will be added before final submission._
