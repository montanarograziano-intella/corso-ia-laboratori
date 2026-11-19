"""Passo C: gli altri due strumenti. L'agente può cercare nel fascicolo e inviare un'email.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent, RunContext  # noqa: E402, F401
from pydantic_ai.models import Model  # noqa: E402

import strumenti  # noqa: E402, F401
from strumenti import Contesto  # noqa: E402

ISTRUZIONI = """Sei un assistente che aiuta un investigatore di polizia giudiziaria a lavorare su un fascicolo.
Prima di rispondere leggi tutti i documenti, da DOC-01 a DOC-11, uno per uno. Nella cronologia ogni evento sta su una riga che comincia con la data
e finisce con la fonte, nella forma [DOC-07, riga 12]. Se un dato non è nei documenti, scrivi "non indicato".
Per inviare un'email usa sempre lo strumento invia_email: non scrivere l'email nella risposta.
Rispondi in italiano."""


def esegui(modello: Model | str, contesto: Contesto, richiesta: str, chiedi_alla_persona) -> str:
    """Porta l'agente fino in fondo e restituisce la sua risposta."""
    agente = Agent(modello, deps_type=Contesto, instructions=ISTRUZIONI)

    @agente.tool
    def leggi_documento(ctx: RunContext[Contesto], id_documento: str) -> str:
        """Legge un documento intero, con i numeri di riga. Identificativi da DOC-01 a DOC-11."""
        return strumenti.leggi_documento(ctx.deps, id_documento)

    @agente.tool
    def cerca_nel_fascicolo(ctx: RunContext[Contesto], domanda: str) -> str:
        """Cerca nei documenti del fascicolo e restituisce le righe pertinenti con documento e numero di riga."""
        return strumenti.cerca_nel_fascicolo(ctx.deps, domanda)

    @agente.tool
    def invia_email(ctx: RunContext[Contesto], destinatario: str, oggetto: str, testo: str, allegati: list[str]) -> str:
        """Invia un'email. `allegati` è l'elenco degli identificativi dei documenti da allegare; può essere vuoto."""
        return strumenti.invia_email(ctx.deps, destinatario, oggetto, testo, allegati)

    risultato = agente.run_sync(richiesta, deps=contesto)
    return str(risultato.output)
