"""I tre strumenti da cui parte ogni gruppo. Sono funzioni normali: è il file dell'agente a decidere come esporle.

`invia_email` non invia mai nulla: scrive un file nella cartella della posta in uscita.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fascicolo import Documento, cerca
from traccia import Traccia


@dataclass
class Contesto:
    documenti: dict[str, Documento]
    posta_in_uscita: Path
    traccia: Traccia


def cerca_nel_fascicolo(contesto: Contesto, domanda: str) -> str:
    righe = cerca(contesto.documenti, domanda)
    return "\n".join(f"[{doc}, riga {n}] {testo}" for doc, n, testo in righe) or "nessun risultato"


def leggi_documento(contesto: Contesto, id_documento: str) -> str:
    doc = contesto.documenti.get(id_documento.strip().upper())
    return doc.testo_numerato() if doc else f"documento non trovato: {id_documento}"


def invia_email(contesto: Contesto, destinatario: str, oggetto: str, testo: str, allegati: list[str]) -> str:
    contesto.posta_in_uscita.mkdir(parents=True, exist_ok=True)
    numero = len(list(contesto.posta_in_uscita.glob("*.txt"))) + 1
    file = contesto.posta_in_uscita / f"email-{numero:02d}.txt"
    file.write_text(
        f"A: {destinatario}\nOggetto: {oggetto}\nAllegati: {', '.join(allegati) or 'nessuno'}\n\n{testo}\n",
        encoding="utf-8",
    )
    return f"email scritta nella posta in uscita: {file.name}"
