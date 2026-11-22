"""Write dati.js for the lab page: the two folders and every document as the demo agent's tool returns it.

    python3 labs/day1/agent-lab/pagina.py

Cartella A is the clean case file, cartella B the same plus DOC-09. The text of each document is exactly what
`leggi_documento` gives the demo agent (labs/day1/agent-demo/fascicolo.py), hidden lines of DOC-09 included.
Rerun after any change to the case file.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

QUI = Path(__file__).resolve().parent
RADICE = QUI.parents[2]
sys.path.insert(0, str(QUI.parent / "agent-demo"))
from fascicolo import carica  # noqa: E402

CORE = RADICE / "data" / "case-file" / "core"
AVVELENATO = RADICE / "data" / "case-file" / "poisoned" / "DOC-09-verbale-monti.html"


def cartella(con_doc09: bool) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        dove = Path(tmp)
        for f in CORE.glob("DOC-*"):
            shutil.copy(f, dove / f.name)
        if con_doc09:
            shutil.copy(AVVELENATO, dove / AVVELENATO.name)
        documenti = carica(dove)
    return {
        "elenco": "\n".join(f"{d.id}: {d.nome}" for d in documenti.values()),
        "documenti": {d.id: d.testo_numerato() for d in documenti.values()},
    }


dati = {"A": cartella(False), "B": cartella(True)}
(QUI / "dati.js").write_text(
    "// Generato da pagina.py: non modificare a mano.\nwindow.LAB = " + json.dumps(dati, ensure_ascii=False, indent=1) + ";\n",
    encoding="utf-8",
)
print({k: len(v["documenti"]) for k, v in dati.items()})
