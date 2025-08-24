
# Contract Workflow Management (SDVOSB-ready) — Streamlit + Postgres

A deploy-ready web app to manage government contract workflows for a SDVOSB team:
- Multi-user with authentication (Streamlit Authenticator if configured; demo fallback built-in).
- Contracts + Tasks + Reporting + Audit Log.
- Prevents duplicate work: visibility on assigned contracts and statuses.
- Persistent DB via Postgres (Supabase/Neon) or SQLite for local dev.

## Features
- **Contracts**: Create/edit, assign officers, track status, due dates, metadata (agency, NAICS, set-aside).
- **Tasks**: Per-contract tasks with statuses, due dates, assignees.
- **Officer View**: See only assigned contracts/tasks (role-aware UI).
- **Reports**: All active contracts, work completed, CSV export.
- **Audit Log**: Who did what and when.
- **Auth**: Uses Streamlit Authenticator if configured, else simple demo login selector to get started immediately.

## Quick Start (Local Dev with SQLite)
```bash
pip install -r requirements.txt
python -m app.init_db         # creates tables + seeds demo users
streamlit run app/app.py
```

## Production Deploy (Streamlit Cloud + Postgres)
1. Push this folder to GitHub.
2. Create a free Postgres DB (Supabase or Neon). Copy the connection string.
3. In Streamlit Cloud, set **Secrets**:
```toml
# .streamlit/secrets.toml (set in Streamlit Cloud UI)
DATA_GUI_DB_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME"

# Optional: enable real login (Streamlit Authenticator)
[credentials]
  usernames.admin = {email="admin@example.com", name="Admin", password="pbkdf2:..."}  # or 'password' plain to be hashed on first login
  usernames.officer = {email="officer@example.com", name="Officer One", password="pbkdf2:..."}

[cookie]
  name = "contract_workflow_auth"
  key = "REPLACE_WITH_RANDOM_STRING"
  expiry_days = 14

[preauthorized]
  emails = ["admin@example.com"]
```
4. Deploy the app; it will auto-run and connect to Postgres.

## Environment Variable
- `DATA_GUI_DB_URL` — SQLAlchemy URL. Defaults to `sqlite:///data.db` for local use.

## Roles
- **admin**: Full access, manage users, contracts, tasks, reports.
- **officer**: Sees/edits assigned contracts and tasks, updates statuses, logs work.
- **viewer**: Read-only access to contracts and reports.

## Notes
- Passwords via Streamlit Authenticator can be managed in secrets; app will hash plaintext on first login if needed.
- For uploads, you can extend `app/storage.py` to wire to S3/Supabase Storage.
