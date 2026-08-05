# Production deployment (Python 3.10)

Python 3.10 adalah versi runtime standar untuk development dan production.
Production Ubuntu 22.04 dan environment lokal harus memakai major/minor version
yang sama agar wheel biner pandas, NumPy, SciPy, dan scikit-learn konsisten.

## Local development on Windows

Install Python 3.10 64-bit, lalu buat virtual environment baru dari executable
3.10. Jangan memakai kembali virtual environment yang dibuat oleh Python 3.14.

```powershell
C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Nilai `python --version` harus menunjukkan `Python 3.10.x`. Dokumentasi API
development tersedia di `http://127.0.0.1:8000/docs`.

Jika `.venv` lama menggunakan versi Python lain, simpan sebagai backup sebelum
membuat ulang environment:

```powershell
deactivate
Rename-Item .venv .venv-python-old-backup
```

### Troubleshooting pandas DLL on Windows

Pesan berikut menunjukkan masalah runtime/dependensi, bukan kesalahan FastAPI:

```text
ImportError: DLL load failed ... An Application Control policy has blocked this file.
```

Periksa versi aktif:

```powershell
python --version
python -m pip show pandas numpy scikit-learn
```

Untuk konfigurasi proyek saat ini, instalasi dari `requirements.txt` pada Python
3.10 menghasilkan lini versi yang didukung: pandas `2.2.x`, NumPy `1.26-2.0`,
dan scikit-learn `1.5.x`. Jika environment berisi pandas `3.x`, NumPy di atas
`2.0`, atau Python `3.14`, buat ulang `.venv`; jangan memperbaiki environment
tersebut dengan menyalin DLL secara manual.

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
URL and a durable writable `STORAGE_DIR` (outside a release directory). CORS
is expected to be handled by Nginx/reverse proxy in front of FastAPI.

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
