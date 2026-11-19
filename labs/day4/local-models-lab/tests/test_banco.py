"""Controlli sul voto, senza modello: che cosa conta come risposta corretta e che cosa no."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from banco import primo_json, semplice, valuta_estrazione, valuta_sintesi, valuta_strumento


def test_i_valori_si_confrontano_senza_formato() -> None:
    assert semplice("4.200,00") == semplice(4200) == semplice("4200.00") == semplice("4200") == "4200"
    assert semplice(-4200.0) == semplice("-4.200,00") == "-4200"  # the sign counts: the question asks for it without
    assert semplice("IT87 D999 9999 9990 0000 0123 465") == semplice("it87d9999999999000000123465")
    assert semplice(None) == semplice("null") == semplice("Non indicato") == "null"
    assert semplice("192.0.2.88") == "192.0.2.88" and semplice("10:19") == "10:19"


def test_il_json_si_trova_anche_in_mezzo_al_testo() -> None:
    assert primo_json('Ecco:\n```json\n{"importo": 4200}\n```\nFatto.') == {"importo": 4200}
    assert primo_json("nessun oggetto qui") is None


def test_un_estrazione_e_giusta_solo_se_tutti_i_campi_coincidono() -> None:
    assert valuta_estrazione('{"ora": "10:19", "durata_minuti": "17"}', {"ora": "10:19", "durata_minuti": 17}) == (True, "")
    ok, motivo = valuta_estrazione('{"ora": "10:12", "durata_minuti": 17}', {"ora": "10:19", "durata_minuti": 17})
    assert not ok and "ora" in motivo
    assert valuta_estrazione("Sono le 10:19.", {"ora": "10:19"})[0] is False


def test_un_dato_assente_e_giusto_solo_se_il_modello_non_lo_inventa() -> None:
    assert valuta_estrazione('{"ora_bonifico": null}', {"ora_bonifico": None})[0]
    assert valuta_estrazione('{"ora_bonifico": "non indicato"}', {"ora_bonifico": None})[0]
    assert not valuta_estrazione('{"ora_bonifico": "10:30"}', {"ora_bonifico": None})[0]
    # Un campo che manca, o un'ora inventata sotto un altro nome, non dimostra che il modello non ha inventato.
    ok, motivo = valuta_estrazione('{"ora": "10:12"}', {"ora_bonifico": None})
    assert not ok and "campo mancante" in motivo
    assert not valuta_estrazione("{}", {"ora_bonifico": None})[0]
    assert valuta_estrazione('{"ora_bonifico": ""}', {"ora_bonifico": None})[0]  # il campo c'è ed è vuoto: vale come assente


def test_un_riassunto_deve_avere_i_fatti_e_non_avere_quelli_sbagliati() -> None:
    assert valuta_sintesi("Il 4 marzo la signora dice di aver trasferito 2.400 euro.", ["2[.\\s]?400", "4 marzo"], ["4[.\\s]?200"]) == (True, "")
    ok, motivo = valuta_sintesi("On 4 March she moved the money.", ["2[.\\s]?400"], ["\\b(the|and)\\b"])
    assert not ok and "manca" in motivo and "non doveva" in motivo


def test_una_chiamata_e_giusta_se_strumento_e_argomenti_coincidono() -> None:
    atteso = {"strumento": "leggi_movimenti", "argomenti": {"data_iniziale": "03/03/2025", "data_finale": "05/03/2025"}}
    giusta = [{"function": {"name": "leggi_movimenti", "arguments": {"data_iniziale": "03/03/2025", "data_finale": "05/03/2025"}}}]
    assert valuta_strumento(giusta, atteso) == (True, "")
    assert not valuta_strumento([], atteso)[0]
    assert not valuta_strumento([{"function": {"name": "leggi_documento", "arguments": {}}}], atteso)[0]
    cerca = {"strumento": "cerca_nel_fascicolo", "argomenti_contengono": {"domanda": "Monti"}}
    assert valuta_strumento([{"function": {"name": "cerca_nel_fascicolo", "arguments": '{"domanda": "chi è Carla Monti"}'}}], cerca)[0]


def test_spazi_stretti_e_trattini_tipografici_non_contano_come_errore() -> None:
    stretto = "\u202f"
    assert valuta_sintesi(f"Il 4{stretto}marzo ha trasferito 2.400{stretto}euro.", ["2[.\\s]?400", "4 marzo"], [])[0]
    assert semplice(f"IT87{stretto}D999 9999 9990 0000 0123 465") == semplice("IT87D9999999999000000123465")


def test_il_visore_salvato_coincide_con_quello_ricostruito() -> None:
    import banco

    salvato = (banco.QUI / "visore" / "risultati.js").read_text(encoding="utf-8")
    banco.ricostruisci_visore()
    assert (banco.QUI / "visore" / "risultati.js").read_text(encoding="utf-8") == salvato
    assert salvato.startswith("// File generato da banco.py")
