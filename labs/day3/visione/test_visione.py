"""Controlli senza modelli: le misure, la lettura dell'IBAN e i dati del test set."""

import re

import pytest
import visione
from PIL import Image
from visione import (
    DATI,
    FOTO_IBAN,
    Parola,
    apri_immagine,
    caratteri_da_correggere,
    caratteri_incerti,
    cer,
    classifica_riquadri,
    fotogrammi,
    iban_piu_simile,
    iban_vero,
    iou,
    misura_rilevamento,
    riga_che_inizia_con,
    targhe_di_fantasia,
    veicoli_veri,
)


def test_iou() -> None:
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0
    assert iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)


def test_ogni_veicolo_vero_conta_una_volta() -> None:
    vero = [(0, 0, 10, 10)]
    doppio = [((0, 0, 10, 10), 0.9), ((1, 0, 11, 10), 0.8)]
    esito = classifica_riquadri(doppio, vero, soglia=0.5)
    assert (len(esito["TP"]), len(esito["FP"]), len(esito["FN"])) == (1, 1, 0)


def test_la_soglia_toglie_i_riquadri_deboli() -> None:
    previsti = [((0, 0, 10, 10), 0.9), ((50, 50, 60, 60), 0.4)]
    veri = {"F": [(0, 0, 10, 10), (100, 100, 110, 110)]}
    bassa = misura_rilevamento({"F": previsti}, veri, 0.3)
    alta = misura_rilevamento({"F": previsti}, veri, 0.5)
    assert (bassa["precisione"], bassa["recall"]) == (0.5, 0.5)
    assert (alta["precisione"], alta["recall"]) == (1.0, 0.5)


def test_una_cifra_sbagliata_rende_sbagliato_l_iban() -> None:
    vero = "IT87 D999 9999 9990 0000 0123 456"
    assert cer("IT87 D999 9999 9990 0000 0128 456", vero) == pytest.approx(1 / len(vero))
    letto = iban_piu_simile("Bonifico IT87 D999 9999 9990 0000 0128 456 euro", vero)
    assert caratteri_da_correggere(letto, vero) == 1
    assert caratteri_da_correggere(iban_piu_simile("IT87 D999 9999 9990 0000 0123 456", vero), vero) == 0


def test_l_iban_letto_puo_avere_un_carattere_in_piu() -> None:
    vero = "IT87 D999 9999 9990 0000 0123 456"
    letto = iban_piu_simile("-4.200,00 IT87 D999 9999 9990 0000 01234 456", vero)
    assert caratteri_da_correggere(letto, vero) == 1


def test_gli_iban_di_doc_05() -> None:
    assert iban_vero(6) == "IT87 D999 9999 9990 0000 0123 456"
    assert iban_vero(8) == "IT87 D999 9999 9990 0000 0123 465"


def test_caratteri_incerti() -> None:
    righe = [
        [Parola("D389", [0.99, 0.6, 0.95, 0.99], 0.5, 0.1, 0.1)],
        [Parola("05/03/2025", [1.0] * 10, 0.7, 0.1, 0.1)],
    ]
    assert caratteri_incerti(righe) == [("D389", "3", 0.6)]
    assert visione.testo_letto(righe, soglia=0.9) == "D[3]89\n05/03/2025"
    assert riga_che_inizia_con(righe, "05/03") == "05/03/2025"


def test_il_test_set() -> None:
    gruppi = list(fotogrammi().values())
    assert (gruppi.count("giorno"), gruppi.count("notte")) == (24, 5)
    veri = veicoli_veri()
    assert all(veri.values()), "ogni fotogramma ha almeno un veicolo"
    for file, riquadri in veri.items():
        larghezza, altezza = apri_immagine(file).size
        assert all(0 <= x0 < x1 <= larghezza and 0 <= y0 < y1 <= altezza for x0, y0, x1, y1 in riquadri), file


def test_le_targhe_sono_di_fantasia() -> None:
    for targa in targhe_di_fantasia():
        assert re.fullmatch(r"[A-Z]{2} \d{3} [A-Z]{2}", targa["targa"])
        assert set(targa["targa"]) & {"I", "O", "Q", "U"}, "una targa italiana valida non usa I, O, Q, U"
        larghezza, altezza = apri_immagine(targa["file"]).size
        x0, y0, x1, y1 = targa["riquadro"]
        assert 0 <= x0 < x1 <= larghezza and 0 <= y0 < y1 <= altezza


def test_scansioni_e_foto() -> None:
    for documento in ("DOC-01", "DOC-05", "DOC-10"):
        assert (DATI / "scansioni" / f"{documento}.txt").read_text(encoding="utf-8").startswith("DATI SINTETICI")
        assert Image.open(DATI / "scansioni" / f"{documento}.jpg").size == (1240, 1754)
    assert FOTO_IBAN.exists(), "FOTO-01 sta nel fascicolo: il laboratorio va aperto dentro il repository intero"
