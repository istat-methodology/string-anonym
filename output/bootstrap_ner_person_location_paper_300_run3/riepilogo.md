# Bootstrap appaiato per conversazione — run 3

Repliche: 10000; seed: 20261014; IC: 95% percentile; conversazioni: 289.

| Modello | F1 micro (IC) | F1 PERSON (IC) | F1 LOCATION (IC) | Indirizzi completi (IC) | Copertura caratteri (IC) |
| --- | ---: | ---: | ---: | ---: | ---: |
| gliner_multi | 0.619 [0.560, 0.673] | 0.397 [0.330, 0.467] | 0.817 [0.763, 0.865] | 0.968 [0.928, 1.000] | 0.983 [0.962, 1.000] |
| gliner_pii | 0.278 [0.234, 0.321] | 0.342 [0.284, 0.404] | 0.213 [0.147, 0.284] | 0.984 [0.960, 1.000] | 0.986 [0.965, 1.000] |
| wikineural | 0.649 [0.600, 0.696] | 0.763 [0.689, 0.833] | 0.599 [0.540, 0.656] | 0.129 [0.055, 0.217] | 0.792 [0.736, 0.842] |
| piiranha | 0.876 [0.833, 0.918] | 0.911 [0.857, 0.959] | 0.862 [0.806, 0.914] | 0.742 [0.628, 0.846] | 0.915 [0.869, 0.955] |

Gli intervalli descrivono la variabilità di campionamento condizionata al corpus sintetico e al suo disegno di generazione; non misurano la generalizzazione al traffico reale.
