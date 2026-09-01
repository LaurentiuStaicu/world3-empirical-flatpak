"""Conservative EROI coupling for the official World3-03 model.

World3 already diverts a fraction of industrial capital to resource
acquisition.  Adding an independent EROI penalty on top of that fraction would
double count part of the same physical burden.  This extension therefore uses
the larger of the original World3 allocation and an EROI-derived allocation.
The latter is exactly equal to the World3 floor at the 2025 coupling boundary.

The module is intended for structural sensitivity tests.  EROI parameters are
priors with heterogeneous empirical support, not a homogeneous observed global
time series and not probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class EROICouplingParameters:
    coupling_start_year: float = 2025.0
    original_capital_burden_floor: float = 0.05
    coupling_strength: float = 1.0
    resource_fraction_reference: float = 0.65
    # EI Statistical Review 2026, Total World gross primary energy, 2025.
    fossil_share_initial: float = 0.8623843748
    fossil_share_long_run: float = 0.30
    fossil_transition_midpoint: float = 2045.0
    fossil_transition_width: float = 11.0
    # Persistence of the latest observed final-stage value (2020), which won
    # the five-year multi-origin backtest. Primary/useful EROI are not mixed.
    fossil_eroi_initial: float = 8.4694506689
    fossil_eroi_floor: float = 4.0
    fossil_quality_elasticity: float = 1.35
    renewable_eroi_initial: float = 10.0
    renewable_eroi_ceiling: float = 18.0
    renewable_learning_rate: float = 0.030
    integration_burden_max: float = 0.32

    def validate(self) -> None:
        if not 1900 <= self.coupling_start_year <= 2100:
            raise ValueError("coupling_start_year must lie inside World3")
        if not 0 <= self.original_capital_burden_floor < 1:
            raise ValueError("capital burden floor must be in [0, 1)")
        if not 0 <= self.coupling_strength <= 3:
            raise ValueError("coupling_strength must be in [0, 3]")
        if not 0 < self.resource_fraction_reference <= 3.5:
            raise ValueError("resource_fraction_reference must be positive")
        if not 0 <= self.fossil_share_long_run <= 1:
            raise ValueError("long-run fossil share must be in [0, 1]")
        if not 0 < self.fossil_share_initial <= 1:
            raise ValueError("initial fossil share must be in (0, 1]")
        if self.fossil_transition_width <= 0:
            raise ValueError("transition width must be positive")
        if self.fossil_eroi_floor <= 1 or self.fossil_eroi_initial <= self.fossil_eroi_floor:
            raise ValueError("fossil EROI bounds are invalid")
        if self.renewable_eroi_initial <= 1 or self.renewable_eroi_ceiling < self.renewable_eroi_initial:
            raise ValueError("renewable EROI bounds are invalid")

    def model_parameters(self) -> dict[str, float]:
        self.validate()
        return {
            "energy coupling start year": self.coupling_start_year,
            "energy original capital burden floor": self.original_capital_burden_floor,
            "energy coupling strength": self.coupling_strength,
            "energy resource fraction reference": self.resource_fraction_reference,
            "energy fossil share initial": self.fossil_share_initial,
            "energy fossil share long run": self.fossil_share_long_run,
            "energy fossil transition midpoint": self.fossil_transition_midpoint,
            "energy fossil transition width": self.fossil_transition_width,
            "energy fossil eroi initial": self.fossil_eroi_initial,
            "energy fossil eroi floor": self.fossil_eroi_floor,
            "energy fossil quality elasticity": self.fossil_quality_elasticity,
            "energy renewable eroi initial": self.renewable_eroi_initial,
            "energy renewable eroi ceiling": self.renewable_eroi_ceiling,
            "energy renewable learning rate": self.renewable_learning_rate,
            "energy integration burden max": self.integration_burden_max,
        }


EROI_SCENARIOS: dict[str, EROICouplingParameters] = {
    "uncoupled": EROICouplingParameters(coupling_strength=0.0),
    "conservative_central": EROICouplingParameters(),
    "accelerated_transition": replace(
        EROICouplingParameters(),
        fossil_share_long_run=0.15,
        fossil_transition_midpoint=2038.0,
        fossil_transition_width=8.0,
        renewable_eroi_ceiling=21.0,
        integration_burden_max=0.24,
    ),
    "fossil_lock_in_stress": replace(
        EROICouplingParameters(),
        fossil_share_long_run=0.55,
        fossil_transition_midpoint=2055.0,
        fossil_eroi_floor=3.0,
        fossil_quality_elasticity=1.7,
        renewable_eroi_ceiling=15.0,
        integration_burden_max=0.38,
    ),
}


_ORIGINAL_ALLOCATION = """fraction of industrial capital allocated to obtaining resources  = 
        IF THEN ELSE ( Time 
                  >= fraction of industrial capital allocated to obtaining resources switch time s\\
\t\t , 
             fraction of capital allocated to obtaining resources 2 , 
             fraction of capital allocated to obtaining resources 1 )
\t~\tDmnl
\t~\t  FRACTION OF CAPITAL ALLOCATED TO OBTAINING RESOURCES
\t\t         (FCAOR#134).
\t|"""

_COUPLED_ALLOCATION = """world3 fraction of industrial capital allocated to obtaining resources =
        IF THEN ELSE ( Time
                  >= fraction of industrial capital allocated to obtaining resources switch time s\\
\t\t ,
             fraction of capital allocated to obtaining resources 2 ,
             fraction of capital allocated to obtaining resources 1 )
\t~\tDmnl
\t~\tOriginal World3 resource-acquisition capital allocation.
\t|

fraction of industrial capital allocated to obtaining resources =
        IF THEN ELSE ( Time < energy coupling start year ,
             world3 fraction of industrial capital allocated to obtaining resources ,
             MAX ( world3 fraction of industrial capital allocated to obtaining resources ,
                   energy capital burden ) )
\t~\tDmnl
\t~\tConservative EROI coupling: take the larger burden to avoid double counting.
\t|"""

_ENERGY_EQUATIONS = r"""

energy coupling start year = 2025
    ~ year
    ~ Boundary between empirical initialization and EROI sensitivity.
    |

energy original capital burden floor = 0.05
    ~ Dmnl
    ~ Scenario-2 resource capital burden at the coupling boundary.
    |

energy coupling strength = 1
    ~ Dmnl
    ~ Translation from incremental energy reinvestment to capital allocation.
    |

energy resource fraction reference = 0.65
    ~ Dmnl
    ~ Candidate-specific World3 fraction of resources remaining at the boundary.
    |

energy fossil share initial = 0.8623843748
    ~ Dmnl
    ~ Observed 2025 fossil share in gross primary energy (EI 2026).
    |

energy fossil share long run = 0.3
    ~ Dmnl
    ~ Long-run fossil share structural assumption.
    |

energy fossil transition midpoint = 2045
    ~ year
    ~ Midpoint of the energy-mix transition.
    |

energy fossil transition width = 11
    ~ year
    ~ Width of the energy-mix transition.
    |

energy transition raw = 1 / ( 1 + EXP ( - ( Time - energy fossil transition midpoint ) / energy fossil transition width ) )
    ~ Dmnl
    ~ Logistic transition before boundary normalization.
    |

energy transition initial = 1 / ( 1 + EXP ( - ( energy coupling start year - energy fossil transition midpoint ) / energy fossil transition width ) )
    ~ Dmnl
    ~ Logistic value at the coupling boundary.
    |

energy transition progress = IF THEN ELSE ( Time < energy coupling start year , 0 ,
    MIN ( 1 , MAX ( 0 , ( energy transition raw - energy transition initial ) / ( 1 - energy transition initial ) ) ) )
    ~ Dmnl
    ~ Transition normalized to exactly zero at the coupling boundary.
    |

energy fossil share = energy fossil share initial +
    ( energy fossil share long run - energy fossil share initial ) * energy transition progress
    ~ Dmnl
    ~ Fossil share in gross primary energy.
    |

energy renewable share = 1 - energy fossil share
    ~ Dmnl
    ~ Non-fossil share in gross primary energy.
    |

energy fossil eroi initial = 8.4694506689
    ~ Dmnl
    ~ Latest observed final-stage fossil EROI, held to 2025 by persistence.
    |

energy fossil eroi floor = 4
    ~ Dmnl
    ~ Fossil EROI lower structural bound.
    |

energy fossil quality elasticity = 1.35
    ~ Dmnl
    ~ Sensitivity of fossil EROI to World3 resource quality.
    |

energy fossil quality ratio = MIN ( 1 , MAX ( 0.001 , fraction of resources remaining / energy resource fraction reference ) )
    ~ Dmnl
    ~ Resource-quality proxy normalized at the coupling boundary.
    |

energy fossil eroi = energy fossil eroi floor +
    ( energy fossil eroi initial - energy fossil eroi floor ) * energy fossil quality ratio ^ energy fossil quality elasticity
    ~ Dmnl
    ~ Unvalidated scenario link between final-stage EROI and World3 resource quality.
    |

energy renewable eroi initial = 10
    ~ Dmnl
    ~ Renewable-system EROI prior at the coupling boundary.
    |

energy renewable eroi ceiling = 18
    ~ Dmnl
    ~ Renewable-system EROI upper structural bound.
    |

energy renewable learning rate = 0.03
    ~ 1/year
    ~ Renewable EROI learning rate.
    |

energy renewable eroi gross = energy renewable eroi ceiling -
    ( energy renewable eroi ceiling - energy renewable eroi initial ) *
    EXP ( - energy renewable learning rate * MAX ( 0 , Time - energy coupling start year ) )
    ~ Dmnl
    ~ Gross renewable EROI before integration burden.
    |

energy integration burden max = 0.32
    ~ Dmnl
    ~ Maximum quadratic grid and storage burden coefficient.
    |

energy variable share = MAX ( 0 , energy renewable share - ( 1 - energy fossil share initial ) )
    ~ Dmnl
    ~ Incremental non-fossil share above the coupling-boundary mix.
    |

energy integration burden = energy integration burden max * energy variable share ^ 2
    ~ Dmnl
    ~ Quadratic grid, storage and balancing burden.
    |

energy renewable eroi effective = energy renewable eroi gross / ( 1 + energy integration burden )
    ~ Dmnl
    ~ Renewable EROI after system integration.
    |

energy system reinvestment share = energy fossil share / energy fossil eroi +
    energy renewable share / energy renewable eroi effective
    ~ Dmnl
    ~ Harmonic-mixture identity: sum of source share divided by source EROI.
    |

energy system eroi = 1 / energy system reinvestment share
    ~ Dmnl
    ~ System EROI at the declared boundary.
    |

energy reinvestment reference = energy fossil share initial / energy fossil eroi initial +
    ( 1 - energy fossil share initial ) / energy renewable eroi initial
    ~ Dmnl
    ~ Reinvestment share at the coupling boundary.
    |

energy capital burden = energy original capital burden floor + energy coupling strength *
    MAX ( 0 , energy system reinvestment share - energy reinvestment reference )
    ~ Dmnl
    ~ Incremental burden only; improvements do not create an unvalidated bonus.
    |
"""


def coupled_model_text(model_text: str) -> str:
    """Inject the conservative energy feedback before Vensim sketch data."""
    if _ORIGINAL_ALLOCATION not in model_text:
        raise ValueError("World3 resource-capital allocation equation was not found")
    if "energy system eroi" in model_text.lower():
        raise ValueError("Energy coupling appears to be already present")
    result = model_text.replace(_ORIGINAL_ALLOCATION, _COUPLED_ALLOCATION, 1)
    marker = r"\\\---/// Sketch information - do not modify anything except names"
    if marker not in result:
        raise ValueError("Vensim sketch marker was not found")
    return result.replace(marker, _ENERGY_EQUATIONS + "\n" + marker, 1)
