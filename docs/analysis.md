# Análisis funcional — SaaS Monthly Revenue

## Resumen del problema

La empresa reporta resultados mensuales de un sistema SaaS de servicios en la nube a múltiples bancos clientes. El proceso actual vive en una planilla Excel (`saas_monthly_revenue.xlsx`) y se quiere migrar a una app web multiusuario que corra en AWS.

---

## Entidades detectadas

| Entidad | Descripción |
|---------|-------------|
| Banco / Cliente | Zanaco (ZMW), CBE (ETB), Dashen Bank (ETB), CBZ (USD) |
| Contrato | Versión de pricing vigente por banco |
| Tramo de pricing | Franjas de volumen con fee por transacción |
| Tipo de cambio | Cotización de referencia por moneda/período |
| Importación | Registro de archivo procesado |
| Fila de importación | Registro individual del CSV |
| Métrica mensual | Agregación consolidada por banco/período |
| Usuario | Acceso con rol admin o viewer |
| Log de auditoría | Trazabilidad de acciones |

---

## Reglas de negocio detectadas

### Datos y períodos
1. Los datos se procesan **a mes vencido**: los datos de Marzo se entregan en Abril
2. La información se **agrupa por año/mes** y se muestra el mes de referencia
3. Un archivo por banco cliente
4. Una reimportación para el mismo banco/período **reemplaza** los datos anteriores

### Formato de archivos de entrada
- CSV/TXT con columnas: `date, file_id, scheme, amount, count`
- Columnas adicionales (`CotDay`, `Control Column`) son ignoradas
- Esquemas conocidos: VISA, MASTERCARD, AMEX

### Conversión de moneda
- Cada banco tiene una moneda origen (ZMW, ETB, USD)
- Se convierte a USD usando el tipo de cambio de referencia
- **El tipo de cambio queda grabado permanentemente** al momento de importar
- No se recalculan retroactivamente los datos históricos si cambia la cotización
- Estrategia por defecto: cotización del primer día del mes
- Fuente de cotizaciones: frankfurter.app (gratuita, sin API key)
- Fallback: carga manual desde el panel de admin

### Facturación (CRÍTICA — marginal progresiva)
La lógica es **marginal / progresiva**, NO por tramo único:

| Hasta (inclusive) | Fee / Tx |
|-------------------|----------|
| 1.000.001 | USD 0.0100 |
| 5.000.001 | USD 0.0070 |
| 20.000.001 | USD 0.0039 |
| 100.000.001 | USD 0.0020 |

**Ejemplo correcto**: 2.000.000 txs:
- Primeras 1.000.001 @ $0.01 = $10.000,01
- Siguientes 999.999 @ $0.007 = $7.000,00
- **Total = $17.000,01** (NO $14.000 que daría flat @ $0.007)

**Mínimo mensual**: USD 750 por cliente. `total_to_bill = max(calculado, 750)`

---

## Supuestos tomados

1. **Reimport replace**: una reimportación del mismo período reemplaza todos los datos anteriores (import + import_rows + metric).
2. **FX inmutable**: una vez grabada la cotización en `exchange_rates`, no se modifica automáticamente para períodos ya importados.
3. **Contrato por banco**: se aplica el contrato con `effective_from` más reciente que sea ≤ al período de referencia.
4. **Formato CSV flexible**: las columnas se detectan por nombre (case-insensitive, trim). Se soportan variantes `fecha`/`date`.
5. **Un período por archivo**: si el CSV contiene filas de múltiples meses, se crean métricas separadas por cada (año, mes).
6. **Roles simples**: admin ve y modifica todo; viewer solo visualiza.
7. **Sin multi-tenant por banco**: todos los viewers ven todos los bancos. (Se puede agregar después si hace falta.)
8. **CBZ en USD**: como su moneda es USD, la cotización es 1:1 y no requiere conversión externa.

---

## Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| API frankfurter.app no disponible | Fallback manual desde admin en `/exchange-rates` |
| Formato CSV del banco cambia | Mapeo de columnas configurable en `bank.import_format` (JSON, para versiones futuras) |
| Volumen muy alto de filas | `import_rows` está indexado por `import_id`; agregar índice en `(bank_id, year, month)` si escala |
| Recálculo retroactivo accidental | El `fx_rate_id` en `monthly_metrics` es inmutable post-import |

---

## Decisiones de diseño

- **Stack monolítico**: FastAPI + Jinja2 + HTMX evita complejidad de SPA. Una sola app, un solo deploy.
- **JWT en cookie httponly**: más seguro que localStorage para un MVP.
- **Alembic**: migraciones explícitas y versionadas.
- **Protocol FXProvider**: el proveedor de cotizaciones está desacoplado detrás de una interfaz Python `Protocol`, fácil de cambiar.
- **Billing puro**: `billing_service.py` no tiene dependencias de ORM ni HTTP, solo lógica matemática → 100% testeable.
