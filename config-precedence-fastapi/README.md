# 12-Factor Configuration Precedence API

FastAPI endpoint: `GET /effective-config?set=key=value&set=...`

Precedence: defaults -> `config.<APP_ENV>.yaml` -> `.env` -> OS `APP_*` variables -> repeated `set` query parameters.

## Local run

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
$env:APP_DEBUG = "false"   # PowerShell; on bash use: export APP_DEBUG=false
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/effective-config`.

Test overrides:

`http://127.0.0.1:8000/effective-config?set=port=9000&set=debug=true`

The `NUM_WORKERS` key in `.env` is an alias for `workers`. `api_key` is always masked as `****`.

## Deploy on Render

This repository includes `render.yaml` for Render Blueprint deployment. It uses:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `APP_ENV=development` and OS-level `APP_DEBUG=false`

This exercise's `.env` includes only the assignment's sample/dummy key. Do not commit real secrets in a real application.
