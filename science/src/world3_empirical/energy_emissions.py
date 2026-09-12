"""Experimental accounting only: no calibrated coefficients or World3 coupling.

Energy is fuel input on a net-calorific basis. Electricity is gross generation.
Atmospheric sinks are explicit external inputs, not a fitted carbon-cycle model.
"""
from dataclasses import dataclass
from math import isfinite


def _nonnegative(**values):
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")


@dataclass(frozen=True)
class CombustionResult:
    electricity_twh: float
    fuel_input_pj_ncv: float
    direct_co2_mt: float


def combustion_generation(*, capacity_gw: float, capacity_factor: float,
                          hours: float, efficiency_ncv: float,
                          co2_kg_per_tj_ncv: float) -> CombustionResult:
    """One technology and interval; excludes upstream and non-CO2 emissions.

    Hours must be supplied (e.g. actual calendar-year hours), not assumed.
    The emissions factor must include the intended oxidation convention.
    """
    _nonnegative(capacity_gw=capacity_gw, capacity_factor=capacity_factor,
                 hours=hours, efficiency_ncv=efficiency_ncv,
                 co2_kg_per_tj_ncv=co2_kg_per_tj_ncv)
    if capacity_factor > 1 or not 0 < efficiency_ncv <= 1 or hours == 0:
        raise ValueError("Invalid utilization, efficiency or interval")
    electricity = capacity_gw * capacity_factor * hours / 1000
    fuel = electricity * 3.6 / efficiency_ncv
    return CombustionResult(electricity, fuel, fuel * co2_kg_per_tj_ncv / 1e6)


def advance_atmospheric_co2(*, stock_gtco2: float,
                            anthropogenic_gtco2_per_year: float,
                            natural_net_source_gtco2_per_year: float,
                            removal_gtco2_per_year: float,
                            years: float) -> float:
    """Mass balance for constant interval-average fluxes; no concentration output.

    Natural net source and removal must refer to non-overlapping processes.
    Negative resulting mass is an input error, never silently clipped.
    Does not prescribe sinks, warming, or damages; cannot forecast independently.
    """
    _nonnegative(stock_gtco2=stock_gtco2,
                 anthropogenic_gtco2_per_year=anthropogenic_gtco2_per_year,
                 natural_net_source_gtco2_per_year=natural_net_source_gtco2_per_year,
                 removal_gtco2_per_year=removal_gtco2_per_year, years=years)
    if years == 0:
        raise ValueError("Interval must be positive")
    result = stock_gtco2 + years * (anthropogenic_gtco2_per_year
             + natural_net_source_gtco2_per_year - removal_gtco2_per_year)
    if result < 0:
        raise ValueError("Removals exceed available atmospheric mass")
    return result


def net_electricity_twh(*, gross_twh: float, auxiliary_fraction: float) -> float:
    """Subtract plant own-use only; excludes transmission/distribution losses."""
    _nonnegative(gross_twh=gross_twh, auxiliary_fraction=auxiliary_fraction)
    if auxiliary_fraction > 1:
        raise ValueError("Auxiliary fraction must not exceed one")
    return gross_twh * (1 - auxiliary_fraction)


def efficiency_from_heat_rate(*, btu_per_net_kwh: float) -> float:
    """EIA rounded conversion; efficiency retains the source heating-value basis.

    This is NET electric efficiency, not EROI or an NCV conversion.
    """
    _nonnegative(btu_per_net_kwh=btu_per_net_kwh)
    if btu_per_net_kwh < 3412:
        raise ValueError("Combustion heat rate implies efficiency above one")
    return 3412 / btu_per_net_kwh
