# Motorul energie netă/EROI

`net_energy.py` este copia auditabilă a motorului energetic experimental din
versiunea 0.5. În versiunea 0.6, seriile sale nu mai apar în selector deoarece
modulul nu este încă legat înapoi de ecuațiile BAU Hibrid 2026. Codul rămâne
disponibil pentru etapa viitoare de cuplare și recalibrare.

Regenerare din surse, într-un mediu cu NumPy, pandas și Matplotlib:

```bash
PYTHONPATH=. python3 scripts/generate_net_energy.py
```

Generatorul păstrează explicit starea `scenario_only_not_empirically_calibrated`.
Fișierele nu trebuie prezentate ca observații sau intervale probabilistice.
