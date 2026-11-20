"""Controlli senza modello: i passi del corpus, come si dividono le parole, come si leggono i passi attesi."""

import csv
import os
from pathlib import Path

import pytest

from rag import DISTRATTORI, FASCICOLO, parole, passi_del_corpus, trovato
from risposte import leggi_env, prompt


def test_un_passo_tra_alternative() -> None:
    assert trovato("DOC-10:6|DOC-03:16", ["DOC-01:2", "DOC-03:16"])
    assert not trovato("DOC-10:6|DOC-03:16", ["DOC-01:2"])


def test_la_contraddizione_chiede_tutte_e_due_le_versioni() -> None:
    attesi = "DOC-03:14 & DOC-01:9|DOC-10:6"
    assert trovato(attesi, ["DOC-10:6", "DOC-03:14"])
    assert not trovato(attesi, ["DOC-10:6", "DOC-01:9"])


def test_orari_e_indirizzi_restano_interi() -> None:
    assert "08:03:49" in parole("2025-03-02T08:03:49+01:00 mx1 delivered")
    assert "192.0.2.88" in parole("L'accesso proviene dall'indirizzo 192.0.2.88.")
    assert "che" not in parole("Che cosa registra il sito?")


def test_il_corpus_ha_i_passi_attesi() -> None:
    passi = dict(passi_del_corpus())
    assert len(list(FASCICOLO.glob("DOC-*"))) == 10 and len(list(DISTRATTORI.glob("DOC-*"))) == 5
    assert passi["DOC-02:8"].startswith("Domanda: Era presente")
    assert "465" in passi["DOC-05:8"] and "987 654" in passi["DOC-52:6"]
    assert not any(riferimento.startswith("DOC-09") for riferimento in passi)  # the poisoned document stays out


def test_ogni_passo_atteso_del_banco_esiste() -> None:
    # A question whose expected passage is not in the corpus could never be found: the table would be wrong by design.
    passi = dict(passi_del_corpus())
    with (Path(__file__).parent / "banco.csv").open(encoding="utf-8") as file:
        banco = list(csv.DictReader(file))
    assert len(banco) == 15
    for domanda in banco:
        for riferimento in domanda["passi_attesi"].replace("&", "|").split("|"):
            assert not riferimento.strip() or riferimento.strip() in passi, (domanda["n"], riferimento)


def test_il_prompt_porta_le_fonti_nella_forma_da_citare() -> None:
    testo = prompt("Domanda di prova?", [("DOC-05:8", "05/03/2025,Bonifico")])
    assert "[DOC-05, riga 8] 05/03/2025,Bonifico" in testo and testo.endswith("Domanda: Domanda di prova?")


def test_leggi_env_accetta_bom_e_virgolette_e_vince_sull_ambiente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LAB_MODEL", "vecchio")
    file = tmp_path / ".env"
    file.write_text('﻿LAB_MODEL="ollama:prova"\n# commento\nCHIAVE_DI_PROVA = abc \n', encoding="utf-8")
    leggi_env(file)
    assert os.environ["LAB_MODEL"] == "ollama:prova"
    assert os.environ.pop("CHIAVE_DI_PROVA") == "abc"
