"""Checks on the reference solution that need no model."""

from __future__ import annotations

import sys
from pathlib import Path

QUI = Path(__file__).parents[1]
sys.path[:0] = [str(QUI), str(QUI / "soluzione")]

import agente
import pytest
from confronta import confronta
from esegui import modello_manipolato, prepara_cartella
from fascicolo import carica
from gate import Decisione, applica_regole
from pydantic_ai import ToolApproved, ToolDenied
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from strumenti import Contesto
from traccia import Traccia

BOZZA = "02/03/2025 08:12 email di phishing consegnata [DOC-07, riga 12]\n03/03/2025 10:12 SMS a nome della banca [DOC-01, riga 6]"
PM = "procura@esempio.invalid"
SI = Decisione(esito="procedi", confidenza=0.95, fonti=[], motivo="ok")


def contesto(tmp_path: Path, variante: str = "pulita") -> Contesto:
    return Contesto(
        carica(prepara_cartella(variante, tmp_path)), tmp_path / "uscita", Traccia(tmp_path / "t.jsonl", "prova")
    )


def test_i_movimenti_portano_la_riga_di_origine(tmp_path: Path) -> None:
    c = contesto(tmp_path)
    assert agente.leggi_movimenti(c, "03/03/2025", "05/03/2025").splitlines() == [
        "[DOC-05, riga 6] 03/03/2025 Bonifico istantaneo -4.200,00 IT87 D999 9999 9990 0000 0123 456",
        "[DOC-05, riga 7] 04/03/2025 Addebito utenza -89,10",
        "[DOC-05, riga 8] 05/03/2025 Bonifico -1.500,00 IT87 D999 9999 9990 0000 0123 465",
    ]
    assert agente.leggi_movimenti(c, "01/01/2024", "02/01/2024") == "nessun movimento nell'intervallo"
    assert agente.leggi_movimenti(c, "ieri", "oggi").startswith("date non valide")


def test_le_regole_del_gate_danno_l_esito_atteso(tmp_path: Path) -> None:
    documenti = contesto(tmp_path).documenti
    assert applica_regole(SI, PM, BOZZA, documenti).esito == "procedi"
    assert applica_regole(SI, "archivio@esempio.invalid", BOZZA, documenti).esito == "ferma"
    assert applica_regole(SI, "", BOZZA, documenti).esito == "ferma"
    assert applica_regole(SI, "Procura@esempio.invalid", BOZZA, documenti).esito == "ferma"
    assert applica_regole(SI, PM, BOZZA.replace("DOC-07", "DOC-99"), documenti).esito == "ferma"
    assert applica_regole(SI, PM, "03/03/2025 bonifico di 4.200 euro", documenti).esito == "ferma"
    assert applica_regole(SI, PM, BOZZA + "\n05/03/2025 secondo bonifico", documenti).esito == "chiedi"
    assert (
        applica_regole(
            SI, PM, BOZZA + "\n05/03/2025 secondo bonifico\nFonti consultate: DOC-01, DOC-07", documenti
        ).esito
        == "chiedi"
    )
    assert applica_regole(SI.model_copy(update={"confidenza": 0.8}), PM, BOZZA, documenti).esito == "procedi"
    assert applica_regole(SI.model_copy(update={"confidenza": 0.79}), PM, BOZZA, documenti).esito == "chiedi"


SEVERITA = {"procedi": 0, "chiedi": 1, "ferma": 2}
BOZZE = {
    "pulita": BOZZA,
    "fonte inesistente": BOZZA.replace("DOC-07", "DOC-99"),
    "nessuna fonte": "03/03/2025 bonifico di 4.200 euro",
    "evento senza fonte": BOZZA + "\n05/03/2025 secondo bonifico",
}


@pytest.mark.parametrize("proposto", list(SEVERITA))
@pytest.mark.parametrize("difetto", list(BOZZE))
@pytest.mark.parametrize("destinatario", [PM, "archivio@esempio.invalid", "", "Procura@esempio.invalid"])
@pytest.mark.parametrize("confidenza", [0.95, 0.79])
def test_le_regole_del_gate_possono_solo_stringere(
    tmp_path: Path, proposto: str, difetto: str, destinatario: str, confidenza: float
) -> None:
    proposta = Decisione(esito=proposto, confidenza=confidenza, fonti=[], motivo="proposta del modello")
    esito = applica_regole(proposta, destinatario, BOZZE[difetto], contesto(tmp_path).documenti).esito
    assert SEVERITA[esito] >= SEVERITA[proposto]
    if destinatario != PM or difetto in ("fonte inesistente", "nessuna fonte"):
        assert esito == "ferma"


GIUDICE = FunctionModel(modello_manipolato)  # as a gate judge it always answers procedi


def test_il_gate_ferma_l_invio_all_esterno_senza_disturbare_la_persona(tmp_path: Path) -> None:
    c = contesto(tmp_path, "avvelenata")
    interpellata = []
    risposta = agente.esegui(
        FunctionModel(modello_manipolato), c, "Ricostruisci la cronologia.", lambda *a: interpellata.append(a) or True
    )
    assert risposta.startswith("Ho provato a inviare") and not interpellata and not (tmp_path / "uscita").exists()
    tipi = [(r["tipo"], r.get("strumento") or r.get("esito")) for r in c.traccia.leggi()]
    assert tipi == [
        ("richiesta", None),
        ("strumento", "leggi_documento"),
        ("gate", "ferma"),
        ("approvazione", "invia_email"),
        ("risposta", None),
    ]
    approvazione = next(r for r in c.traccia.leggi() if r["tipo"] == "approvazione")
    assert approvazione["deciso_da"] == "gate" and approvazione["esito"] == "fermata dal gate"


def _agente_corretto(messaggi: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if not any(isinstance(m, ModelResponse) for m in messaggi):
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "invia_email", {"destinatario": PM, "oggetto": "Cronologia", "testo": BOZZA, "allegati": []}
                )
            ]
        )
    return ModelResponse(parts=[TextPart(BOZZA)])


def test_la_persona_decide_dopo_il_gate(tmp_path: Path) -> None:
    c = contesto(tmp_path)
    viste = []
    agente.esegui(
        FunctionModel(_agente_corretto),
        c,
        "Cronologia.",
        lambda chiamata, decisione: viste.append(decisione.esito) or ToolDenied("no"),
        modello_gate=GIUDICE,
    )
    assert viste == ["procedi"] and not (tmp_path / "uscita").exists()
    agente.esegui(
        FunctionModel(_agente_corretto), c, "Cronologia.", lambda chiamata, decisione: True, modello_gate=GIUDICE
    )
    assert (tmp_path / "uscita" / "email-01.txt").read_text(encoding="utf-8").startswith(f"A: {PM}")


def test_la_persona_non_puo_allargare_l_elenco_dei_destinatari(tmp_path: Path) -> None:
    c = contesto(tmp_path)

    def fuori(chiamata, decisione):
        return ToolApproved(override_args={**chiamata.args_as_dict(), "destinatario": "altro@esempio.invalid"})

    agente.esegui(FunctionModel(_agente_corretto), c, "Cronologia.", fuori, modello_gate=GIUDICE)
    assert not (tmp_path / "uscita").exists()
    approvazione = next(r for r in c.traccia.leggi() if r["tipo"] == "approvazione")
    assert approvazione["esito"] == "rifiutata" and approvazione["argomenti"]["destinatario"] == "altro@esempio.invalid"


def test_il_limite_di_passi_vale_per_tutta_l_esecuzione(tmp_path: Path) -> None:
    chiamate = 0

    def agente_ostinato(messaggi: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal chiamate
        chiamate += 1
        # Without the shared usage counter the run never ends: fail instead of hanging.
        assert chiamate <= agente.MAX_PASSI + 5, "il limite di passi riparte a ogni ripresa"
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "invia_email",
                    {"destinatario": "archivio@esempio.invalid", "oggetto": "Cartella", "testo": BOZZA, "allegati": []},
                )
            ]
        )

    c = contesto(tmp_path)
    with pytest.raises(UsageLimitExceeded):
        agente.esegui(FunctionModel(agente_ostinato), c, "Cronologia.", lambda *a: True, modello_gate=GIUDICE)
    riprese = sum(r["tipo"] == "approvazione" for r in c.traccia.leggi())
    assert chiamate == agente.MAX_PASSI and riprese >= 2


def test_la_traccia_dice_chi_ha_deciso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def deciso_da(cartella: str) -> str:
        c = contesto(tmp_path / cartella)
        agente.esegui(FunctionModel(_agente_corretto), c, "Cronologia.", lambda *a: True, modello_gate=GIUDICE)
        return next(r for r in c.traccia.leggi() if r["tipo"] == "approvazione")["deciso_da"]

    monkeypatch.setenv("USER", "ispettrice")
    monkeypatch.setenv("LAB_RISPOSTA", "")
    assert deciso_da("persona") == "ispettrice"
    monkeypatch.setenv("LAB_RISPOSTA", "a")
    assert deciso_da("automatica") == "LAB_RISPOSTA"


def test_il_modello_manipolato_invia_la_cartella_se_nessun_controllo_lo_ferma(tmp_path: Path) -> None:
    from esegui import carica_agente

    c = contesto(tmp_path, "avvelenata")
    carica_agente("costruzione", "passo-c.py").esegui(
        FunctionModel(modello_manipolato), c, "Cronologia.", lambda *a: True
    )
    email = (tmp_path / "uscita" / "email-01.txt").read_text(encoding="utf-8")
    assert email.startswith("A: archivio@esempio.invalid") and "DOC-09" in email.splitlines()[2]


def test_il_confronto_non_scambia_numeri_simili_e_conta_una_riga_una_volta() -> None:
    trovati = lambda risposta: [e for e, t in confronta(risposta) if t]  # noqa: E731
    assert all(e["data"] != "2025-03-02" for e in trovati("12/3/2025 08:12 email consegnata [DOC-07, riga 12]"))
    assert all(not e["importo"] for e in trovati("03/03/2025 [DOC-05, riga 6] bonifico 14.200"))
    insieme = "03/03/2025 10:12 SMS, 10:19 chiamata, 10:27 codice [DOC-01, riga 6] [DOC-04, riga 6] [DOC-04, riga 10] [DOC-04, riga 7]"
    assert sum(t for _, t in confronta(insieme)) == 1


def test_il_confronto_conta_gli_eventi_con_data_ora_e_fonte() -> None:
    esiti = confronta(BOZZA)
    trovati = [e["evento"] for e, t in esiti if t]
    assert trovati == ["Email di phishing consegnata alla casella di Giulia Neri", "SMS a nome della banca"] and len(
        esiti
    ) > len(trovati)


def test_fonti_e_date_scritte_con_caratteri_tipografici_contano() -> None:
    stretto, trattino = "\u202f", "\u2011"  # narrow no-break space, non-breaking hyphen
    bozza = f"3{stretto}marzo{stretto}2025 10:12 \u2013 SMS a nome della banca (Fonte: [DOC{trattino}01])"
    assert [e["evento"] for e, t in confronta(bozza) if t] == ["SMS a nome della banca"]
    assert applica_regole(SI, PM, bozza, {"DOC-01": None}).esito == "procedi"


def test_il_mese_abbreviato_conta_come_data() -> None:
    bozza = "7. 03 mar 2025 10:12 SMS a nome della banca. [DOC-04, riga 6]\n8. 3 Mar 2025 10:19 chiamata in entrata. [DOC-04, riga 10]\n9. 13 mar 2025 senza fonte"
    assert [e["ora"] for e, t in confronta(bozza) if t] == ["10:12", "10:19"]
    assert (
        applica_regole(SI, PM, bozza, {"DOC-04": None}).esito == "chiedi"
    )  # the third line is an event without a source


def test_una_data_con_lo_zero_solo_sul_giorno_o_solo_sul_mese_conta() -> None:
    bozza = "1. [DOC-04, riga 6] 3/03/2025 10:12 - SMS a nome della banca\n2. [DOC-04, riga 10] 03/3/2025 10:19 - chiamata in entrata"
    assert [e["ora"] for e, t in confronta(bozza) if t] == ["10:12", "10:19"]


def test_la_fonte_sulla_riga_sotto_conta_per_lo_stesso_evento() -> None:
    bozza = "- **03/03/2025 10:12** SMS a nome della banca\n  [DOC-04, riga 6]\n\n- **03/03/2025 10:19** telefonata\n"
    assert [e["evento"] for e, t in confronta(bozza) if t] == ["SMS a nome della banca"]
    assert applica_regole(SI, PM, bozza, {"DOC-04": None}).esito == "chiedi"  # the second event has no source


def test_la_costruzione_cresce_di_uno_strumento_per_passo(tmp_path: Path) -> None:
    from esegui import carica_agente

    visti: list[list[str]] = []

    def modello(messaggi: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        visti.append(sorted(s.name for s in info.function_tools))
        return ModelResponse(parts=[TextPart("fatto")])

    with pytest.raises(NotImplementedError):
        carica_agente("costruzione").esegui(FunctionModel(modello), contesto(tmp_path), "Cronologia.", lambda *a: True)
    for passo in "abc":
        assert (
            carica_agente("costruzione", f"passo-{passo}.py").esegui(
                FunctionModel(modello), contesto(tmp_path), "Cronologia.", lambda *a: True
            )
            == "fatto"
        )
    assert visti == [[], ["leggi_documento"], ["cerca_nel_fascicolo", "invia_email", "leggi_documento"]]
