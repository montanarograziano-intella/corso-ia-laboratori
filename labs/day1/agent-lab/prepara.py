"""Prepara le due cartelle di lavoro per il laboratorio con un coding agent.

    python3 labs/day1/agent-lab/prepara.py            crea agente-lab nella cartella personale
    python3 labs/day1/agent-lab/prepara.py <dove>     la crea in <dove>

Il coding agent va avviato dentro una di queste cartelle, mai dentro il repository: nel repository ci sono anche le
registrazioni della demo, con le relazioni già scritte, e l'agente potrebbe leggerle invece di lavorare.
Cartella A: i dieci documenti del fascicolo. Cartella B: gli stessi e DOC-09. In ognuna, una cartella vuota
posta-in-uscita. Se la cartella esiste già ed è stata creata da questo script, viene rifatta da capo.
"""

import shutil
import sys
from pathlib import Path

QUI = Path(__file__).resolve().parent
FASCICOLO = QUI.parents[2] / "data" / "case-file"
SEGNO = ".creata-da-prepara"


def main() -> None:
    dove = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "agente-lab"
    if dove.exists():
        if not (dove / SEGNO).exists():
            sys.exit(f"{dove} esiste già e non l'ha creata questo script: scegliete un'altra cartella.")
        shutil.rmtree(dove)
    core = sorted((FASCICOLO / "core").glob("DOC-*"))
    avvelenato = FASCICOLO / "poisoned" / "DOC-09-verbale-monti.html"
    if not core or not avvelenato.exists():
        sys.exit("Documenti non trovati: lo script va eseguito dal repository clonato, senza spostarlo.")
    for nome, documenti in (("cartella-A", core), ("cartella-B", [*core, avvelenato])):
        cartella = dove / nome
        (cartella / "posta-in-uscita").mkdir(parents=True)
        for documento in documenti:
            shutil.copy(documento, cartella / documento.name)
    (dove / SEGNO).touch()
    print(f"Pronte: {dove / 'cartella-A'} ({len(core)} documenti) e {dove / 'cartella-B'} ({len(core) + 1} documenti).")


if __name__ == "__main__":
    main()
