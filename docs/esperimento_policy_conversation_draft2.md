# Esperimento di policy contestuale `conversation-draft-2`

Stato: esperimento di sviluppo, 2 ottobre 2026. Non costituisce una policy
approvata né una certificazione di anonimizzazione.

## Perimetro

Il modello riceve l'intera conversazione e le detection già prodotte. Restituisce
una decisione per ogni `detection_id`: `KEEP`, `MASK`, `GENERALIZE` o `REVIEW`.
Non riceve le ipotesi attese e non produce una valutazione complessiva del rischio
residuo della conversazione.

Il contratto distingue:

- `MASK`: placeholder neutro coerente con il tipo, per esempio `[PERSON_1]`;
- `GENERALIZE`: formulazione meno specifica che conserva il ruolo utile;
- `KEEP` e `REVIEW`: nessun replacement.

## Risultati del lotto

Il lotto comprende 46 conversazioni valide e 202 decisioni:

| Azione prodotta | Numero |
|---|---:|
| KEEP | 111 |
| MASK | 83 |
| GENERALIZE | 8 |
| REVIEW | 0 |

Confronto con le ipotesi separate:

| Stato dell'ipotesi | Concordi | Discordi |
|---|---:|---:|
| APPROVED | 160 | 0 |
| PROVISIONAL | 16 | 0 |
| OPEN | 8 | 18 |

Le discordie non sono conteggiate come errori: riguardano soltanto ipotesi
`OPEN`. Tutte si concentrano sulle denominazioni delle organizzazioni nello
scenario di acquisizione societaria. In una conversazione il modello sceglie
`GENERALIZE`; nelle altre tre sceglie `MASK` con placeholder neutri.

## Interpretazione

Le convenzioni approvate sono rispettate nell'intero lotto. La variabilità fra
`MASK` e `GENERALIZE` per le organizzazioni mostra invece una scelta non stabile
che richiede una decisione di policy condivisa con il management. Il risultato
non va usato per trasformare automaticamente le ipotesi `OPEN` in gold.

## Passi non implementati

Non sono ancora implementati:

1. un valutatore quantitativo dedicato alla policy;
2. la valutazione complessiva del rischio residuo della conversazione dopo le
   trasformazioni proposte;
3. la sostituzione finale deterministica;
4. la valutazione del rischio sull'intero dataset, che resta fuori perimetro.
