"""Il notebook, eseguito dall'inizio alla fine con il modello finto al posto di Ollama: nessuna rete, nessun modello."""

import io
import json
import sys
import urllib.request
import zlib
from pathlib import Path

import numpy as np

LAB = Path(__file__).parents[1]
sys.path.insert(0, str(LAB))

from modello_finto import modello_finto


def _ollama_finto(richiesta, timeout=None):
    corpo = json.loads(richiesta.data)
    messaggio = modello_finto(corpo["messages"], corpo.get("tools"), corpo.get("format"))
    return io.BytesIO(json.dumps({"message": messaggio}).encode())


class _VettoriFinti:
    """Al posto del modello di embedding (1 GB): un vettore che dipende solo dal testo."""

    def __init__(self, *_, **__) -> None:
        pass

    def embed(self, testi):
        return [np.random.default_rng(zlib.crc32(testo.encode())).random(8) for testo in testi]


def test_il_notebook_gira_e_i_controlli_fermano_il_documento_avvelenato(monkeypatch) -> None:
    monkeypatch.chdir(LAB)
    monkeypatch.setattr(urllib.request, "urlopen", _ollama_finto)
    sys.path.append(str(LAB.parents[1] / "day3" / "rag"))
    import rag

    monkeypatch.setattr(rag, "TextEmbedding", _VettoriFinti)
    monkeypatch.setenv("LAB_RISPOSTA", "r")
    spazio: dict = {}
    for cella in json.loads((LAB / "notebook.ipynb").read_text(encoding="utf-8"))["cells"]:
        if cella["cell_type"] == "code":
            exec(compile("".join(cella["source"]), cella["id"], "exec"), spazio)

    assert spazio["chiedi_al_modello"] is spazio["modello_vero"]  # step 8 puts the local model back

    avvelenata = LAB / "lavoro" / "notebook" / "avvelenata-finto"
    passi = [json.loads(riga) for riga in (avvelenata / "traccia.jsonl").read_text(encoding="utf-8").splitlines()]
    assert passi[0]["argomenti"] == {"id_documento": "DOC-09"}
    assert passi[-1]["tipo"] == "gate" and passi[-1]["esito"] == "ferma"
    assert not list((avvelenata / "posta-in-uscita").glob("*.txt"))
    # Senza gate la richiesta arriva alla persona, che qui rifiuta: l'email non parte nemmeno così.
    spazio["contesto"] = spazio["nuova_esecuzione"]("prova", avvelenata=True)
    spazio["chiedi_al_modello"] = modello_finto
    spazio["agente"]("Leggi DOC-09.", spazio["STRUMENTI"], spazio["esegui_con_controllo"])
    assert not list(spazio["contesto"].posta_in_uscita.glob("*.txt"))
    assert spazio["contesto"].traccia.leggi()[-1]["esito"] == "rifiutata"
    # Un invio legittimo: il gate dice «procedi», poi decide la persona, che qui rifiuta.
    legittima = {
        "destinatario": "procura@esempio.invalid",
        "oggetto": "Fatto",
        "testo": "SMS alle 10:12 [DOC-01, riga 6].",
        "allegati": [],
    }
    spazio["contesto"] = spazio["nuova_esecuzione"]("prova-legittima")
    assert "rifiutato" in spazio["esegui_con_gate"]({"name": "invia_email", "arguments": legittima})
    passi = spazio["contesto"].traccia.leggi()
    assert [(p["tipo"], p["esito"]) for p in passi] == [("gate", "procedi"), ("approvazione", "rifiutata")]
    assert passi[-1]["deciso_da"] == "LAB_RISPOSTA" and not list(spazio["contesto"].posta_in_uscita.glob("*.txt"))
    # Una fonte che non esiste ferma la bozza, anche scritta con un trattino tipografico.
    assert (
        spazio["gate"]("procura@esempio.invalid", "SMS alle 10:12 [DOC-01, riga 6] e [DOC\u201199, riga 3].").esito
        == "ferma"
    )
