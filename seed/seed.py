"""
Seed script con datos REALES extraídos de saas_monthly_revenue.xlsx.

Carga:
  - 2 usuarios (admin, viewer)
  - 4 bancos: Zanaco (ZMW), CBZ Bank (ZMW), Dashen Bank (ETB), CBE (ETB - inactivo)
  - Contrato estándar con pricing escalonado vigente
  - Cotizaciones FX reales del Excel (Exchange Rates sheet)
  - Métricas mensuales exactas (txs, ZMW/ETB, USD) del Excel

Usage:
    python seed/seed.py
    # o desde Docker:
    docker compose exec app python seed/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date
from app.database import SessionLocal
from app.models.user import User
from app.models.bank import Bank
from app.models.contract import Contract, PricingTier
from app.models.exchange_rate import ExchangeRate
from app.models.monthly_metric import MonthlyMetric
from app.services.auth import hash_password
from app.services.billing_service import calculate_billing, total_to_bill, TierDef

TIERS = [
    TierDef(upper_bound=1_000_001,   fee_per_tx=0.01),
    TierDef(upper_bound=5_000_001,   fee_per_tx=0.007),
    TierDef(upper_bound=20_000_001,  fee_per_tx=0.0039),
    TierDef(upper_bound=100_000_001, fee_per_tx=0.002),
]


def run():
    db = SessionLocal()
    try:
        _create_users(db)
        zanaco = _get_or_create_bank(db, "Zanaco", "ZANACO", "ZMW")
        cbe    = _get_or_create_bank(db, "Commercial Bank of Ethiopia", "CBE", "ETB")
        cbz    = _get_or_create_bank(db, "CBZ Bank", "CBZ", "ZMW")
        dashen = _get_or_create_bank(db, "Dashen Bank", "DASHEN", "ETB")

        # Mark CBE as inactive
        cbe.active = False
        db.add(cbe)

        for bank in [zanaco, cbz, dashen]:
            _ensure_contract(db, bank)

        _seed_fx_rates(db)
        db.flush()

        _seed_zanaco(db, zanaco)
        _seed_cbe(db, cbe)
        _seed_dashen(db, dashen)

        db.commit()
        print("Seed completado con datos reales del Excel.")
        print("  admin / admin123   (rol admin)")
        print("  viewer / viewer123  (rol viewer)")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def _create_users(db):
    if not db.query(User).filter_by(username="admin").first():
        db.add(User(username="admin", email="admin@example.com",
                    password_hash=hash_password("admin123"), role="admin"))
    if not db.query(User).filter_by(username="viewer").first():
        db.add(User(username="viewer", email="viewer@example.com",
                    password_hash=hash_password("viewer123"), role="viewer"))
    db.flush()


# ---------------------------------------------------------------------------
# Banks & contracts
# ---------------------------------------------------------------------------

def _get_or_create_bank(db, name, code, currency):
    bank = db.query(Bank).filter_by(code=code).first()
    if not bank:
        bank = Bank(name=name, code=code, currency=currency, import_format={})
        db.add(bank)
        db.flush()
    return bank


def _ensure_contract(db, bank):
    if db.query(Contract).filter_by(bank_id=bank.id).first():
        return
    c = Contract(bank_id=bank.id, version="v1",
                 effective_from=date(2022, 1, 1), min_monthly_fee=750.0)
    db.add(c)
    db.flush()
    for tier in TIERS:
        db.add(PricingTier(contract_id=c.id,
                           upper_bound=tier.upper_bound,
                           fee_per_tx=tier.fee_per_tx))
    db.flush()


# ---------------------------------------------------------------------------
# FX rates — from Exchange Rates sheet in saas_monthly_revenue.xlsx
# ---------------------------------------------------------------------------

def _seed_fx_rates(db):
    rates = [
        # --- ZMW (Zambian Kwacha) — rates used in CBZ/Zanaco sheet ---
        ("ZMW", 2023,  4, 21.15),
        ("ZMW", 2023,  5, 17.732),
        ("ZMW", 2023,  6, 19.4939),
        ("ZMW", 2023,  7, 17.557),
        ("ZMW", 2023,  8, 18.95),
        ("ZMW", 2023,  9, 20.1707),
        ("ZMW", 2023, 10, 20.9902),
        ("ZMW", 2023, 11, 22.04),
        ("ZMW", 2023, 12, 23.70),
        ("ZMW", 2024,  1, 25.667),
        ("ZMW", 2024,  2, 27.072),
        ("ZMW", 2024,  3, 23.4452),
        ("ZMW", 2024,  4, 24.867),
        ("ZMW", 2024,  5, 26.75),
        ("ZMW", 2024,  6, 25.75),
        ("ZMW", 2024,  7, 23.95),
        ("ZMW", 2024,  8, 25.95),
        ("ZMW", 2024,  9, 26.061),
        ("ZMW", 2024, 10, 26.4),
        ("ZMW", 2024, 11, 26.7),
        ("ZMW", 2024, 12, 26.85),
        ("ZMW", 2025,  1, 27.825),
        ("ZMW", 2025,  2, 27.8546),
        ("ZMW", 2025,  3, 28.0119),
        ("ZMW", 2025,  4, 27.8546),
        ("ZMW", 2025,  5, 28.5148),
        ("ZMW", 2025,  6, 28.047),
        ("ZMW", 2025,  7, 27.806),
        ("ZMW", 2025,  8, 26.6),
        ("ZMW", 2025,  9, 23.811),
        ("ZMW", 2025, 10, 23.32),
        ("ZMW", 2025, 11, 23.536),
        ("ZMW", 2025, 12, 23.91),
        ("ZMW", 2026,  1, 23.7),
        ("ZMW", 2026,  2, 156.731),
        # --- ETB (Ethiopian Birr) — rates used in CBE / Dashen sheets ---
        ("ETB", 2022,  7, 52.1427),
        ("ETB", 2022,  8, 52.4617),
        ("ETB", 2022,  9, 52.5893),
        ("ETB", 2022, 10, 52.8777),
        ("ETB", 2022, 11, 53.0339),
        ("ETB", 2022, 12, 53.3387),
        ("ETB", 2023,  1, 53.4716),
        ("ETB", 2023,  2, 53.7445),
        ("ETB", 2023,  3, 53.9027),
        ("ETB", 2023,  4, 54.1696),
        ("ETB", 2023,  5, 54.3041),
        ("ETB", 2023,  6, 54.5943),
        ("ETB", 2023,  7, 54.7611),
        ("ETB", 2023,  8, 55.0944),
        ("ETB", 2023,  9, 55.2224),
        ("ETB", 2023, 10, 55.4947),
        ("ETB", 2023, 11, 55.6854),
        ("ETB", 2023, 12, 55.9969),
        ("ETB", 2024,  1, 56.1663),
        ("ETB", 2024,  2, 56.4624),
        ("ETB", 2024,  3, 56.6236),
        ("ETB", 2024,  4, 56.9193),
        ("ETB", 2024,  5, 57.0504),
        ("ETB", 2024,  6, 57.3265),
        ("ETB", 2024,  7, 77.5192),
        ("ETB", 2024,  8, 107.0682),
        ("ETB", 2024,  9, 115.9662),
        ("ETB", 2024, 10, 120.1004),
        ("ETB", 2024, 11, 124.1839),
        ("ETB", 2024, 12, 125.0975),
        ("ETB", 2025,  1, 125.4119),
        ("ETB", 2025,  2, 126.2308),
        ("ETB", 2025,  3, 129.9114),
        ("ETB", 2025,  4, 133.8203),
        ("ETB", 2025,  5, 135.2875),
        ("ETB", 2025,  6, 136.6634),
        ("ETB", 2025,  7, 141.3926),
        ("ETB", 2025,  8, 146.406),
        ("ETB", 2025,  9, 144.879),
        ("ETB", 2025, 10, 153.1498),
        ("ETB", 2025, 11, 154.8885),
        ("ETB", 2025, 12, 155.7553),
        ("ETB", 2026,  1, 155.4775),
        ("ETB", 2026,  2, 156.71),
    ]
    for currency, year, month, rate in rates:
        existing = (db.query(ExchangeRate)
                    .filter_by(currency=currency, year=year, month=month, strategy="first_day")
                    .first())
        if not existing:
            db.add(ExchangeRate(currency=currency, year=year, month=month,
                                rate_usd=rate, strategy="first_day", source="seed_excel"))


# ---------------------------------------------------------------------------
# Helper: upsert a monthly metric
# ---------------------------------------------------------------------------

def _upsert(db, bank, year, month, total_txs, amount_orig, amount_usd):
    fx = (db.query(ExchangeRate)
          .filter_by(currency=bank.currency, year=year, month=month, strategy="first_day")
          .first())

    contract_amount = calculate_billing(total_txs, TIERS)
    bill = total_to_bill(total_txs, TIERS, 750.0)
    avg = amount_usd / total_txs if total_txs else 0.0

    m = db.query(MonthlyMetric).filter_by(bank_id=bank.id, year=year, month=month).first()
    if m:
        m.total_txs = total_txs
        m.amount_orig = amount_orig
        m.currency = bank.currency
        m.amount_usd = amount_usd
        m.fx_rate_id = fx.id if fx else None
        m.avg_per_tx_usd = avg
        m.contract_amount = contract_amount
        m.total_to_bill = bill
    else:
        db.add(MonthlyMetric(
            bank_id=bank.id, year=year, month=month,
            total_txs=total_txs, amount_orig=amount_orig,
            currency=bank.currency, amount_usd=amount_usd,
            fx_rate_id=fx.id if fx else None,
            avg_per_tx_usd=avg,
            contract_amount=contract_amount,
            total_to_bill=bill,
        ))


# ---------------------------------------------------------------------------
# Zanaco — ZMW amounts from Raw Data_Zanaco, USD from Summary Zanaco pivot
# ---------------------------------------------------------------------------

def _seed_zanaco(db, bank):
    # (year, month, total_txs, amount_zmw, amount_usd)
    # Raw ZMW from Raw Data_Zanaco aggregated by month
    # USD from the pivot table in CBZ / Summary Zanaco sheet
    data = [
        (2023,  4,   214,    755882.00,     42628.12993458155),
        (2023,  5,  1159,   3430608.00,    175983.66668547594),
        (2023,  6,  1467,   4166097.00,    237289.7989405935),
        (2023,  7,  1655,   4368899.00,    230548.7598944591),
        (2023,  8,  1788,   4797929.00,    237866.26145845212),
        (2023,  9,  1776,   3564834.00,    169833.2555192423),
        (2023, 10,  1316,   1669680.00,     75756.80580762251),
        (2023, 11,  1133,   2009150.00,     84774.26160337553),
        (2023, 12,  1394,   2355640.00,     91776.98990922197),
        (2024,  1,  1581,   2640441.00,     97534.02039007093),
        (2024,  2,  1222,   3307799.00,    141086.4057461655),
        (2024,  3,  1005,   1747108.00,     70258.09305505287),
        (2024,  4,  1142,   1413209.00,     52830.2429906542),
        (2024,  5,  1445,   2065039.00,     80195.68932038835),
        (2024,  6,  1596,   2610312.00,    108990.06263048018),
        (2024,  7,  2106,   5312390.00,    204716.37764932562),
        (2024,  8,  2457,   9465899.00,    363220.8664287633),
        (2024,  9,  2769,  10082411.00,    381909.5075757577),
        (2024, 10,  3035,   9328520.00,    349382.7715355805),
        (2024, 11,  2939,  12389512.00,    461434.3389199255),
        (2024, 12,  3649,  15817604.00,    568467.3495058401),
        (2025,  1,  4898,  20535100.00,    737224.7312831633),
        (2025,  2,  5884,  23452132.00,    841948.2598924414),
        (2025,  3,  6035,  19078602.00,    717240.6766917291),
        (2025,  4,  6100,  20953447.00,    879990.2146066944),
        (2025,  5,  7838,  26400968.00,    992517.5939849622),
        (2025,  6,  7964,  26834399.00,   1126974.8855570953),
        (2025,  7, 10504,  30521157.85,   1308797.5064322469),
        (2025,  8, 11642,  31157076.60,   1323805.090074779),
        (2025,  9,  9500,  28663221.72,   1198796.3914680053),
        (2025, 10, 10409,  38912134.49,   1641862.2147679324),
        (2025, 11, 10902,  39275961.20,   1732126.1830209477),
        (2025, 12, 11941,  43868170.24,   1984985.0787330314),
        (2026,  1, 13133,  49832285.49,   2562071.2334190235),
        (2026,  2,  1379,   2988284.97,    159981.84957358302),
    ]
    for year, month, txs, amount_orig, amount_usd in data:
        _upsert(db, bank, year, month, txs, amount_orig, amount_usd)
    db.flush()
    print(f"  Zanaco: {len(data)} períodos cargados")


# ---------------------------------------------------------------------------
# CBE — ETB amounts from Raw Data_CBE, USD from Summary CBE
# ---------------------------------------------------------------------------

def _seed_cbe(db, bank):
    # (year, month, total_txs, amount_etb, amount_usd)
    # USD from Summary CBE sheet
    data = [
        (2022,  7, 440, 10135769.00, 194385.1967773054),
        (2022,  8, 119,  2676082.00,  51010.203634270336),
        (2022,  9, 124,  3838444.00,  72989.0681184195),
        (2022, 10, 126,  3263201.00,  61712.234079772774),
        (2022, 11,  62,  1507428.00,  28423.857193229233),
        (2022, 12,  73,  1770425.00,  33192.1287920403),
        (2023,  1,  45,  1185552.00,  22171.620074955685),
        (2023,  2,  50,   973377.00,  18111.192773214),
        (2023,  3,  33,   549155.00,  10187.894112910853),
    ]
    for year, month, txs, amount_orig, amount_usd in data:
        _upsert(db, bank, year, month, txs, amount_orig, amount_usd)
    db.flush()
    print(f"  CBE: {len(data)} períodos cargados")


# ---------------------------------------------------------------------------
# Dashen Bank — ETB amounts from Dashen_Data, USD from Summary Dashen pivot
# ---------------------------------------------------------------------------

def _seed_dashen(db, bank):
    # (year, month, total_txs, amount_etb, amount_usd)
    # ETB from Dashen_Data raw sheet aggregated by month
    # USD from Summary Dashen Bank pivot table
    data = [
        (2024,  1,  77,  6736266.00,  119934.30224173571),
        (2024,  2,  61,  5808929.00,  102881.36884014851),
        (2024,  3,  61,  4437657.00,   78371.1561963563),
        (2024,  4, 100, 15307602.00,  268935.1766448287),
        (2024,  5,  72,  5162414.00,   90488.65564483334),
        (2024,  6,  71, 12392808.00,  216179.39347422228),
        (2024,  7,  75,   574527.00,    7411.415494483947),
        (2024,  8,  77, 13762672.00,  128541.17282255608),
        (2024,  9,  76,  5024533.00,   43327.56441100942),
        (2024, 10, 133,  8087680.00,   67340.99137055333),
        (2024, 11, 110,  9896612.00,   79693.19694420935),
        (2024, 12, 133,  3074665.00,   24578.149043745878),
        (2025,  1, 152,   548468.00,    4373.332993121067),
        (2025,  2,  90,   308749.00,    2445.9086055067382),
        (2025,  3, 134,   553145.00,    4258.882986873296),
        (2025,  4, 126,   549238.00,    4227.789093181969),
        (2025,  5, 141,   553829.00,    4138.602289787124),
        (2025,  6, 117,   732488.00,    5414.306569343066),
        (2025,  7,  98,   508664.00,    3722.0206726892507),
        (2025,  8, 115,   551029.00,    3897.155862470879),
        (2025,  9, 109,   437974.00,    2991.5030804748435),
        (2025, 10, 159, 10739705.48,   74128.79354495821),
        (2025, 11, 134,  5946275.99,   38826.534478007816),
        (2025, 12, 162,  3532370.29,   22805.891270171764),
        (2026,  1, 138,   854996.42,    5489.356830875098),
        (2026,  2, 131,   606570.93,    3901.3421877763667),
    ]
    for year, month, txs, amount_orig, amount_usd in data:
        _upsert(db, bank, year, month, txs, amount_orig, amount_usd)
    db.flush()
    print(f"  Dashen: {len(data)} períodos cargados")


if __name__ == "__main__":
    run()
