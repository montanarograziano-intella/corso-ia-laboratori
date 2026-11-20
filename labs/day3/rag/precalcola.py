"""Calcola le risposte di riserva del notebook, per quando in aula manca il modello o la rete.

Uso: uv run precalcola.py, con il modello scritto in `.env` (il file vince sulle variabili già impostate).

Per le quattro domande della parte 3 scrive la risposta con i primi cinque passi della ricerca ibrida («rag»); per
due di loro anche quella con tutto il fascicolo nel prompt («tutto»). Il file dice con quale modello e quando sono state calcolate.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
from datetime import date

from rag import Indice
import risposte
from risposte import PRECALCOLATE, QUI, leggi_env, rispondi

DOMANDE_DELLA_PARTE_3 = ("1", "12", "13", "15")
CON_TUTTO_IL_FASCICOLO = ("12", "13")  # le due che il notebook rifà senza ricerca


async def main() -> None:
    leggi_env()
    risposte.ATTESA_MASSIMA = 600  # qui nessuno aspetta: un modello locale lento deve poter finire
    modello = os.environ["LAB_MODEL"]
    indice = Indice()
    with (QUI / "banco.csv").open(encoding="utf-8") as file:
        banco = {d["n"]: d for d in csv.DictReader(file)}
    calcolate = {}
    for numero in DOMANDE_DELLA_PARTE_3:
        domanda = banco[numero]["domanda"]
        calcolate[numero] = {"domanda": domanda, "rag": await rispondi(domanda, indice.cerca(domanda, "ibrida", 5), modello)}
        if numero in CON_TUTTO_IL_FASCICOLO:
            calcolate[numero]["tutto"] = await rispondi(domanda, indice.passi, modello)
        print(numero, domanda, calcolate[numero], flush=True)
    contenuto = {"modello": modello, "data": date.today().isoformat(), "risposte": calcolate}
    PRECALCOLATE.write_text(json.dumps(contenuto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
