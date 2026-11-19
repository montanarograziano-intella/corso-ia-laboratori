"""Avvia l'agente del mattino (../agent-lab) con un modello locale e dice che cosa è successo.

    python3 agente_locale.py qwen3.5:4b-q4_K_M
    python3 agente_locale.py qwen3.5:4b-q4_K_M --contesto 4096    lo stesso, con una finestra di contesto piccola

L'agente parla con Ollama attraverso l'indirizzo compatibile con OpenAI, che non permette di fissare la finestra di
contesto a ogni richiesta. Per questo lo script crea prima una copia del modello con la finestra fissata
(`<modello>-ctx16k`; per il modello di riferimento è `qwen3.5-4b-16k`, la stessa del mattino), poi ci avvia l'agente. Riporta i documenti letti, se un'email è stata scritta, quanti eventi
di riferimento contiene, e il tempo impiegato. I risultati vanno in risultati/ e nel visore (visore/index.html).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from banco import HOST, MACCHINA, QUI, chiama, ricostruisci_visore  # noqa: E402

LAB = QUI.parent / "agent-lab"
LIMITE_SECONDI = 900


# La copia a 16k del modello di riferimento ha lo stesso nome che le dà il laboratorio del mattino: è la stessa copia.
NOMI_DEL_MATTINO = {("qwen3.5:4b-q4_K_M", 16384): "qwen3.5-4b-16k"}


def con_contesto(modello: str, contesto: int) -> str:
    """Crea (o riusa) una copia del modello con la finestra di contesto fissata, e ne restituisce il nome."""
    nome = NOMI_DEL_MATTINO.get((modello, contesto)) or f"{modello.replace(':', '-')}-ctx{contesto // 1024}k"
    try:
        for _ in chiama("/api/create", {"model": nome, "from": modello, "parameters": {"num_ctx": contesto}}, flusso=True):
            pass
    except urllib.error.HTTPError:
        sys.exit(f"Modello non trovato: {modello}. Installarlo con: ollama pull {modello}")
    except urllib.error.URLError:
        sys.exit(f"Ollama non risponde su {HOST}. Avviarlo, poi riprovare.")
    return nome


def riassumi(passi: list[dict], uscita: str, scaduto: bool, email: bool, punteggio: str) -> dict:
    """Che cosa è successo in un'esecuzione, dalla traccia e dalle uscite dei due programmi del mattino. Non tocca file né modelli."""
    documenti = passi[0]["documenti"] if passi else []
    letti = {p["argomenti"].get("id_documento", "").upper() for p in passi if p.get("strumento") == "leggi_documento" and not str(p.get("risultato", "")).startswith("documento non trovato")}
    voto = re.search(r"(\d+) eventi trovati su (\d+)", punteggio) if email else None
    interrotta = re.search(r"Esecuzione interrotta: (.+)", uscita)
    if scaduto:
        nota = "tempo scaduto dopo 15 minuti"
    elif "does not support tools" in uscita:
        nota = "il modello non supporta gli strumenti"
    elif interrotta:
        nota = interrotta.group(1)[:140]
    elif not email:
        nota = "ha risposto senza inviare l'email"
    elif not voto:  # il formato dell'uscita di confronta.py è cambiato: meglio dirlo che scrivere zero
        nota = "email inviata, ma il punteggio non si è potuto leggere"
    else:
        nota = ""
    return {
        "documenti_letti": len(letti & set(documenti)), "documenti": len(documenti), "email_inviata": email,
        "eventi_trovati": int(voto.group(1)) if voto else None, "eventi": int(voto.group(2)) if voto else None,
        "passi": len(passi), "nota": nota,
    }


def prova(modello: str, contesto: int) -> dict:
    variante = con_contesto(modello, contesto)
    prima = {p.name for p in (LAB / "lavoro" / "tracce").glob("*.jsonl")} if (LAB / "lavoro" / "tracce").exists() else set()
    inizio = time.monotonic()
    # L'agente deve parlare con lo stesso Ollama del banco, anche quando è su un altro computer (OLLAMA_HOST).
    ambiente = {**os.environ, "LAB_MODEL": f"ollama:{variante}", "LAB_RISPOSTA": "a", "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", HOST + "/v1")}
    try:
        esito = subprocess.run(["uv", "run", "--quiet", "esegui.py", "soluzione", "pulita"], cwd=LAB, env=ambiente, capture_output=True, text=True, timeout=LIMITE_SECONDI)
        uscita, scaduto = esito.stdout + esito.stderr, False
    except FileNotFoundError:
        sys.exit("uv non trovato: il progetto del mattino non è installato su questo portatile. Usare le prove nel visore.")
    except subprocess.TimeoutExpired as tempo:
        uscita, scaduto = (tempo.stdout or b"").decode(errors="replace") if isinstance(tempo.stdout, bytes) else (tempo.stdout or ""), True
    secondi = round(time.monotonic() - inizio)
    chiama("/api/generate", {"model": variante, "keep_alive": 0})
    nuove = sorted(p for p in (LAB / "lavoro" / "tracce").glob("*.jsonl") if p.name not in prima)
    passi = [json.loads(r) for r in nuove[-1].read_text(encoding="utf-8").splitlines()] if nuove else []
    email = sorted((LAB / "lavoro" / "posta-in-uscita" / nuove[-1].stem).glob("*.txt")) if nuove else []
    punteggio = subprocess.run(["uv", "run", "--quiet", "confronta.py", str(email[-1])], cwd=LAB, capture_output=True, text=True).stdout if email else ""
    return {
        "modello": modello, "contesto": contesto, "quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "macchina": MACCHINA,
        "agente": {**riassumi(passi, uscita, scaduto, bool(email), punteggio), "secondi": secondi},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("modelli", nargs="+")
    parser.add_argument("--contesto", type=int, default=16384)
    args = parser.parse_args()
    for modello in args.modelli:
        print(f"\n{modello} · contesto {args.contesto}: l'agente lavora sul fascicolo (fino a 15 minuti)...")
        r = prova(modello, args.contesto)
        a = r["agente"]
        print(f"  documenti letti {a['documenti_letti']}/{a['documenti']} · email {'inviata' if a['email_inviata'] else 'NON inviata'} · eventi {a['eventi_trovati'] if a['eventi'] else 'n.d.'}/{a['eventi'] or 'n.d.'} · {a['secondi']} s" + (f" · {a['nota']}" if a["nota"] else ""))
        nome = re.sub(r"[^a-z0-9.]+", "-", f"agente-{modello}-ctx{args.contesto}".lower())
        (QUI / "risultati" / f"{nome}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ricostruisci_visore()


if __name__ == "__main__":
    main()
