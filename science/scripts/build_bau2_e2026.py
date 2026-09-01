"""Build the BAU Hybrid 2026 application dataset.

The current hybrid starts from official World3-03 BAU2 and estimates a local
level/trend observation layer for each measurable indicator. It is a
transition release toward joint dynamic recalibration: the interface no longer
pretends that the per-indicator correction is already a fully coupled World3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

import numpy as np
import pandas as pd
from scipy.stats import linregress


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bau2_e2026" / "2026-08-28"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "outputs" / "bau2_e2026"
BAU2 = ROOT / "outputs" / "world3_03_bau2.csv"
BAU = ROOT / "outputs" / "world3_03_bau.csv"

FAOSTAT_URL = (
    "https://bulks-faostat.fao.org/production/"
    "Production_Indices_E_All_Data_(Normalized).zip"
)
HDI_URL = (
    "https://ourworldindata.org/grapher/human-development-index.csv"
    "?v=1&csvType=full&useColumnShortNames=false"
)
UN_POPULATION_URL = (
    "https://ourworldindata.org/grapher/population-with-un-projections.csv"
    "?v=1&csvType=full&useColumnShortNames=true"
)


@dataclass(frozen=True)
class Indicator:
    key: str
    label: str
    unit: str
    observed: pd.Series
    model: pd.Series
    model_alt: pd.Series
    source: str
    source_url: str
    status: str
    benchmark: pd.Series | None = None
    lower: float | None = None
    upper: float | None = None


def download(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    request = urllib.request.Request(url, headers={"User-Agent": "World3-Empirical/0.3"})
    with urllib.request.urlopen(request, timeout=180) as response:
        path.write_bytes(response.read())
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_faostat_food() -> tuple[pd.Series, Path]:
    archive = download(FAOSTAT_URL, RAW / "faostat_production_indices.zip")
    parts: list[pd.DataFrame] = []
    with zipfile.ZipFile(archive) as bundle:
        csv_name = next(name for name in bundle.namelist() if name.endswith("(Normalized).csv"))
        with bundle.open(csv_name) as handle:
            for chunk in pd.read_csv(handle, encoding="latin-1", chunksize=300_000):
                selected = chunk[
                    chunk["Area"].eq("World")
                    & chunk["Item"].eq("Food")
                    & chunk["Element"].eq(
                        "Gross per capita Production Index Number (2014-2016 = 100)"
                    )
                ][["Year", "Value"]]
                if not selected.empty:
                    parts.append(selected)
    frame = pd.concat(parts, ignore_index=True).drop_duplicates("Year")
    return frame.set_index("Year")["Value"].sort_index(), archive


def load_hdi() -> tuple[pd.Series, Path]:
    path = download(HDI_URL, RAW / "undp_hdi_owid_adapter.csv")
    frame = pd.read_csv(path)
    world = frame.loc[frame["Entity"].eq("World")]
    return world.set_index("Year")["Human Development Index"].sort_index(), path


def load_un_population() -> tuple[pd.Series, Path]:
    path = download(UN_POPULATION_URL, RAW / "un_wpp2024_owid_adapter.csv")
    frame = pd.read_csv(path)
    world = frame.loc[frame["entity"].eq("World")].set_index("year")
    observed = world["population__sex_all__age_all__variant_estimates"]
    projected = world["population__sex_all__age_all__variant_medium__projected"]
    combined = observed.combine_first(projected) / 1e9
    return combined.sort_index(), path


def normalize(series: pd.Series, base_year: int) -> pd.Series:
    return 100.0 * series / float(series.loc[base_year])


def build_indicators() -> tuple[list[Indicator], list[Path]]:
    empirical = pd.read_csv(PROCESSED / "empirical_model_inputs_2026-08-28.csv").set_index("year")
    bau2 = pd.read_csv(BAU2).set_index("year")
    bau2.index = bau2.index.astype(int)
    bau = pd.read_csv(BAU).set_index("year")
    bau.index = bau.index.astype(int)

    fao_food, fao_path = load_faostat_food()
    hdi, hdi_path = load_hdi()
    un_population, un_path = load_un_population()

    population = empirical["population"].dropna() / 1e9
    industry_pc = (empirical["industrial_output"] / empirical["population"]).dropna()
    industry_pc = normalize(industry_pc, 2015)
    ghg_flow = empirical["fossil_co2_proxy"].dropna()
    ghg_flow = normalize(ghg_flow, 1990)

    indicators = [
        Indicator(
            "population",
            "Populație mondială",
            "miliarde persoane",
            population,
            bau2["population"] / 1e9,
            bau["population"] / 1e9,
            "World Bank WDI SP.POP.TOTL",
            "https://api.worldbank.org/v2/country/WLD/indicator/SP.POP.TOTL",
            "observat până în 2025; valoarea 2025 poate fi estimată",
            benchmark=un_population,
            lower=0,
        ),
        Indicator(
            "industry_per_capita",
            "Producție industrială pe locuitor",
            "indice, 2015=100",
            industry_pc,
            normalize(bau2["industrial_output_per_capita"], 2015),
            normalize(bau["industrial_output_per_capita"], 2015),
            "World Bank WDI NV.IND.TOTL.KD / populație",
            "https://api.worldbank.org/v2/country/WLD/indicator/NV.IND.TOTL.KD",
            "proxy observat până în 2025; include construcții",
            lower=0,
        ),
        Indicator(
            "food_per_capita",
            "Producție alimentară pe locuitor",
            "indice FAO, 2014–2016=100",
            fao_food,
            normalize(bau2["food_per_capita"], 2015),
            normalize(bau["food_per_capita"], 2015),
            "FAOSTAT Production Indices, World, Food, gross per capita",
            "https://www.fao.org/faostat/en/#data/QI",
            "observat până în 2024; agregat fizic ponderat cu prețuri",
            lower=0,
        ),
        Indicator(
            "pollution_pressure",
            "Emisii antropice anuale (proxy)",
            "indice de flux, 1990=100",
            ghg_flow,
            normalize(bau2["persistent_pollution_generation_rate"], 1990),
            normalize(bau["persistent_pollution_generation_rate"], 1990),
            "World Bank / EDGAR proxy EN.GHG.CO2.MT.CE.AR5",
            "https://edgar.jrc.ec.europa.eu/dataset_ghg2025",
            "observat până în 2024; comparație flux-la-flux cu generarea generică de poluare World3, nu cu stocul latent",
            lower=0,
        ),
        Indicator(
            "human_welfare",
            "Dezvoltare umană",
            "indice 0–1",
            hdi,
            bau2["human_welfare_index"],
            bau["human_welfare_index"],
            "UNDP Human Development Report 2025, HDI",
            "https://hdr.undp.org/data-center/documentation-and-downloads",
            "observat până în 2023; HDI nu este identic cu HWI World3",
            lower=0,
            upper=1,
        ),
    ]
    return indicators, [fao_path, hdi_path, un_path]


def holt_residuals(residual: pd.Series, alpha: float = 0.35, beta: float = 0.08) -> pd.DataFrame:
    values = residual.to_numpy(dtype=float)
    level = np.empty_like(values)
    trend = np.empty_like(values)
    level[0] = values[0]
    trend[0] = 0.0 if len(values) < 2 else values[1] - values[0]
    for index in range(1, len(values)):
        previous_level = level[index - 1]
        level[index] = alpha * values[index] + (1 - alpha) * (
            previous_level + trend[index - 1]
        )
        trend[index] = beta * (level[index] - previous_level) + (1 - beta) * trend[index - 1]
    return pd.DataFrame({"level": level, "trend": trend}, index=residual.index)


def fit_indicator(
    indicator: Indicator,
    *,
    cutoff: int | None = None,
    end_year: int = 2100,
    draws: int = 2500,
    seed: int = 20260828,
    trend_weight: float = 1.0,
    damping: float = 12.0,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    observed = indicator.observed.dropna().copy()
    if cutoff is not None:
        observed = observed.loc[observed.index <= cutoff]
    last_year = int(observed.index.max())
    model = indicator.model.reindex(range(int(indicator.model.index.min()), end_year + 1)).interpolate()
    overlap = observed.index.intersection(model.index)
    residual = np.log(observed.loc[overlap] / model.loc[overlap])
    filtered = holt_residuals(residual)

    recent = residual.loc[residual.index >= max(int(residual.index.min()), last_year - 14)]
    regression = linregress(recent.index.to_numpy(dtype=float), recent.to_numpy(dtype=float))
    slope = float(regression.slope) * trend_weight
    slope_se = float(regression.stderr) if np.isfinite(regression.stderr) else 0.0
    # The forecast must start at the latest observation, while the historical
    # fitted line remains smoothed and suitable for visual residual diagnosis.
    level = float(residual.loc[last_year])
    innovation = residual - filtered["level"]
    sigma = max(float(innovation.std(ddof=1)), 0.004)

    years = np.arange(max(1950, int(model.index.min())), end_year + 1)
    frame = pd.DataFrame({"year": years})
    frame["observed"] = indicator.observed.reindex(years).to_numpy()
    frame["original_bau2"] = model.reindex(years).to_numpy()
    frame["fitted"] = np.nan
    fit_values = model.loc[overlap] * np.exp(filtered["level"])
    fit_map = fit_values.to_dict()
    frame["fitted"] = frame["year"].map(fit_map)

    forecast_years = years[years >= last_year]
    horizon = forecast_years - last_year
    correction = level + slope * damping * (1 - np.exp(-horizon / damping))
    central = model.loc[forecast_years].to_numpy() * np.exp(correction)

    rng = np.random.default_rng(seed + sum(map(ord, indicator.key)))
    level_draw = rng.normal(level, sigma / np.sqrt(max(len(recent), 4)), size=draws)
    effective_slope_se = max(slope_se, sigma / max(len(recent), 8))
    slope_draw = rng.normal(slope, effective_slope_se, size=draws)
    damping_draw = np.clip(rng.lognormal(np.log(damping), 0.30, size=draws), 4, 30)
    draw_correction = (
        level_draw[:, None]
        + slope_draw[:, None]
        * damping_draw[:, None]
        * (1 - np.exp(-horizon[None, :] / damping_draw[:, None]))
    )
    random_walk = rng.normal(size=(draws, len(horizon))) * sigma * np.sqrt(horizon[None, :] / 18.0)
    draw_values = model.loc[forecast_years].to_numpy()[None, :] * np.exp(
        draw_correction + random_walk
    )

    # Structural sensitivity: repeat the empirical anchoring against the
    # official BAU resource-limited path.  The resulting envelope is not a
    # confidence interval; it shows how strongly the future depends on which
    # World3 continuation mechanism is retained.
    alternate = indicator.model_alt.reindex(model.index).interpolate()
    frame["original_bau"] = alternate.reindex(years).to_numpy()
    alt_residual = np.log(observed.loc[overlap] / alternate.loc[overlap])
    alt_recent = alt_residual.loc[alt_residual.index >= max(int(alt_residual.index.min()), last_year - 14)]
    alt_regression = linregress(alt_recent.index.to_numpy(dtype=float), alt_recent.to_numpy(dtype=float))
    alt_slope = float(alt_regression.slope) * trend_weight
    alt_level = float(alt_residual.loc[last_year])
    alt_correction = alt_level + alt_slope * damping * (1 - np.exp(-horizon / damping))
    alternate_central = alternate.loc[forecast_years].to_numpy() * np.exp(alt_correction)
    if indicator.lower is not None:
        draw_values = np.maximum(draw_values, indicator.lower)
        central = np.maximum(central, indicator.lower)
    if indicator.upper is not None:
        draw_values = np.minimum(draw_values, indicator.upper)
        central = np.minimum(central, indicator.upper)
        alternate_central = np.minimum(alternate_central, indicator.upper)
    if indicator.lower is not None:
        alternate_central = np.maximum(alternate_central, indicator.lower)

    positions = frame["year"].ge(last_year)
    frame.loc[positions, "forecast_median"] = central
    frame.loc[positions, "p10"] = np.quantile(draw_values, 0.10, axis=0)
    frame.loc[positions, "p90"] = np.quantile(draw_values, 0.90, axis=0)
    frame.loc[positions, "alternate_bau"] = alternate_central
    frame.loc[positions, "sensitivity_low"] = np.minimum(
        frame.loc[positions, "p10"].to_numpy(), alternate_central
    )
    frame.loc[positions, "sensitivity_high"] = np.maximum(
        frame.loc[positions, "p90"].to_numpy(), alternate_central
    )
    if indicator.benchmark is not None:
        frame["benchmark"] = indicator.benchmark.reindex(years).to_numpy()
    else:
        frame["benchmark"] = np.nan

    # One continuous hybrid line for the application: retrospective fitted
    # values where observations exist, followed by the forecast at and after
    # the latest observed year. Observations remain separate points.
    frame["hybrid_2026"] = frame["fitted"]
    forecast_available = frame["forecast_median"].notna()
    frame.loc[forecast_available, "hybrid_2026"] = frame.loc[
        forecast_available, "forecast_median"
    ]

    metadata: dict[str, float | int | str] = {
        "key": indicator.key,
        "label": indicator.label,
        "unit": indicator.unit,
        "source": indicator.source,
        "source_url": indicator.source_url,
        "status": indicator.status,
        "first_observed_year": int(indicator.observed.index.min()),
        "last_observed_year": int(indicator.observed.index.max()),
        "recent_log_residual_slope": slope,
        "recent_slope_standard_error": slope_se,
        "observation_innovation_sigma": sigma,
        "damping_years": damping,
        "trend_weight": trend_weight,
        "empirical_interval": "observation-layer Monte Carlo p10-p90; conditional on the retained BAU2 structure",
        "structural_alternative": "alternate_bau is the same empirical anchoring applied to official World3-03 BAU",
        "sensitivity_band": "outer BAU/BAU2 envelope plus observation-layer p10-p90; not a probability interval",
    }
    return frame, metadata


def backtest(
    indicator: Indicator,
    cutoff: int = 2018,
    *,
    trend_weight: float = 1.0,
    damping: float = 12.0,
    evaluation_end: int | None = None,
) -> dict[str, float | int | str]:
    available_after = indicator.observed.loc[indicator.observed.index > cutoff].dropna()
    if evaluation_end is not None:
        available_after = available_after.loc[available_after.index <= evaluation_end]
    if available_after.empty:
        return {"key": indicator.key, "cutoff": cutoff, "n": 0}
    fit, _ = fit_indicator(
        indicator,
        cutoff=cutoff,
        end_year=int(available_after.index.max()),
        draws=300,
        trend_weight=trend_weight,
        damping=damping,
    )
    forecast = fit.set_index("year")["forecast_median"].reindex(available_after.index)

    model = indicator.model.reindex(range(int(indicator.model.index.min()), int(available_after.index.max()) + 1)).interpolate()
    anchored = model.loc[available_after.index] * (
        float(indicator.observed.loc[cutoff]) / float(model.loc[cutoff])
    )
    hybrid_mape = float(np.mean(np.abs((forecast - available_after) / available_after)) * 100)
    anchored_mape = float(np.mean(np.abs((anchored - available_after) / available_after)) * 100)
    return {
        "key": indicator.key,
        "cutoff": cutoff,
        "test_start": int(available_after.index.min()),
        "test_end": int(available_after.index.max()),
        "n": int(len(available_after)),
        "bau2_level_anchored_mape_pct": anchored_mape,
        "bau2_e2026_mape_pct": hybrid_mape,
        "improvement_pct": 100 * (anchored_mape - hybrid_mape) / anchored_mape if anchored_mape else 0,
        "trend_weight": trend_weight,
        "damping_years": damping,
    }


def select_hyperparameters(
    indicator: Indicator, *, forecast_origin: int = 2018
) -> tuple[float, float]:
    """Choose damping using only observations available at forecast_origin."""
    validation_cutoff = forecast_origin - 3
    validation = indicator.observed.loc[
        (indicator.observed.index > validation_cutoff)
        & (indicator.observed.index <= forecast_origin)
    ].dropna()
    if len(validation) < 2 or validation_cutoff not in indicator.observed.index:
        return 0.5, 12.0
    best = (float("inf"), 0.0, 12.0)
    for weight in (0.0, 0.25, 0.5, 0.75, 1.0):
        for damping in (6.0, 12.0, 20.0):
            frame, _ = fit_indicator(
                indicator,
                cutoff=validation_cutoff,
                end_year=forecast_origin,
                draws=100,
                trend_weight=weight,
                damping=damping,
            )
            forecast = frame.set_index("year")["forecast_median"].reindex(validation.index)
            error = float(np.mean(np.abs((forecast - validation) / validation)))
            # Prefer the least complex correction when scores are essentially tied.
            score = error + 0.00005 * weight + 0.000002 * damping
            if score < best[0]:
                best = (score, weight, damping)
    return best[1], best[2]


def rolling_origin_backtest(
    indicator: Indicator,
    origins: tuple[int, ...] = (2005, 2010, 2015, 2018),
) -> dict[str, float | int | str]:
    """Evaluate several historical forecast origins without future leakage."""
    results: list[dict[str, float | int | str]] = []
    used_origins: list[int] = []
    for origin in origins:
        if origin not in indicator.observed.index:
            continue
        available_after = indicator.observed.loc[
            indicator.observed.index > origin
        ].dropna()
        if len(available_after) < 2:
            continue
        weight, damping = select_hyperparameters(
            indicator, forecast_origin=origin
        )
        result = backtest(
            indicator,
            cutoff=origin,
            trend_weight=weight,
            damping=damping,
        )
        if int(result.get("n", 0)):
            results.append(result)
            used_origins.append(origin)

    if not results:
        return {"key": indicator.key, "origins": "", "n_origins": 0, "n": 0}

    total_n = sum(int(result["n"]) for result in results)
    hybrid = sum(
        float(result["bau2_e2026_mape_pct"]) * int(result["n"])
        for result in results
    ) / total_n
    anchored = sum(
        float(result["bau2_level_anchored_mape_pct"]) * int(result["n"])
        for result in results
    ) / total_n
    return {
        "key": indicator.key,
        "origins": "/".join(str(origin) for origin in used_origins),
        "n_origins": len(used_origins),
        "n": total_n,
        "bau2_level_anchored_mape_pct": anchored,
        "bau2_e2026_mape_pct": hybrid,
        "improvement_pct": (
            100 * (anchored - hybrid) / anchored if anchored else 0
        ),
        "selection_rule": "nested 3-year validation ending at each origin",
    }


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    indicators, downloaded = build_indicators()
    metadata = []
    tests = []
    rolling_tests = []
    for indicator in indicators:
        trend_weight, damping = select_hyperparameters(
            indicator, forecast_origin=2018
        )
        frame, description = fit_indicator(
            indicator, trend_weight=trend_weight, damping=damping
        )
        frame.to_csv(OUTPUT / f"{indicator.key}.csv", index=False, float_format="%.8g")
        metadata.append(description)
        if 2018 in indicator.observed.index:
            tests.append(
                backtest(
                    indicator,
                    trend_weight=trend_weight,
                    damping=damping,
                )
            )
        rolling_tests.append(rolling_origin_backtest(indicator))

    pd.DataFrame(tests).to_csv(OUTPUT / "backtest_2019_latest.csv", index=False)
    pd.DataFrame(rolling_tests).to_csv(
        OUTPUT / "backtest_multi_origin.csv", index=False
    )
    manifest = {
        "model": "BAU Hybrid 2026",
        "generated_on": str(date(2026, 8, 28)),
        "structural_model": "official World3-03 scenario 2 (BAU2)",
        "method": "transitional per-indicator empirical assimilation on BAU2; joint dynamic recalibration remains the next model stage",
        "uncertainty": "observation p10-p90 plus a BAU/BAU2 structural sensitivity envelope",
        "validation": "hyperparameters selected without the 2019-latest holdout; multi-origin audit uses nested 3-year validation ending at each forecast origin",
        "pollution_mapping": "annual CO2 flow is compared with World3 persistent pollution generation rate (flow-to-flow), never with the latent persistent pollution stock",
        "important_limit": "the sensitivity envelope is not a probability interval and excludes policy, war, novel technology, and unmodeled tipping points",
        "indicators": metadata,
        "downloads": [
            {"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in downloaded
        ],
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(pd.DataFrame(tests).to_string(index=False))
    print(f"Saved BAU2-E2026 datasets to {OUTPUT}")


if __name__ == "__main__":
    main()
