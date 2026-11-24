"""Il motore del notebook RAG: i chunk del fascicolo e tre ricerche, per parole chiave, vettoriale e ibrida.

Il corpus sono i dieci documenti di base del fascicolo più i cinque distrattori della cartella `distrattori/`: una
frode simile, con altri nomi, date, importi e IBAN. Un chunk è una riga; nei verbali è una domanda con la sua
risposta, e porta il numero di riga della risposta. «DOC-05:8» è la riga 8 del file di DOC-05.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

QUI = Path(__file__).resolve().parent
FASCICOLO = QUI.parents[2] / "data" / "case-file" / "core"
DISTRATTORI = QUI / "distrattori"
MODELLO = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # multilingue, 1 GB, gira su CPU

# Parole che non distinguono un chunk dall'altro: senza toglierle, «che cosa è stato» pesa più di «10:41».
VUOTE = set(
    "a ad al alla alle allo ai agli che chi con cosa da dal dalla dalle dei del della delle di e è ed ha hanno ho i "
    "il in la le lo l ma nel nella nelle non o per più quale quali quando se si su sua sue suo sul sulla un una uno "
    "sono stata stato stati era come dove gli ne d c all dall dell nell sull".split()
)


def chunk_del_corpus(cartelle: tuple[Path, ...] = (FASCICOLO, DISTRATTORI)) -> list[tuple[str, str]]:
    """Restituisce (riferimento, testo) per ogni chunk dei documenti nelle cartelle."""
    chunk = []
    for cartella in cartelle:  # una cartella mancante darebbe un archivio più piccolo e una tabella sbagliata, in silenzio
        if not cartella.is_dir():
            raise FileNotFoundError(f"manca la cartella {cartella}: il laboratorio va aperto dentro il repository intero")
    for file in sorted(f for cartella in cartelle for f in cartella.glob("DOC-*")):
        documento = re.match(r"DOC-\d+", file.name).group()
        domanda = ""
        for numero, testo in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            testo = testo.strip()
            if numero == 1 or not testo:  # la riga 1 è l'avviso sui dati sintetici
                continue
            if testo.startswith("Domanda:"):  # nei verbali il chunk è la domanda con la sua risposta
                domanda = testo
                continue
            chunk.append((f"{documento}:{numero}", f"{domanda} {testo}".strip()))
            domanda = ""
    return chunk


def parole(testo: str) -> list[str]:
    """Orari, indirizzi IP e numeri con il punto restano interi; il resto si divide in parole e numeri."""
    trovate = re.findall(r"\d{1,3}(?:[:.]\d{1,3})+|[a-zà-ù]+|\d+", testo.lower())
    return [parola for parola in trovate if parola not in VUOTE]


def trovato(attesi: str, primi: list[str]) -> bool:
    """«A|B» chiede uno dei due chunk; «A & B|C» chiede A e anche uno tra B e C."""
    return all(any(chunk.strip() in primi for chunk in gruppo.split("|")) for gruppo in attesi.split("&"))


class Archivio:
    """I chunk, con ciò che serve alle tre ricerche: le parole per BM25 e un vettore per chunk."""

    def __init__(self, chunk: list[tuple[str, str]] | None = None) -> None:
        self.chunk = chunk if chunk is not None else chunk_del_corpus()
        self.riferimenti = [riferimento for riferimento, _ in self.chunk]
        self.testi = [testo for _, testo in self.chunk]
        self.bm25 = BM25Okapi([parole(testo) for testo in self.testi])
        # Il modello resta in questa cartella: la cartella temporanea del sistema viene svuotata tra un giorno e l'altro.
        self.modello = TextEmbedding(MODELLO, cache_dir=str(QUI / ".modelli"))
        self.vettori = self._vettori(self.testi)

    def _vettori(self, testi: list[str]) -> np.ndarray:
        vettori = np.array(list(self.modello.embed(testi)))
        return vettori / np.linalg.norm(vettori, axis=1, keepdims=True)

    def punteggi(self, domanda: str) -> tuple[np.ndarray, np.ndarray]:
        """I punteggi di ogni chunk per la domanda: quello per parole chiave e quello vettoriale."""
        return self.bm25.get_scores(parole(domanda)), self.vettori @ self._vettori([domanda])[0]

    def cerca(self, domanda: str, modo: str = "ibrida", k: int = 5) -> list[tuple[str, str]]:
        """I primi k chunk per la domanda. `modo` è «parole», «vettori» o «ibrida»."""
        per_parole, per_vettori = self.punteggi(domanda)
        indici = range(len(self.chunk))
        # Un chunk senza nessuna parola della domanda non ha un posto nella ricerca per parole: dargliene uno
        # premierebbe l'ordine dei file. Per questo la ricerca per parole può restituire meno di k chunk.
        ordine = {
            "parole": sorted((i for i in indici if per_parole[i] > 0), key=lambda i: -per_parole[i]),
            "vettori": sorted(indici, key=lambda i: -per_vettori[i]),
        }
        if modo == "ibrida":
            posto = {nome: {i: p for p, i in enumerate(lista, 1)} for nome, lista in ordine.items()}

            def fusione(i: int) -> float:
                # Somma dei reciproci dei posti (reciprocal rank fusion, costante 60).
                per_le_parole = 1 / (60 + posto["parole"][i]) if i in posto["parole"] else 0.0
                return per_le_parole + 1 / (60 + posto["vettori"][i])

            ordine["ibrida"] = sorted(indici, key=lambda i: -fusione(i))
        return [self.chunk[i] for i in ordine[modo][:k]]
