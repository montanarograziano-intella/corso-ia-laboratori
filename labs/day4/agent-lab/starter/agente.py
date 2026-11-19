"""Il vostro agente, dopo la costruzione guidata. Completare i punti marcati DA FARE, in ordine.

Si avvia con `uv run --env-file .env esegui.py starter pulita`.
Parte 1 (30 minuti): compiti da 1 a 3. Parte 2 (70 minuti): compiti da 4 a 6.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent, DeferredToolRequests, RunContext  # noqa: E402
from pydantic_ai.models import Model  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

import strumenti  # noqa: E402
from strumenti import Contesto  # noqa: E402

ISTRUZIONI = """Sei un assistente che aiuta un investigatore di polizia giudiziaria a lavorare su un fascicolo.
Prima di rispondere leggi tutti i documenti, da DOC-01 a DOC-11, uno per uno. Nella cronologia ogni evento sta su una riga che comincia con la data
e finisce con la fonte, nella forma [DOC-07, riga 12]. Se un dato non è nei documenti, scrivi "non indicato".
Per inviare un'email usa sempre lo strumento invia_email: non scrivere l'email nella risposta.
Rispondi in italiano."""


def crea_agente(modello: Model | str) -> Agent[Contesto, str | DeferredToolRequests]:
    agente: Agent[Contesto, str | DeferredToolRequests] = Agent(modello, deps_type=Contesto, output_type=[str, DeferredToolRequests], instructions=ISTRUZIONI)

    @agente.tool
    def cerca_nel_fascicolo(ctx: RunContext[Contesto], domanda: str) -> str:
        """Cerca nei documenti del fascicolo e restituisce le righe pertinenti con documento e numero di riga."""
        return strumenti.cerca_nel_fascicolo(ctx.deps, domanda)

    @agente.tool
    def leggi_documento(ctx: RunContext[Contesto], id_documento: str) -> str:
        """Legge un documento intero, con i numeri di riga. Identificativi da DOC-01 a DOC-11."""
        return strumenti.leggi_documento(ctx.deps, id_documento)

    @agente.tool
    def invia_email(ctx: RunContext[Contesto], destinatario: str, oggetto: str, testo: str, allegati: list[str]) -> str:
        """Invia un'email. `allegati` è l'elenco degli identificativi dei documenti da allegare; può essere vuoto."""
        # DA FARE 5 (parte 2): questo strumento deve richiedere l'approvazione di una persona prima di partire.
        return strumenti.invia_email(ctx.deps, destinatario, oggetto, testo, allegati)

    # DA FARE 2 (parte 1): aggiungere uno strumento `leggi_movimenti` che legge la tabella dei movimenti bancari
    # (DOC-05) tra due date. Scrivere nome, descrizione e parametri: è ciò che il modello legge per sceglierlo.
    # Ogni movimento restituito deve portare la riga di origine, nella forma [DOC-05, riga 6].

    return agente


def esegui(modello: Model | str, contesto: Contesto, richiesta: str, chiedi_alla_persona) -> str:
    """Porta l'agente fino in fondo e restituisce la sua risposta."""
    agente = crea_agente(modello)

    # DA FARE 1 (parte 1): fissare un limite di passi con UsageLimits e passarlo a run_sync.
    limiti: UsageLimits | None = None
    if limiti is None:
        raise NotImplementedError("compito 1, il limite di passi in starter/agente.py")

    risultato = agente.run_sync(richiesta, deps=contesto, usage_limits=limiti)

    # DA FARE 3 (parte 1): confrontare la cronologia inviata con quella di riferimento. Nessun codice da scrivere:
    # `uv run confronta.py <file dell'email>`; il file è indicato alla fine dell'esecuzione.

    # DA FARE 4 (parte 2): un gate tipizzato sulla bozza di email. Una decisione con tre esiti (procedi, chiedi,
    # ferma), una confidenza e le fonti; regole in codice per le fonti inesistenti e per il destinatario.
    # DA FARE 5 (parte 2): quando risultato.output è un DeferredToolRequests, mostrare la chiamata con
    # chiedi_alla_persona(chiamata, decisione) e riprendere l'esecuzione con la risposta. Due attenzioni:
    # riprendere con usage=risultato.usage, altrimenti il limite di passi riparte da zero a ogni ripresa;
    # un destinatario cambiato dalla persona va ricontrollato con l'elenco del gate prima di inviare.
    # DA FARE 6 (parte 2): scrivere ogni passo nella traccia con contesto.traccia.scrivi(...).

    return str(risultato.output)
