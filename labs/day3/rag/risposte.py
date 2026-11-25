"""La parte «risposta» del notebook RAG: i chunk trovati vanno a un LLM, che risponde citando le fonti.

Il modello è una stringa di Pydantic AI presa da `LAB_MODEL` nel file `.env`, come nel laboratorio del giorno 4:
`anthropic:...`, `openai:...` oppure `ollama:...` per un modello sul portatile. Senza modello, o se la chiamata
fallisce, il notebook usa le risposte già calcolate in `risposte_precalcolate.json`.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

QUI = Path(__file__).resolve().parent
PRECALCOLATE = QUI / "risposte_precalcolate.json"
ATTESA_MASSIMA = 180  # secondi: oltre, in aula si passa alla risposta già calcolata

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

ISTRUZIONI = """Rispondi alla domanda usando solo i chunk qui sotto, che vengono da un fascicolo.
Ogni affermazione porta la sua fonte tra parentesi quadre, nella forma [DOC-05, riga 6].
Se due chunk dicono cose diverse, riportale tutte e due con le loro fonti e dì che non coincidono.
Se i chunk non bastano a rispondere, scrivi che il fascicolo non lo dice: non completare con ciò che sembra probabile.
Rispondi in italiano, in poche righe."""


def leggi_env(file: Path = QUI / ".env") -> None:
    """Carica le righe `NOME=valore` del file `.env`, se c'è. Il file vince su ciò che è già impostato.

    Così chi corregge `.env` e riesegue la cella vede il valore nuovo, senza riavviare il notebook.
    """
    if not file.exists():
        return
    for riga in file.read_text(
        encoding="utf-8-sig"
    ).splitlines():  # utf-8-sig: il Blocco note di Windows aggiunge un BOM
        nome, separatore, valore = riga.strip().partition("=")
        if separatore and nome and not nome.startswith("#"):
            os.environ[nome.strip()] = valore.strip().strip("\"'")


def costruisci_prompt(domanda: str, chunk: list[tuple[str, str]]) -> str:
    """Il testo che il modello riceve, in tre blocchi separati da una riga vuota.

    1. Le istruzioni (ISTRUZIONI, qui sopra): usare solo i chunk, citare la fonte, dire quando il fascicolo non basta.
    2. I chunk trovati dalla ricerca, uno per riga, ciascuno preceduto dalla sua fonte:
           [DOC-05, riga 8] 05/03/2025,Bonifico,"-1.500,00",IT87 D999 ...
    3. La domanda.

    `chunk` è la lista di coppie (riferimento, testo) che restituisce la ricerca, per esempio ("DOC-05:8", "05/03/...").
    """
    # Blocco 2: ogni chunk diventa una riga. Il riferimento "DOC-05:8" si scrive "[DOC-05, riga 8]",
    # la stessa forma che le istruzioni chiedono al modello di usare quando cita una fonte.
    righe_dei_chunk = []
    for riferimento, testo in chunk:
        documento, riga = riferimento.split(":")
        righe_dei_chunk.append(f"[{documento}, riga {riga}] {testo}")
    elenco_dei_chunk = "\n".join(righe_dei_chunk)

    # I tre blocchi, uno dopo l'altro.
    return ISTRUZIONI + "\n\nChunk:\n" + elenco_dei_chunk + "\n\nDomanda: " + domanda


async def rispondi(domanda: str, chunk: list[tuple[str, str]], modello: str | None = None) -> str:
    """La risposta del modello alla domanda, dati i chunk.

    Solleva un errore se manca il modello, se la chiamata fallisce o se dura più di `ATTESA_MASSIMA` secondi.
    """
    from pydantic_ai import Agent

    modello = modello or os.environ.get("LAB_MODEL")
    if not modello:
        raise RuntimeError("manca LAB_MODEL: scriverlo nel file .env, oppure usare le risposte già calcolate")
    if modello.startswith("ollama:"):
        os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    try:
        esito = await asyncio.wait_for(Agent(modello).run(costruisci_prompt(domanda, chunk)), ATTESA_MASSIMA)
    except TimeoutError:
        raise RuntimeError(f"il modello non ha risposto in {ATTESA_MASSIMA} secondi") from None
    return esito.output.strip()


def risposta_precalcolata(numero: str, variante: str) -> tuple[str, str]:
    """La risposta già calcolata per la domanda `numero` del golden dataset, variante «rag» o «tutto», e da dove viene."""
    riserva = json.loads(PRECALCOLATE.read_text(encoding="utf-8"))
    origine = f"calcolata il {riserva['data']} con {riserva['modello']}"
    risposta = riserva["risposte"].get(numero, {}).get(variante)
    return risposta or "Per questa domanda non c'è una risposta già calcolata.", origine
