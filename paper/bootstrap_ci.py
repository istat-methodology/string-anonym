"""Bootstrap per conversazione (run3): IC al 95% per exact match e copertura indirizzi.

Uso: python3 bootstrap_ci.py <root_repo_mnt> [B] [seed]
Legge le predizioni congelate della run3; non modifica nulla nella repo.
"""
import json, sys, random
from pathlib import Path

root = Path(sys.argv[1])
B = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 20271
sys.path.insert(0, str(root / "src"))
from esporta_dataset_masking import leggi          # noqa: E402
from valuta_indirizzi import valuta                # noqa: E402

ds = root / "output" / "dataset_detection_paper_300"
run = root / "output" / "confronto_ner_person_location_paper_300_run3"
inputs = leggi(ds / "input.jsonl")
gold_det = leggi(ds / "detections_attese.jsonl")
gold_ner = {r["id"]: r["annotazioni"] for r in leggi(ds / "annotazioni_ner_attese.jsonl")}
ids = [r["id"] for r in inputs]
MODELS = ["gliner_multi", "gliner_pii", "wikineural", "piiranha"]

def key(a):
    return (a["campo"], a["tipo"], a["start"], a["end"])

def counts(pred, gold):
    P = {key(a) for a in pred}; G = {key(a) for a in gold}
    out = {}
    for t in ("PERSON", "LOCATION", "ALL"):
        p = {k for k in P if t == "ALL" or k[1] == t}
        g = {k for k in G if t == "ALL" or k[1] == t}
        out[t] = (len(p & g), len(p - g), len(g - p))
    return out

def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f

def pct(xs):
    xs = sorted(xs); n = len(xs)
    return xs[int(0.025 * n)], xs[int(0.975 * n) - 1]

rng = random.Random(seed)
samples = [[rng.randrange(len(ids)) for _ in ids] for _ in range(B)]
result = {"B": B, "seed": seed, "n_conversations": len(ids), "models": {}}

for m in MODELS:
    preds = {r["id"]: r for r in leggi(run / m / "predizioni.jsonl")}
    per_conv = {i: counts(preds[i]["annotazioni"], gold_ner[i]) for i in ids}
    tot = {t: tuple(sum(per_conv[i][t][k] for i in ids) for k in range(3)) for t in ("ALL", "PERSON", "LOCATION")}
    addr = valuta(inputs, gold_det, list(preds.values()))
    addr_conv = {i: [0, 0, 0.0, 0.0] for i in ids}   # complete, total, covered_frac_sum(not used), unused
    for d in addr["details"]:
        addr_conv[d["id"]][0] += int(d["complete"]); addr_conv[d["id"]][1] += 1
    point = {t: prf(*tot[t]) for t in tot}
    point["addr_complete"] = (addr["full_address"]["complete"], addr["full_address"]["total"])
    boots = {"ALL": [], "PERSON": [], "LOCATION": [], "addr": []}
    for s in samples:
        for t in ("ALL", "PERSON", "LOCATION"):
            tp = sum(per_conv[ids[j]][t][0] for j in s); fp = sum(per_conv[ids[j]][t][1] for j in s); fn = sum(per_conv[ids[j]][t][2] for j in s)
            boots[t].append(prf(tp, fp, fn))
        c = sum(addr_conv[ids[j]][0] for j in s); n = sum(addr_conv[ids[j]][1] for j in s)
        boots["addr"].append(c / n if n else float("nan"))
    res = {"counts": {t: tot[t] for t in tot}, "addr_complete": point["addr_complete"]}
    for t in ("ALL", "PERSON", "LOCATION"):
        res[t] = {}
        for idx, name in enumerate(("precision", "recall", "f1")):
            lo, hi = pct([b[idx] for b in boots[t]])
            res[t][name] = {"point": point[t][idx], "lo": lo, "hi": hi}
    vals = [v for v in boots["addr"] if v == v]
    lo, hi = pct(vals)
    res["addr_complete_rate"] = {"point": point["addr_complete"][0] / point["addr_complete"][1], "lo": lo, "hi": hi}
    result["models"][m] = res
    print(m, "ALL tp/fp/fn", tot["ALL"], "| addr", point["addr_complete"])

Path("bootstrap_ci_run3.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
for m, r in result["models"].items():
    f = lambda x: f'{x["point"]:.3f} [{x["lo"]:.3f}, {x["hi"]:.3f}]'
    print(f"{m:13s} F1 {f(r['ALL']['f1'])} | PERSON F1 {f(r['PERSON']['f1'])} | LOC F1 {f(r['LOCATION']['f1'])} | addr {f(r['addr_complete_rate'])}")
