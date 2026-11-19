"""L'agente, costruito da una funzione vuota. Si scrive qui, un passo alla volta: A, B, C.

Si avvia con `uv run --env-file .env esegui.py costruzione pulita`. Se un passo non funziona, copiare passo-a.py,
passo-b.py o passo-c.py su questo file e ripartire da lì. Dopo il passo C il laboratorio continua in
starter/agente.py, che contiene lo stesso agente e i segnaposto dei compiti da 1 a 6.
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
    raise NotImplementedError("passo A, creare l'agente in costruzione/agente.py")
