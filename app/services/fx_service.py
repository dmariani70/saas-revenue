from datetime import date
from typing import Optional, Protocol
import httpx

from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate


class FXProvider(Protocol):
    def get_rate(self, currency: str, year: int, month: int) -> Optional[float]:
        """Return units of currency per 1 USD, or None if unavailable."""
        ...


class OpenExchangeRatesProvider:
    """
    Fetches historical FX rates from openexchangerates.org (free tier, API key required).
    Base is USD so rate_usd = units of currency per 1 USD.
    """

    BASE_URL = "https://openexchangerates.org/api"

    def __init__(self, app_id: str):
        self.app_id = app_id

    def get_rate(self, currency: str, year: int, month: int) -> Optional[float]:
        if currency.upper() == "USD":
            return 1.0
        ref_date = date(year, month, 1).isoformat()
        try:
            resp = httpx.get(
                f"{self.BASE_URL}/historical/{ref_date}.json",
                params={"app_id": self.app_id, "symbols": currency.upper(), "base": "USD"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("rates", {}).get(currency.upper())
        except Exception:
            return None


class FrankfurterProvider:
    """Fetches FX rates from frankfurter.app (free, no key) — major currencies only."""

    BASE_URL = "https://api.frankfurter.app"

    def get_rate(self, currency: str, year: int, month: int) -> Optional[float]:
        if currency.upper() == "USD":
            return 1.0
        ref_date = date(year, month, 1).isoformat()
        try:
            resp = httpx.get(
                f"{self.BASE_URL}/{ref_date}",
                params={"from": "USD", "to": currency.upper()},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["rates"].get(currency.upper())
        except Exception:
            return None


class ManualFallback:
    """Used when the API is unavailable; reads from the DB only."""

    def get_rate(self, currency: str, year: int, month: int) -> Optional[float]:
        return None


def _build_default_provider() -> FXProvider:
    from app.config import settings
    if settings.open_exchange_rates_key:
        return OpenExchangeRatesProvider(app_id=settings.open_exchange_rates_key)
    return FrankfurterProvider()


_provider: FXProvider = _build_default_provider()


def set_provider(provider: FXProvider) -> None:
    global _provider
    _provider = provider


def get_or_fetch_rate(
    db: Session,
    currency: str,
    year: int,
    month: int,
    strategy: str = "first_day",
) -> Optional[ExchangeRate]:
    """
    Returns the ExchangeRate record for (currency, year, month).
    If not in DB, fetches from the provider and persists it.
    Never modifies historical records.
    """
    if currency.upper() == "USD":
        # Create a synthetic 1:1 record if needed
        rec = (
            db.query(ExchangeRate)
            .filter_by(currency="USD", year=year, month=month, strategy=strategy)
            .first()
        )
        if not rec:
            rec = ExchangeRate(currency="USD", year=year, month=month,
                               rate_usd=1.0, strategy=strategy, source="fixed")
            db.add(rec)
            db.flush()
        return rec

    rec = (
        db.query(ExchangeRate)
        .filter_by(currency=currency.upper(), year=year, month=month, strategy=strategy)
        .first()
    )
    if rec:
        return rec

    rate = _provider.get_rate(currency, year, month)
    if rate is None:
        return None

    rec = ExchangeRate(
        currency=currency.upper(),
        year=year,
        month=month,
        rate_usd=rate,
        strategy=strategy,
        source="frankfurter.app",
    )
    db.add(rec)
    db.flush()
    return rec
