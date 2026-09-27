"""Legge i cinque dataset e prepara liste ordinate per il sampling locale."""

import argparse
import csv
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import unicodedata


ROOT = Path(__file__).resolve().parents[1]


def pulisci(value):
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def leggi_lista(path):
    with path.open(encoding="utf-8-sig") as f:
        valori = sorted({pulisci(riga) for riga in f} - {""})
    if not valori:
        raise ValueError(f"Lista vuota: {path.name}")
    return valori


@dataclass
class DatiInput:
    nomi: list[str]
    cognomi: list[str]
    comuni: dict[str, str]
    strade: list[tuple[str, str]]  # codice ISTAT, odonimo; senza civici
    statistiche: dict
    codici_catastali: dict[str, str] = field(default_factory=dict)
    indagini: list[dict] = field(default_factory=list)

    def campiona(self, rng, entita, email_indipendente=False):
        """Campionamento uniforme dalle liste; i civici sono fittizi (1–300)."""
        valori = {}
        if "persona_1" in entita or "email_1" in entita:
            nome = rng.choice(self.nomi).title()
            cognome = rng.choice(self.cognomi).title()
            if "persona_1" in entita:
                valori["persona_1"] = f"{nome} {cognome}"
            if "email_1" in entita and email_indipendente:
                # Recapito sintetico del nuovo contatto, non derivato dal vecchio referente.
                valori["email_1"] = f"contatto.{rng.randrange(100000, 1000000)}@example.org"
            elif "email_1" in entita:
                testo = unicodedata.normalize("NFKD", f"{nome}.{cognome}")
                locale = re.sub(r"[^a-z.]", "", testo.encode("ascii", "ignore").decode().lower())
                valori["email_1"] = f"{locale or 'utente'}@example.org"
        if "indirizzo_1" in entita:
            codice, strada = rng.choice(self.strade)
            valori["indirizzo_1"] = f"{strada.title()} {rng.randint(1, 300)}, {self.comuni[codice]}"
        return valori


def leggi_indagini(path):
    richiesti = {"codice_psn", "nome_indagine", "tipo_rispondente"}
    indagini = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not richiesti <= set(reader.fieldnames or []):
            raise ValueError("Colonne mancanti in codici_psn.csv")
        for numero, row in enumerate(reader, 2):
            row = {k: pulisci(v) for k, v in row.items() if k is not None}
            if any(not row[k] for k in richiesti):
                raise ValueError(f"Valori PSN mancanti alla riga {numero}")
            if row["tipo_rispondente"] not in {"imprese", "famiglie_individui", "altro", "da_verificare"}:
                raise ValueError(f"Tipo rispondente PSN non valido alla riga {numero}")
            codice = row["codice_psn"]
            if codice in indagini and indagini[codice] != row:
                raise ValueError(f"Associazioni PSN discordanti: {codice}")
            indagini[codice] = row
    if not indagini:
        raise ValueError("Catalogo PSN vuoto")
    return [indagini[c] for c in sorted(indagini)]


def carica_input(cartella):
    cartella = Path(cartella)
    nomi = leggi_lista(cartella / "nomi.txt")
    cognomi = leggi_lista(cartella / "cognomi.txt")
    comuni = {}
    catastali = {}
    with (cartella / "codici_comuni.csv").open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        richiesti = {"Codice Comune (alfanumerico)", "Comune", "Codice catasto"}
        if not richiesti <= set(reader.fieldnames or []):
            raise ValueError("Colonne mancanti in codici_comuni.csv")
        for row in reader:
            codice = pulisci(row["Codice Comune (alfanumerico)"])
            comune = pulisci(row["Comune"])
            if not codice or not comune:
                raise ValueError("Comune con codice o denominazione vuota")
            if codice in comuni and comuni[codice] != comune:
                raise ValueError(f"Denominazioni discordanti per il comune {codice}")
            catasto = pulisci(row["Codice catasto"])
            if not re.fullmatch(r"[A-Z][0-9]{3}", catasto):
                raise ValueError(f"Codice catastale assente o non valido: {codice}")
            if codice in catastali and catastali[codice] != catasto:
                raise ValueError(f"Codici catastali discordanti: {codice}")
            comuni[codice] = comune
            catastali[codice] = catasto
    if not comuni:
        raise ValueError("Elenco comuni vuoto")
    strade = set()
    righe = vuote = 0
    sconosciuti = set()
    # Lo stradario compatto è l’unico input per le strade.
    with (cartella / "strade_lazio.csv").open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not {"CODICE_ISTAT", "COMUNE", "ODONIMO"} <= set(reader.fieldnames or []):
            raise ValueError("Colonne mancanti in strade_lazio.csv")
        for row in reader:
            righe += 1
            codice = pulisci(row["CODICE_ISTAT"])
            strada = pulisci(row["ODONIMO"])
            if not strada or not codice or not pulisci(row["COMUNE"]):
                raise ValueError(f"Strada con valori mancanti alla riga {righe + 1}")
            if codice not in comuni:
                sconosciuti.add(codice)
                continue
            if pulisci(row["COMUNE"]) != comuni[codice]:
                raise ValueError(f"Comune discordante nello stradario: {codice}")
            strade.add((codice, strada))
    if sconosciuti:
        raise ValueError(f"Codici degli indirizzi assenti dall'elenco comuni: {sorted(sconosciuti)}")
    if not strade:
        raise ValueError("Nessuna strada valida")
    indagini = leggi_indagini(cartella / "codici_psn.csv")
    return DatiInput(nomi, cognomi, dict(sorted(comuni.items())), sorted(strade), {
        "indagini": len(indagini),
        "nomi": len(nomi), "cognomi": len(cognomi), "comuni": len(comuni),
        "righe_indirizzi": righe, "odonimi_vuoti": vuote,
        "strade_uniche_per_comune": len(strade),
        "duplicati_rimossi": righe - vuote - len(strade),
    }, dict(sorted(catastali.items())), indagini)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    try:
        dati = carica_input(args.data_dir)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(dati.statistiche, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
