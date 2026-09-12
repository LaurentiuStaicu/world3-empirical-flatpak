"""Post-hoc error attribution; never an exclusion or model-selection rule."""
import math

from .egrid_temporal import _index, KG_PER_SHORT_TON


def error_influence(training_rows, target_rows, training_year, target_year):
    if target_year != training_year + 1:
        raise ValueError("Years must be consecutive")
    training = _index(training_rows, training_year)
    target = _index(target_rows, target_year)
    plants = sorted(training.keys() & target.keys())
    if not plants:
        raise ValueError("No matched plants")
    signals = {}
    for field, conversion, label in (
        ("UNHTI", 1000, "heat_rate_btu_per_net_kwh"),
        ("UNCO2", KG_PER_SHORT_TON, "co2_kg_per_net_mwh"),
    ):
        records = []
        for plant in plants:
            before, after = training[plant], target[plant]
            ratio = after["PLNGENAN"] / before["PLNGENAN"]
            predicted = before[field] * ratio
            observed = after[field]
            records.append({
                "plant_id": plant,
                "name": before["PNAME"],
                "training_net_mwh": before["PLNGENAN"],
                "target_net_mwh": after["PLNGENAN"],
                "generation_ratio": ratio,
                "training_intensity": conversion * before[field] / before["PLNGENAN"],
                "target_intensity": conversion * observed / after["PLNGENAN"],
                "absolute_quantity_error": abs(predicted - observed),
                "signed_quantity_error": predicted - observed,
                "training_source": before[field + "SRC"],
                "target_source": after[field + "SRC"],
            })
        records.sort(key=lambda r: (-r["absolute_quantity_error"], r["plant_id"]))
        absolute_error = math.fsum(r["absolute_quantity_error"] for r in records)
        target_quantity = math.fsum(target[p][field] for p in plants)
        for row in records:
            row["share_of_absolute_error_pct"] = (
                100 * row["absolute_quantity_error"] / absolute_error if absolute_error else None
            )
        signals[label] = {
            "quantity_unit": "MMBtu" if field == "UNHTI" else "short tons CO2",
            "matched_plants": len(plants),
            "wmape_pct": 100 * absolute_error / target_quantity,
            "error_share_defined": absolute_error > 0,
            "top_error_shares_pct": {
                str(n): 100 * math.fsum(r["absolute_quantity_error"] for r in records[:n]) / absolute_error
                if absolute_error else None for n in (1, 2, 5, 10)
            },
            "top_plants": records[:10],
        }
    return {
        "training_year": training_year,
        "target_year": target_year,
        "status": "post_hoc_descriptive_only",
        "exclusions_applied": False,
        "signals": signals,
    }
