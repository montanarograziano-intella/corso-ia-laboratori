"""Prova il banco di domande con le tre ricerche: per parole chiave (BM25), vettoriale e ibrida.

Uso: uv run prova_banco.py [--k 5]

Per ogni domanda dice se il chunk atteso è tra i primi k risultati di ciascuna ricerca, e stampa la tabella per
tipo di domanda. La domanda senza risposta resta fuori dalla tabella.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from rag import Archivio, trovato

QUI = Path(__file__).resolve().parent
MODI = ("parole", "vettori", "ibrida")


def tabella(archivio: Archivio, k: int = 5) -> tuple[list[dict], dict[str, dict[str, int]]]:
    """Per ogni domanda del banco, l'esito delle tre ricerche; e i conteggi per tipo di domanda."""
    with (QUI / "banco.csv").open(encoding="utf-8") as file:
        domande = list(csv.DictReader(file))
    esiti, conteggi = [], defaultdict(lambda: defaultdict(int))
    for d in domande:
        primi = {modo: [riferimento for riferimento, _ in archivio.cerca(d["domanda"], modo, k)] for modo in MODI}
        if not d["chunk_attesi"]:
            esiti.append({**d, "primi": primi})
            continue
        esito = {modo: trovato(d["chunk_attesi"], primi[modo]) for modo in MODI}
        conteggi[d["tipo"]]["domande"] += 1
        for modo in MODI:
            conteggi[d["tipo"]][modo] += esito[modo]
        esiti.append({**d, **esito, "primi": primi})
    return esiti, conteggi


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=5)
    k = parser.parse_args().k
    archivio = Archivio()
    esiti, conteggi = tabella(archivio, k)
    print(f"{len(archivio.chunk)} chunk, primi {k} risultati\n n  tipo             parole  vettori  ibrida")
    for e in esiti:
        if not e["chunk_attesi"]:
            print(f"{e['n']:>2}  {e['tipo']:<16} fuori tabella; l'ibrida trova {', '.join(e['primi']['ibrida'])}")
        else:
            print(f"{e['n']:>2}  {e['tipo']:<16} " + "  ".join(f"{'sì' if e[m] else 'no':<6}" for m in MODI))
    print("\ntipo             domande  parole  vettori  ibrida")
    for tipo, c in conteggi.items():
        print(f"{tipo:<16} {c['domande']:>7}  {c['parole']:>6}  {c['vettori']:>7}  {c['ibrida']:>6}")


if __name__ == "__main__":
    main()
