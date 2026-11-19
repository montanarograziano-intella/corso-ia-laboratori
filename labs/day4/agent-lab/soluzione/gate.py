"""Il gate tipizzato della parte 2: una decisione con un insieme chiuso di esiti, controllata da regole in codice.

Il modello propone una `Decisione`. Le regole qui sotto hanno l'ultima parola: una fonte che non esiste ferma la
bozza, un evento senza fonte o una confidenza bassa la mandano a una persona.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from fascicolo import Documento, eventi, testo_semplice

SOGLIA = 0.8
DESTINATARI_AMMESSI = {"procura@esempio.invalid"}
FONTE = re.compile(r"DOC-\d+")


class Decisione(BaseModel):
    esito: Literal["procedi", "chiedi", "ferma"]
    confidenza: float = Field(ge=0, le=1)
    fonti: list[str]
    motivo: str


def applica_regole(decisione: Decisione, destinatario: str, testo: str, documenti: dict[str, Documento]) -> Decisione:
    """La decisione dopo le regole. Le regole possono solo renderla più severa, mai più permissiva."""
    testo = testo_semplice(testo)
    citate = set(FONTE.findall(testo))
    inesistenti = sorted(citate - set(documenti))
    senza_fonte = [evento for evento in eventi(testo) if not FONTE.search(evento)]

    def stretta(esito: Literal["chiedi", "ferma"], motivo: str) -> Decisione:
        return decisione.model_copy(update={"esito": esito, "motivo": motivo, "fonti": sorted(citate)})

    if destinatario not in DESTINATARI_AMMESSI:
        return stretta("ferma", f"destinatario non in elenco: {destinatario}")
    if inesistenti:
        return stretta("ferma", f"fonti citate che non esistono nel fascicolo: {', '.join(inesistenti)}")
    if not citate:
        return stretta("ferma", "la bozza non cita nessuna fonte")
    if decisione.esito == "ferma":
        return decisione
    if senza_fonte:
        return stretta("chiedi", f"{len(senza_fonte)} eventi senza fonte")
    if decisione.confidenza < SOGLIA:
        return stretta("chiedi", f"confidenza {decisione.confidenza:.2f} sotto la soglia {SOGLIA}")
    return decisione.model_copy(update={"fonti": sorted(citate)})
