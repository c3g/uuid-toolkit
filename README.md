# UUID Toolkit (UUIDinator)

Web application for validating and generating research identifiers, with CILogon/COManage-backed authentication.

## Overview

The UUID Toolkit lets researchers and collaborators upload a spreadsheet of identifiers (CSV, XLSX, or JSON), validate them against a chosen identifier format, generate new identifiers where they're missing, and check the results against a persistent PostgreSQL registry so that a value used months ago is caught as a conflict today. It supports several identifier conventions out of the box, including CPHI, PCGL, RFC4122 UUIDs, and a configurable CUSTOM format, and is built so that a new convention can be added without touching the core pipeline.

## Architecture

The application is a layered pipeline: React collects a request, FastAPI receives it, a strategy registry selects the identifier format's rules, a multi-pass pipeline coordinates validation or generation, and PostgreSQL supplies persistent conflict knowledge.

```
 USER
  |
  v
+------------------+
| React Frontend    |
+--------+---------+
         | HTTP
         v
+------------------+
| FastAPI Routes    |
+--------+---------+
         v
+------------------+
| Core Pipeline     |
+--------+---------+
         v
+------------------+
| Strategy Registry |
+--------+---------+
         |
   +-----+-----+-------+
   |     |     |       |
   v     v     v       v
 UUID  CPHI  PCGL   CUSTOM
         |
         v
+------------------+
| DB Comparison     |
+--------+---------+
         v
+------------------+
| PostgreSQL         |
+------------------+
```

For production-style deployment, the React build is compiled once (`npm run build`) and served directly by FastAPI from the same container image, so there is a single disposable application container in front of a persistent PostgreSQL instance.

## Authentication & Authorization

### CILogon (OIDC) + COManage

Authentication and authorization are deliberately kept separate:

- **Authentication** ("who is this person?") is handled by [CILogon](https://www.cilogon.org/), an OIDC identity broker that federates institutional and Google logins. Integration uses [Authlib](https://authlib.org/) (`authlib.integrations.starlette_client.OAuth`), which performs real OIDC discovery and validates the ID token's signature, issuer, and audience.
- **Authorization** ("what can they do here?") is answered entirely by **COManage group membership**, released as a `groups` claim on the ID token. The application never makes its own authorization decision from anything else.

**Access model — gate before content:** no page or API route is reachable without a valid session. CILogon's registered redirect URI is the application's own root path (`/`), so the root route triple-purposes as normal page serving, the OIDC callback, and the redirect-to-CILogon step. `/api/health` and `/api/ready` stay ungated so the container healthcheck keeps working.

**Roles:** two roles exist, `admin` and `member`, resolved from COManage group strings shaped as `CO:COU:<this app's COU name>:<role>`:

```
CO:COU:c3g tech-dev uuid-toolkit:admins    -> admin
CO:COU:c3g tech-dev uuid-toolkit:members:* -> member
```

Being a member of the wider collaboration alone (`CO:members:*`) grants nothing — only membership in this application's own COU counts, so admission stays admin-controlled at the COManage level.

**The local `users` table is a mirror, not a gate.** It is kept in sync on every login (a row is created or its role corrected to match COManage's answer), and it's what the read-only User Management page displays, but it never independently grants access. A person with no recognized COManage group role is rejected with a 403 even if a stale row for them still exists locally.

**Session handling:** the session cookie stores only an opaque user ID, never a role — role is re-derived from the database (itself synced from COManage) on every request, so nothing the browser sends is ever trusted for an authorization decision.

**Configuration** — environment variables (see `.env.example`):

```bash
OIDC_ISSUER=https://cilogon.org
OIDC_CLIENT_ID=replace-with-cilogon-client-id
OIDC_CLIENT_SECRET=replace-with-cilogon-client-secret
OIDC_REDIRECT_URI=https://your-dashboard-domain.com/
SESSION_SECRET=replace-with-a-long-random-secret
SESSION_COOKIE_SECURE=true
AUTH_REQUIRED=true
```

`OIDC_REDIRECT_URI` must exactly match what is registered with CILogon for this client, including the trailing slash. `AUTH_REQUIRED=false` disables the gate entirely and must never be set outside local `npm run dev` frontend iteration.

## Code Structure

**Frontend (React + Vite)**

- `frontend-vite/src/`
  - `App.jsx` — route definitions, admin-only route gating
  - `main.jsx` — application bootstrap (`AuthProvider`, `BrowserRouter`)
  - `pages/ToolkitPage.jsx` — the main validate/generate workflow page
  - `pages/DatabaseManagementPage.jsx` — admin project/identifier management
  - `pages/UserManagementPage.jsx` — read-only enrolled-user list
  - `components/` — `ConfigPanel`, `UploadPanel`, `ResultPanel`, `ResultsTable`, `SummaryCards`, `DownloadActions`, `Sidebar`, `Topbar`, and supporting modals
  - `context/AuthContext.jsx`, `useAuth.js` — signed-in identity and role
  - `services/` — `apiClient.js`, `identifiersApi.js`, `projectsApi.js`, `usersApi.js`
  - `layouts/DashboardLayout.jsx` — shared page chrome

**Backend (FastAPI)**

- `backend/app/`
  - `main.py` — app entry point, CORS/session middleware, router registration, the login gate
  - `core/` — `pipeline.py` (validation/generation orchestration), `parser.py`, `normalizer.py`, `validation_result.py`, `pipeline_response.py`, `oidc.py`, `comanage_groups.py`, `auth_dependencies.py`
  - `strategies/` — `base.py` (the `StrategyInterface` contract), `registry.py` (strategy factory), `uuid_standard.py`, `cphi.py`, `pcgl.py`, `pcgl_modifiers.py`, `custom.py`
  - `api/` — `validate.py`, `generate.py`, `projects.py`, `identifier_database.py`, `database_management.py`, `auth.py`, `users.py`, `utils.py`
- `backend/db/` — `database.py`, `models.py` (`Project`, `IdentifierRegistry`, `User`), `project_repository.py`, `identifier_repository.py`, `comparison.py`, `database_management.py`, `schema_management.py`, `user_repository.py`
- `backend/scripts/` — `create_tables.py`, `reset_tables.py`

**Container / CI**

- `Containerfile` — multi-stage build: Node/Vite compiles the frontend, then a Python runtime image serves both the built assets and the FastAPI backend
- `compose.yml` — local Podman Compose stack: PostgreSQL, a one-shot `db-init` table-creation step, and the app
- `.github/workflows/` — automated tests and image publish to GHCR on merge to `main`

## Features

**1. Identifier strategies**
- CPHI: `<PROJECT_CODE>-<6-digit ID>` (e.g. `NRGI-123456`)
- PCGL: base format identical to CPHI, plus variant modifiers (`NRGI-123456_EXP_4829`) with patient (`SPE`) and sample (`EXP`, `RG`, `ANA`, `LIB`, `WRK`) modifier sets
- UUID: RFC4122 UUIDv4
- CUSTOM: user-configurable prefix/connector/suffix format

**2. Validation and generation, multi-pass**
- Structural validation, then in-file duplicate detection, then database comparison
- Fill-missing generation with collision avoidance against the upload, the database, and other values generated in the same run (bounded retries)
- Derived generation (PCGL-style): one confirmed base identifier produces several variant identifiers in a single pass, regenerated together on collision

**3. PostgreSQL-backed identifier registry**
- Project Tags define comparison scope; a match in the selected scope is a hard conflict, a match elsewhere under the same strategy is a soft warning
- An `Unassigned` system tag catches identifiers saved without a chosen project
- No database migration is needed to add a new strategy — `strategy_name` is a plain string column

**4. Results and downloads**
- Download all rows, only the incorrect rows (for a fix-and-reupload loop), or only the clean rows
- Save clean identifiers directly to the registry

**5. Admin-only database management**
- Create/delete Project Tags, delete identifiers by row, value, project, or strategy, with a separate, more destructive "clear all data" action

## Deployment

### Prerequisites

- Podman (or Docker)
- A CILogon OIDC client registered for this application, with COManage group release enabled for its COU
- PostgreSQL (bundled in `compose.yml` for local/production-style testing)

### Environment configuration

Copy `.env.example` and fill in real values. At minimum:

```bash
DATABASE_URL=postgresql+psycopg://username:password@hostname:5432/database_name
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
OIDC_ISSUER=https://cilogon.org
OIDC_CLIENT_ID=replace-with-cilogon-client-id
OIDC_CLIENT_SECRET=replace-with-cilogon-client-secret
OIDC_REDIRECT_URI=https://your-dashboard-domain.com/
SESSION_SECRET=replace-with-a-long-random-secret
SESSION_COOKIE_SECURE=true
AUTH_REQUIRED=true
```

### Container deployment (Podman Compose)

```bash
git clone https://github.com/c3g/uuid-toolkit.git
cd uuid-toolkit
podman compose -f compose.yml up -d
podman compose -f compose.yml ps -a
```

The stack brings up PostgreSQL, runs a one-shot table-creation step, then starts the application container on port 8000.

On Windows, Podman runs inside a Linux VM, so the app may need to be reached through the current VM IP rather than `localhost`:

```bash
podman machine ssh "ip -4 -o addr show eth0"
```

### Local development (separate dev servers)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn main:app --app-dir app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend-vite
npm install
npm run dev
```

The FastAPI dev server runs on port 8000, Vite on port 5173. Set `AUTH_REQUIRED=false` for local `npm run dev` frontend iteration only — CILogon's registered redirect URI doesn't apply there, and this must never be set outside local development.

### Initialize the database

```bash
cd backend
python -m scripts.create_tables
```

## Database Schema

**Core tables:**
- `projects` — Project Tags, unique on `(name, strategy_name)`
- `identifier_registry` — stored identifiers, unique on `(project_id, identifier_value)`, cascading delete from `projects`
- `users` — the local mirror of who currently has access, synced from COManage on every login (`email`, `cilogon_sub`, `role`, `last_login_at`)

No database enum or check constraint restricts `strategy_name` — adding a new identifier strategy requires no migration.

## Data Flow

**Validation:**
1. File uploaded with a chosen strategy and configuration
2. Parsed and normalized into a common record shape
3. Structural validation, then in-file duplicate detection
4. Compared against the PostgreSQL registry (hard conflicts / soft warnings)
5. Final summary and clean records returned to the frontend

**Generation:**
1. Existing identifiers are validated and classified; missing rows are identified
2. A blocked-identifier set is built from valid uploaded values plus database-reserved values
3. Candidates are generated for missing rows and checked against that set and each other, with bounded retries on collision
4. Final database comparison, then results returned

**Save:**
1. Clean identifiers from a validate/generate run are POSTed to the registry
2. Already-saved identifiers are skipped rather than erroring
3. A project/strategy mismatch is rejected (a PCGL identifier cannot be saved into a CPHI project)

## Troubleshooting

**Authentication issues:**
- Confirm `OIDC_REDIRECT_URI` matches exactly what's registered with CILogon, including the trailing slash
- A 403 "authenticated but not enrolled" means the person's COManage `groups` claim doesn't include this app's COU — check their group membership in COManage, not the local `users` table
- If the `groups` claim is missing entirely (not just empty) for every login, that's a CILogon attribute-release configuration issue for this specific client, not an application bug

**Database issues:**
- Ensure `DATABASE_URL` points at a reachable PostgreSQL instance
- Run `python -m scripts.create_tables` to create missing tables (safe to re-run; it does not touch existing tables)
- `python -m scripts.reset_tables --confirm-reset` drops and recreates everything — development only, never point it at production

**Local Podman networking (Windows):**
- `curl http://127.0.0.1:8000/api/health` failing to connect usually means the request needs to go to the Podman VM's IP instead of `127.0.0.1` — check it with `podman machine ssh "ip -4 -o addr show eth0"`

## Contact

johnny.wenglin@gmail.com
