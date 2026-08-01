# Production deployment (Python 3.10)

## Prepare the host

Use a clean Python 3.10 virtual environment. The bounded versions in
`requirements.txt` keep the application on a dependency set that supports
Python 3.10.

```bash
python3.10 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create the production `.env` from `.env.example`. Set a PostgreSQL database
URL, a durable writable `STORAGE_DIR` (outside a release directory), and exact
frontend origins in `ALLOWED_ORIGINS`. Do not use `*` as an allowed origin when
the browser sends credentials.

## Migrate before serving

Run migrations once per release, before starting application workers:

```bash
alembic upgrade head
```

`AUTO_CREATE_SCHEMA` is `false` by default. Keep it disabled in production:
migrations are the sole mechanism for changing database schema.

## Run

Use a process manager or container orchestrator to restart the process and a
reverse proxy/load balancer for TLS. Example process command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

Tune worker count to available CPU and memory; dataset parsing and ML training
are CPU- and memory-intensive. Configure the proxy body-size limit to match
`MAX_UPLOAD_SIZE_BYTES` (25 MiB by default).

## Dates and timestamps

The API emits timezone-aware UTC ISO-8601 timestamps using
`datetime.now(timezone.utc)`. Database columns are PostgreSQL
`TIMESTAMP WITH TIME ZONE`; PostgreSQL stores these values as instants, so the
database session's display timezone does not change their meaning.
