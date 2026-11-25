"""Controlli sulla lettura di un'esecuzione dell'agente, senza modello: una traccia e due uscite, e che cosa se ne ricava."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from agente_locale import con_contesto, riassumi  # noqa: F401 (con_contesto: l'importazione non deve chiamare Ollama)

PASSI = [
    {"documenti": ["DOC-01", "DOC-02"]},
    {"strumento": "leggi_documento", "argomenti": {"id_documento": "doc-01"}, "risultato": "1  testo"},
    {
        "strumento": "leggi_documento",
        "argomenti": {"id_documento": "DOC-99"},
        "risultato": "documento non trovato: DOC-99",
    },
]


def test_un_esecuzione_riuscita() -> None:
    r = riassumi(PASSI, "", False, True, "trovato  ...\n\n8 eventi trovati su 19\n")
    assert (r["documenti_letti"], r["documenti"], r["email_inviata"], r["eventi_trovati"], r["eventi"], r["nota"]) == (
        1,
        2,
        True,
        8,
        19,
        "",
    )


def test_senza_email_non_c_e_un_punteggio() -> None:
    r = riassumi(PASSI, "", False, False, "")
    assert r["eventi_trovati"] is None and r["eventi"] is None and "senza inviare" in r["nota"]


def test_tempo_scaduto_e_modello_senza_strumenti() -> None:
    assert riassumi([], "", True, False, "")["nota"] == "tempo scaduto dopo 15 minuti"
    r = riassumi([], "registry.ollama.ai/library/gemma3:4b does not support tools", False, False, "")
    assert r["nota"] == "il modello non supporta gli strumenti" and r["documenti"] == 0 and r["passi"] == 0


def test_un_esecuzione_interrotta_riporta_il_motivo() -> None:
    assert (
        riassumi(PASSI, "Esecuzione interrotta: superato il limite di 25 richieste\n", False, False, "")["nota"]
        == "superato il limite di 25 richieste"
    )


def test_un_punteggio_che_non_si_legge_non_diventa_zero() -> None:
    r = riassumi(PASSI, "", False, True, "formato cambiato")
    assert r["eventi_trovati"] is None and "non si è potuto leggere" in r["nota"]
