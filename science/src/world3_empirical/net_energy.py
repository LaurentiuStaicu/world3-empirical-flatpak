"""Dynamic scenarios for energy quality and net energy.

The module is deliberately separate from the empirically conditioned BAU2
observation layer. Its parameters are structural priors, not measured global
EROI observations, so outputs are sensitivity scenarios rather than forecasts.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NetEnergyParameters:
    start_year: int = 2025
    end_year: int = 2100
    time_step: float = 1.0
    gross_energy_index: float = 100.0
    gross_growth_initial: float = 0.018
    gross_growth_long_run: float = -0.004
    gross_growth_transition_year: float = 2040.0
    gross_growth_transition_width: float = 12.0
    # EI Statistical Review 2026, Total World gross primary energy, 2025.
    fossil_share_initial: float = 0.8623843748
    fossil_share_long_run: float = 0.30
    fossil_transition_midpoint: float = 2045.0
    fossil_transition_width: float = 11.0
    fossil_resource_fraction_initial: float = 0.65
    fossil_depletion_rate: float = 0.010
    fossil_eroi_initial: float = 8.4694506689
    fossil_eroi_floor: float = 4.0
    fossil_quality_elasticity: float = 1.35
    renewable_eroi_initial: float = 10.0
    renewable_eroi_ceiling: float = 18.0
    renewable_learning_rate: float = 0.030
    integration_burden_max: float = 0.32

    def validate(self) -> None:
        if self.end_year <= self.start_year:
            raise ValueError("end_year must be greater than start_year")
        if not 0 < self.time_step <= 1:
            raise ValueError("time_step must be in (0, 1]")
        for name in (
            "fossil_share_initial",
            "fossil_share_long_run",
            "fossil_resource_fraction_initial",
        ):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if self.fossil_eroi_floor <= 1 or self.fossil_eroi_initial <= self.fossil_eroi_floor:
            raise ValueError("fossil EROI must remain above 1 and above its floor initially")
        if self.renewable_eroi_initial <= 1 or self.renewable_eroi_ceiling < self.renewable_eroi_initial:
            raise ValueError("renewable EROI bounds are invalid")


SCENARIOS: dict[str, NetEnergyParameters] = {
    "quality_decline": NetEnergyParameters(),
    "accelerated_transition": replace(
        NetEnergyParameters(),
        fossil_share_long_run=0.15,
        fossil_transition_midpoint=2038.0,
        fossil_transition_width=8.0,
        renewable_eroi_ceiling=21.0,
        integration_burden_max=0.24,
        gross_growth_long_run=0.001,
    ),
    "fossil_lock_in_stress": replace(
        NetEnergyParameters(),
        fossil_share_long_run=0.55,
        fossil_transition_midpoint=2055.0,
        fossil_depletion_rate=0.016,
        fossil_eroi_floor=3.0,
        fossil_quality_elasticity=1.7,
        renewable_eroi_ceiling=15.0,
        integration_burden_max=0.38,
        gross_growth_long_run=-0.012,
        gross_growth_transition_year=2035.0,
    ),
}


def _smooth_transition(year: float, midpoint: float, width: float) -> float:
    x = np.clip((year - midpoint) / width, -60.0, 60.0)
    return float(1.0 / (1.0 + np.exp(-x)))


def _transition_from_start(
    year: float, start_year: float, midpoint: float, width: float
) -> float:
    """Normalize a logistic so the declared start-year state is exact."""
    raw = _smooth_transition(year, midpoint, width)
    initial = _smooth_transition(start_year, midpoint, width)
    return float(np.clip((raw - initial) / (1.0 - initial), 0.0, 1.0))


def simulate_net_energy(parameters: NetEnergyParameters) -> pd.DataFrame:
    """Simulate resource quality, source EROI, mix and resulting net energy."""
    parameters.validate()
    years = np.arange(
        parameters.start_year,
        parameters.end_year + parameters.time_step / 2,
        parameters.time_step,
    )
    gross = np.empty(len(years))
    resource_fraction = np.empty(len(years))
    gross[0] = parameters.gross_energy_index
    resource_fraction[0] = parameters.fossil_resource_fraction_initial
    records: list[dict[str, float]] = []

    for index, year in enumerate(years):
        transition = _transition_from_start(
            year,
            parameters.start_year,
            parameters.fossil_transition_midpoint,
            parameters.fossil_transition_width,
        )
        fossil_share = parameters.fossil_share_initial + (
            parameters.fossil_share_long_run - parameters.fossil_share_initial
        ) * transition
        renewable_share = 1.0 - fossil_share

        quality_ratio = max(
            resource_fraction[index] / parameters.fossil_resource_fraction_initial,
            0.0,
        )
        fossil_eroi = parameters.fossil_eroi_floor + (
            parameters.fossil_eroi_initial - parameters.fossil_eroi_floor
        ) * quality_ratio**parameters.fossil_quality_elasticity

        elapsed = year - parameters.start_year
        renewable_gross_eroi = parameters.renewable_eroi_ceiling - (
            parameters.renewable_eroi_ceiling - parameters.renewable_eroi_initial
        ) * np.exp(-parameters.renewable_learning_rate * elapsed)
        variable_share = max(
            renewable_share - (1.0 - parameters.fossil_share_initial), 0.0
        )
        integration_burden = parameters.integration_burden_max * variable_share**2
        renewable_effective_eroi = renewable_gross_eroi / (1.0 + integration_burden)

        # Energy investments add, so the system EROI is a harmonic mixture.
        system_eroi = 1.0 / (
            fossil_share / fossil_eroi + renewable_share / renewable_effective_eroi
        )
        reinvestment_share = 1.0 / system_eroi
        net = gross[index] * (1.0 - reinvestment_share)
        records.append(
            {
                "year": float(year),
                "gross_energy_index": float(gross[index]),
                "net_energy_index_raw": float(net),
                "system_eroi": float(system_eroi),
                "energy_reinvestment_pct": float(100.0 * reinvestment_share),
                "fossil_share": float(fossil_share),
                "renewable_share": float(renewable_share),
                "fossil_resource_fraction": float(resource_fraction[index]),
                "fossil_eroi": float(fossil_eroi),
                "renewable_eroi_effective": float(renewable_effective_eroi),
                "integration_burden": float(integration_burden),
            }
        )

        if index + 1 < len(years):
            growth_transition = _transition_from_start(
                year,
                parameters.start_year,
                parameters.gross_growth_transition_year,
                parameters.gross_growth_transition_width,
            )
            growth = parameters.gross_growth_initial + (
                parameters.gross_growth_long_run - parameters.gross_growth_initial
            ) * growth_transition
            gross[index + 1] = gross[index] * np.exp(growth * parameters.time_step)
            extraction_pressure = (
                parameters.fossil_depletion_rate
                * fossil_share
                * gross[index]
                / parameters.gross_energy_index
            )
            resource_fraction[index + 1] = max(
                resource_fraction[index] - extraction_pressure * parameters.time_step,
                0.001,
            )

    frame = pd.DataFrame.from_records(records)
    base_net = float(frame.loc[0, "net_energy_index_raw"])
    frame["net_energy_index"] = 100.0 * frame["net_energy_index_raw"] / base_net
    return frame


def run_named_scenarios() -> pd.DataFrame:
    frames = []
    for name, parameters in SCENARIOS.items():
        frame = simulate_net_energy(parameters)
        frame.insert(0, "scenario", name)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
