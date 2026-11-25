"""Confronta una cronologia scritta da un agente con quella di riferimento.

    uv run confronta.py <file con la risposta dell'agente>

Un evento conta come trovato quando la sua data (con l'ora e l'importo, se la cronologia di riferimento li ha)
compare su una riga della risposta che cita anche almeno una delle fonti di riferimento per quell'evento. La
fonte può stare anche sulla riga sotto l'evento.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fascicolo import eventi

RIFERIMENTO = Path(__file__).parents[3] / "data" / "case-file" / "reference" / "timeline.csv"
MESI = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]


def forme_della_data(iso: str) -> list[str]:
    """Le scritture di una data che contano: 2025-03-02, 02/03/2025, 2/3/2025, 2/03/2025, 2 marzo, 02 marzo, 2 mar, 02 mar."""
    anno, mese, giorno = iso.split("-")
    nome = MESI[int(mese) - 1]
    giorni, mesi = {giorno, str(int(giorno))}, {mese, str(int(mese))}
    return [
        iso,
        *(f"{g}/{m}/{anno}" for g in giorni for m in mesi),
        *(f"{g} {m}" for g in giorni for m in (nome, nome[:3])),
    ]


def contiene(riga: str, forma: str) -> bool:
    """La forma compare nella riga come numero intero: «2/3/2025» non vale dentro «12/3/2025», «4.200» non vale dentro «14.200»."""
    return re.search(rf"(?<!\d){re.escape(forma)}(?!\d)", riga, re.IGNORECASE) is not None


def corrisponde(riga: str, evento: dict, con_fonte: bool = True) -> bool:
    """Una riga della risposta vale per un evento di riferimento: stessa data, e ora e importo se il riferimento li ha.
    Con `con_fonte` la riga deve anche citare una delle fonti di riferimento."""
    ora = evento["ora"] if re.fullmatch(r"\d\d:\d\d", evento["ora"]) else None
    importo = f"{int(float(evento['importo'])):,}".replace(",", ".") if evento["importo"] else None  # 4200.00 -> 4.200
    return bool(
        any(contiene(riga, forma) for forma in forme_della_data(evento["data"]))
        and (ora is None or contiene(riga, ora) or contiene(riga, ora.replace(":", ".")))
        and (importo is None or contiene(riga, importo) or contiene(riga, importo.replace(".", "")))
        and (not con_fonte or set(re.findall(r"DOC-\d+", evento["fonti"])) & set(re.findall(r"DOC-\d+", riga)))
    )


def confronta(risposta: str, riferimento: Path = RIFERIMENTO, con_fonte: bool = True) -> list[tuple[dict, bool]]:
    righe = [r for r in riferimento.read_text(encoding="utf-8").splitlines() if not r.startswith("#")]
    blocchi = eventi(risposta)
    usati: set[int] = set()  # una riga della risposta vale per un solo evento di riferimento
    esiti = []
    for evento in csv.DictReader(righe):
        indice = next(
            (n for n, riga in enumerate(blocchi) if n not in usati and corrisponde(riga, evento, con_fonte)), None
        )
        if indice is not None:
            usati.add(indice)
        esiti.append((evento, indice is not None))
    return esiti


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    esiti = confronta(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for evento, trovato in esiti:
        print(f"{'trovato ' if trovato else 'MANCA   '} {evento['data']} {evento['ora']:<13} {evento['evento']}")
    print(f"\n{sum(t for _, t in esiti)} eventi trovati su {len(esiti)}")


if __name__ == "__main__":
    main()
