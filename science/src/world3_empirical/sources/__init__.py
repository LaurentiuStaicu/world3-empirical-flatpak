"""Adapters for authoritative empirical data sources."""

from .world_bank import WorldBankSeries, fetch_world_bank_series, parse_world_bank_payload

__all__ = ["WorldBankSeries", "fetch_world_bank_series", "parse_world_bank_payload"]

