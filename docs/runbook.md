# Runbook — SaaS Monthly Revenue

## Correr localmente

### Pre-requisitos
- Docker Desktop instalado y corriendo
- Git (opcional)

### Pasos

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Levantar la base de datos y la app
docker compose up -d

# 3. Aplicar migraciones
docker compose exec app alembic upgrade head

# 4. Cargar datos de demo (bancos, contratos, cotizaciones, métricas históricas)
docker compose exec app python seed/seed.py

# 5. Abrir el navegador
# http://localhost:8000
```

### Credenciales demo
| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| admin | admin123 | admin |
| viewer | viewer123 | viewer |

---

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://saas:saas@localhost:5432/saas` |
| `SECRET_KEY` | Clave secreta para JWT | *debe cambiarse* |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración de sesión (min) | `480` |
| `DATA_FOLDER` | Carpeta de archivos a importar | `./data/imports` |
| `FX_STRATEGY` | Estrategia de tipo de cambio | `first_day` |

---

## Crear usuario admin manualmente

```bash
docker compose exec app python -c "
from app.database import SessionLocal
from app.models.user import User
from app.services.auth import hash_password
db = SessionLocal()
db.add(User(username='myadmin', email='me@example.com',
            password_hash=hash_password('mypassword'), role='admin'))
db.commit()
print('Usuario creado')
"
```

---

## Importar archivos

### Desde la UI
1. Loguearse como admin
2. Ir a **Importaciones**
3. Seleccionar banco y subir el archivo CSV/TXT

### Formato del archivo CSV
```
date,file_id,scheme,amount,count
2025-01-15,1001,VISA,168755,45
2025-01-16,1002,MASTERCARD,52074,16
```

Columnas mínimas requeridas:
- `date` — fecha de la transacción (formato `YYYY-MM-DD`, `DD/MM/YYYY`, o `MM/DD/YYYY`)
- `file_id` — identificador del batch/archivo
- `scheme` — esquema de tarjeta (VISA, MASTERCARD, AMEX)
- `amount` — monto en moneda original del banco
- `count` — cantidad de transacciones

Columnas adicionales (ej: `CotDay`, `Control Column`) son ignoradas.

---

## Aplicar migraciones

```bash
# Dentro de Docker
docker compose exec app alembic upgrade head

# Con venv local
DATABASE_URL=postgresql://saas:saas@localhost:5432/saas alembic upgrade head
```

---

## Correr tests

```bash
# Con venv local (sin DB necesaria para tests unitarios)
pip install -r requirements.txt
pytest tests/ -v

# Con Docker
docker compose exec app pytest tests/ -v
```

---

## Detener el sistema

```bash
docker compose down          # para pero conserva datos
docker compose down -v       # para y borra la BD
```
