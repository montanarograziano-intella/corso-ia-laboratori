"""Passo B: il primo strumento. L'agente può leggere un documento del fascicolo.
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

    risultato = agente.run_sync(richiesta, deps=contesto)
    return str(risultato.output)
