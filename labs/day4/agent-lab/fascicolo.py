"""Legge il fascicolo da una cartella e lo cerca per parole chiave.

L'identificativo di un documento è il prefisso del nome del file (DOC-07). Ogni riga conserva il suo numero,
perché le fonti si citano come "DOC-07, riga 12". I documenti HTML sono ridotti al loro testo, compreso quello
nascosto: è ciò che legge un agente.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

TIPOGRAFICI = str.maketrans({**dict.fromkeys("\u2010\u2011\u2012\u2013\u2212", "-"), **dict.fromkeys("\u00a0\u2009\u202f", " ")})


def testo_semplice(testo: str) -> str:
    """Models write DOC‑05 and «3 marzo» with typographic hyphens and narrow spaces: make them plain before matching."""
    return testo.translate(TIPOGRAFICI)


# Una data come 03/03/2025, 2025-03-03, 3 marzo oppure 3 mar: i modelli scrivono spesso il mese abbreviato.
DATA = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2} (?:gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)[a-z]*)\b", re.IGNORECASE)


FONTE_CON_RIGA = re.compile(r"DOC-\d+\W{0,3}rig")


def eventi(testo: str) -> list[str]:
    """Gli eventi di una cronologia, una stringa ciascuno: una riga con una data, più la riga subito sotto se
    porta la fonte.

    I modelli mettono la fonte sulla riga dell'evento o su quella sotto, nella forma «DOC-07, riga 12»: valgono
    come lo stesso evento. Un elenco finale delle fonti consultate non appartiene a nessun evento.
    """
    blocchi: list[str] = []
    aperto = False  # la riga subito dopo una data può ancora appartenere all'evento
    for riga in testo_semplice(testo).splitlines():
        if DATA.search(riga):
            blocchi.append(riga)
            aperto = True
            continue
        if aperto and FONTE_CON_RIGA.search(riga):
            blocchi[-1] += " " + riga.strip()
        aperto = False
    return blocchi


ID = re.compile(r"^(DOC-\d+)")
WORD = re.compile(r"[a-zà-ù0-9@.:]+", re.IGNORECASE)
STOP = {"il", "lo", "la", "i", "gli", "le", "un", "una", "di", "a", "da", "in", "con", "su", "per", "e", "che", "del", "della", "è", "al"}


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("style", "script", "title"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script", "title") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._skip:
            self.lines.append(text)


@dataclass(frozen=True)
class Documento:
    id: str
    nome: str
    righe: tuple[str, ...]

    def testo_numerato(self) -> str:
        return "\n".join(f"{n}: {riga}" for n, riga in enumerate(self.righe, 1) if riga.strip())


def _leggi(path: Path) -> tuple[str, ...]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        parser = _Text()
        parser.feed(raw)
        return tuple(parser.lines)
    return tuple(raw.splitlines())


def carica(cartella: Path) -> dict[str, Documento]:
    """Carica tutti i file DOC-* della cartella. Dà errore se la cartella non ne contiene."""
    documenti: dict[str, Documento] = {}
    for path in sorted(cartella.iterdir()):
        m = ID.match(path.name)
        if m and path.is_file():
            documenti[m.group(1)] = Documento(m.group(1), path.name, _leggi(path))
    if not documenti:
        raise FileNotFoundError(f"nessun documento DOC-* in {cartella}")
    return documenti


def cerca(documenti: dict[str, Documento], domanda: str, massimo: int = 6) -> list[tuple[str, int, str]]:
    """Restituisce fino a `massimo` righe come (identificativo, numero di riga, testo), prima quelle più pertinenti."""
    parole = {p.lower() for p in WORD.findall(domanda)} - STOP
    trovati: list[tuple[int, str, int, str]] = []
    for doc in documenti.values():
        for n, riga in enumerate(doc.righe, 1):
            punti = len(parole & {p.lower() for p in WORD.findall(riga)})
            if punti:
                trovati.append((punti, doc.id, n, riga))
    trovati.sort(key=lambda t: (-t[0], t[1], t[2]))
    return [(doc_id, n, riga) for _, doc_id, n, riga in trovati[:massimo]]
