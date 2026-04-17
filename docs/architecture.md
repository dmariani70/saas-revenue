# Arquitectura — SaaS Monthly Revenue

## Stack elegido

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Backend | Python 3.12 + FastAPI | Tipado, async, liviano, excelente soporte para server-render |
| Templates | Jinja2 + HTMX | Sin SPA, sin build step, sin node_modules |
| Gráficos | Chart.js 4 (CDN) | Liviano, sin dependencias, bar charts listos |
| ORM | SQLAlchemy 2.x | Estándar Python, tipado con `Mapped[]` |
| Migraciones | Alembic | Versionado explícito |
| BD | PostgreSQL 16 | Robusto, gratis en RDS |
| Auth | JWT en cookie httponly + bcrypt | Seguro para MVP, sin estado en servidor |
| FX API | frankfurter.app | Gratuita, sin API key, confiable |
| Contenedor | Docker + Docker Compose | Portabilidad local → AWS |

---

## Estructura del proyecto

```
app/
├── main.py              # FastAPI app, monta routers
├── config.py            # Settings via pydantic-settings + .env
├── database.py          # Engine + SessionLocal + Base
├── models/              # SQLAlchemy ORM models
│   ├── user.py
│   ├── bank.py
│   ├── contract.py      # Contract + PricingTier
│   ├── exchange_rate.py
│   ├── import_record.py # Import + ImportRow
│   ├── monthly_metric.py
│   └── audit_log.py
├── services/            # Lógica de negocio (sin dependencia de HTTP)
│   ├── auth.py          # JWT, bcrypt, get_current_user
│   ├── billing_service.py  # Cálculo marginal puro
│   ├── fx_service.py    # FXProvider Protocol + FrankfurterProvider
│   ├── importer.py      # Parser CSV + orquestación
│   └── reporting.py     # Consultas de agregación
├── routers/             # FastAPI routers (HTTP layer)
│   ├── auth.py          # /login, /logout
│   ├── dashboard.py     # /
│   ├── banks.py         # /banks, /banks/{id}
│   ├── imports.py       # /imports, /imports/upload
│   ├── contracts.py     # /contracts
│   ├── exchange_rates.py # /exchange-rates
│   └── admin.py         # /admin/users
└── templates/           # Jinja2 HTML
    ├── base.html        # Layout con sidebar
    ├── login.html
    ├── dashboard.html
    ├── bank_detail.html # Chart.js embebido
    └── ...
```

---

## Modelo de datos

```
users ──────────── audit_logs
  │
banks ──┬────────── contracts ─── pricing_tiers
        │
        ├────────── imports ────── import_rows
        │
        └────────── monthly_metrics ── exchange_rates
```

### Invariantes críticos
- `monthly_metrics.fx_rate_id` apunta al `exchange_rates.id` usado al importar → inmutable post-import
- `monthly_metrics` tiene `UNIQUE(bank_id, year, month)` → upsert en reimport
- `exchange_rates` tiene `UNIQUE(currency, year, month, strategy)` → no duplica cotizaciones
- `contracts` se busca por `bank_id` + `effective_from <= período` → contrato histórico correcto

---

## Flujo de importación

```
Admin sube CSV
      │
      ▼
importer.import_file()
      │
      ├─ parse CSV → ImportRow objects
      ├─ fx_service.get_or_fetch_rate()  ← API frankfurter / DB / manual
      ├─ Agregar: Σtxs, Σamount_orig, amount_usd = amount_orig / rate
      ├─ billing_service.total_to_bill(txs, contract.tiers, min_fee)
      ├─ Upsert MonthlyMetric
      └─ AuditLog
```

---

## Estrategia FX

```python
class FXProvider(Protocol):
    def get_rate(self, currency, year, month) -> Optional[float]: ...

# Implementaciones:
FrankfurterProvider  # GET https://api.frankfurter.app/{date}?from=USD&to={currency}
ManualFallback       # retorna None → obliga a cargar desde admin
```

El sistema busca primero en la BD. Si no existe, llama al provider y graba el resultado. Una vez grabado, nunca se sobreescribe automáticamente.

---

## Cálculo de billing (marginal progresivo)

```python
def calculate_billing(total_txs: int, tiers: list[TierDef]) -> float:
    remaining = total_txs
    prev_bound = 0
    total = 0.0
    for tier in sorted(tiers, key=lambda t: t.upper_bound):
        band_size = tier.upper_bound - prev_bound
        applied = min(remaining, band_size)
        total += applied * tier.fee_per_tx
        remaining -= applied
        prev_bound = tier.upper_bound
        if remaining <= 0:
            break
    return total

total_to_bill = max(calculate_billing(txs, tiers), min_monthly_fee)
```

---

## Arquitectura AWS (producción)

```
Internet
    │
    ▼
[ALB]  (HTTPS 443)
    │
    ▼
[ECS Fargate]  (task: app container, 512 CPU / 1GB RAM)
    │
    ├──► [RDS PostgreSQL 16] (db.t3.micro)
    │
    ├──► [S3]  (archivos CSV importados, opcional)
    │
    └──► [CloudWatch Logs]

Secrets: AWS Secrets Manager → DATABASE_URL, SECRET_KEY
```

### Estimación de costo AWS (MVP)
| Servicio | Instancia | Costo aprox/mes |
|----------|-----------|-----------------|
| ECS Fargate | 0.25 vCPU / 512MB | ~$8 |
| RDS PostgreSQL | db.t3.micro | ~$15 |
| ALB | bajo tráfico | ~$16 |
| **Total** | | **~$40/mes** |

### Deploy básico
```bash
# Build y push a ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker build -t saas-revenue .
docker tag saas-revenue:latest $ECR_URI/saas-revenue:latest
docker push $ECR_URI/saas-revenue:latest

# Aplicar migraciones en RDS (desde tarea ECS one-off)
# O desde bastion host: DATABASE_URL=... alembic upgrade head
```
