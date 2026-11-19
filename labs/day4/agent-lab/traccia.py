"""Traccia di un'esecuzione, in sola aggiunta: un oggetto JSON per riga."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class Traccia:
    def __init__(self, path: Path, esecuzione: str) -> None:
        self.path = path
        self.esecuzione = esecuzione
        self.passo = 0
        path.parent.mkdir(parents=True, exist_ok=True)

    def scrivi(self, tipo: str, **campi: Any) -> None:
        """Write one record. `tipo` is one of: richiesta, strumento, approvazione, risposta, limite."""
        self.passo += 1
        record = {"esecuzione": self.esecuzione, "passo": self.passo, "ora": datetime.now().isoformat(timespec="seconds"), "tipo": tipo, **campi}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def leggi(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
