# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```powershell
# --- Setup (SQLite only) ---
$env:DATABASE_URL="sqlite:///./saas.db"; alembic upgrade head
$env:DATABASE_URL="sqlite:///./saas.db"; python seed/seed.py

# --- Run dev server ---
$env:DATABASE_URL="sqlite:///./saas.db"; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# http://localhost:8000  —  admin/admin123

# --- Tests (no DB required) ---
pytest tests/ -v

# --- New migration after model changes ---
$env:DATABASE_URL="sqlite:///./saas.db"; alembic revision --autogenerate -m "description"
$env:DATABASE_URL="sqlite:///./saas.db"; alembic upgrade head
```

## Known issues

- **bcrypt**: requires `bcrypt==4.0.1` — newer versions break with `passlib==1.7.4` on Python 3.13.
- **Zombie port**: if port 8000 is stuck and can't be killed, use `--port 8001`.
- **Windows commands**: always use PowerShell syntax (`$env:VAR="val"; command`), never bash-style `VAR=val command`.

## Architecture

**Stack**: FastAPI + Jinja2 (server-rendered) + HTMX 2.0.4 + SQLAlchemy 2.x + Alembic + SQLite + Babel (ISO currencies)

**Design philosophy**: Minimal, ultra-lightweight. Loads once/month, queried 3x/month by 2 users max. SQLite is perfect for this scale — zero server overhead, instant startup, zero cost.

The app replaces an Excel report (`saas_monthly_revenue.xlsx`) for SaaS billing. It ingests CSV files per bank client, converts amounts to USD via FX rates, applies marginal tiered billing, and displays monthly dashboards with HTMX-powered interactivity + Chart.js.

**Key design rules:**
- Business logic lives exclusively in `app/services/` — never in routers or templates
- `billing_service.py` is pure Python (no ORM/HTTP) — keep it that way for testability
- FX rates fetched from openexchangerates.org via `OpenExchangeRatesProvider` (key in `.env`)
- Once an exchange rate is stored it is **never overwritten automatically** — historical imports stay immutable
- A reimport for the same (bank, year, month) replaces all previous data for that period
- In FastAPI routers, literal routes (`/new`, `/export`) **must be declared before** parameterized routes (`/{id}`) to avoid 422 errors

**Data flow**: CSV upload → `importer.import_file()` → parse rows → fetch/store FX rate → aggregate into `monthly_metrics` → calculate billing → upsert

## Services

| File | Responsibility |
|------|---------------|
| `app/services/auth.py` | JWT cookie, bcrypt, `get_current_user`, `require_admin` |
| `app/services/billing_service.py` | Marginal tiered pricing + minimum fee (pure Python) |
| `app/services/fx_service.py` | `FXProvider` Protocol + `OpenExchangeRatesProvider` + `FrankfurterProvider` fallback |
| `app/services/importer.py` | CSV parser, FX fetch, billing calc, monthly_metrics upsert |
| `app/services/reporting.py` | DB queries for dashboard and bank detail |
| `app/services/currencies.py` | ISO 4217 list via Babel — used in bank form |

## Critical billing logic

Marginal (progressive) tiers — NOT flat rate per band:
- ≤ 1,000,001 txs → $0.0100/tx
- ≤ 5,000,001 txs → $0.0070/tx on the excess above 1M
- ≤ 20,000,001 txs → $0.0039/tx on the excess above 5M
- ≤ 100,000,001 txs → $0.0020/tx on the excess above 20M
- Minimum monthly fee: **USD 750** → `total_to_bill = max(calculated, 750)`

Tests in `tests/test_billing.py` verify against real Excel data.

## Models

All in `app/models/`. Key constraints:
- `monthly_metrics`: `UNIQUE(bank_id, year, month)` — upsert on reimport
- `exchange_rates`: `UNIQUE(currency, year, month, strategy)`
- `contracts`: active contract = `effective_from <= period_date ORDER BY effective_from DESC LIMIT 1`

## Auth

JWT in httponly cookie `access_token`. Roles: `admin` (full access) | `viewer` (read-only).
Use `Depends(get_current_user)` for any authenticated route, `Depends(require_admin)` for admin-only.

## Seed data

`seed/seed.py` loads 70 real periods from the Excel:
- Zanaco (ZMW): 35 months, Apr 2023 → Feb 2026
- CBE (ETB): 9 months, Jul 2022 → Mar 2023
- Dashen Bank (ETB): 26 months, Jan 2024 → Feb 2026

## UI

All templates are in English. Key pages:
- `/` — Dashboard: latest period per bank
- `/banks/{id}` — Bank detail: stat cards, two bar charts, pivot table (grouped by year, expand/collapse)
- `/exchange-rates` — Currency chips, line chart, "Fill missing" sync button
- `/imports` — CSV upload form + history
- `/contracts` — Pricing tier management
