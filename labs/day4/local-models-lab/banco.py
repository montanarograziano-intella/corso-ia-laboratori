"""Il banco di prova del laboratorio sui modelli locali: quindici domande sul fascicolo, le stesse per ogni modello.

    python3 banco.py qwen3.5:4b-q4_K_M                 un modello
    python3 banco.py qwen3.5:4b-q4_K_M phi4-mini       più modelli, uno dopo l'altro
    python3 banco.py <modello> --contesto 2048         cambia la finestra di contesto (di solito 8192)
    python3 banco.py <modello> --vincolato             impone un JSON valido alle domande di estrazione
    python3 banco.py <modello> --ragiona               lascia ragionare il modello prima della risposta
    python3 banco.py <modello> --etichetta contesto-2k dà un nome alla prova nei risultati (per un esperimento)
    python3 banco.py --ricostruisci                    rifà visore/risultati.js dalle prove salvate, senza modelli

Ogni domanda stampa una riga verde o rossa, come un test. Una prova finisce con quattro numeri: risposte corrette,
tempo al primo token, token al secondo, memoria del modello caricato. I risultati vanno in risultati/ e in
visore/risultati.js: aprire visore/index.html per vedere tutte le prove fianco a fianco.

Servono solo Python e Ollama avviato (http://localhost:11434, oppure OLLAMA_HOST). Nessun altro pacchetto.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

QUI = Path(__file__).parent
FASCICOLO = QUI.parents[2] / "data" / "case-file"
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not HOST.startswith("http"):
    HOST = "http://" + HOST
VERDE, ROSSO, GRIGIO, FINE = "\033[32m", "\033[31m", "\033[90m", "\033[0m"
if os.name == "nt":
    os.system("")
# Il nome del computer distingue nel visore le prove dei docenti da quelle del gruppo. LAB_MACCHINA lo sostituisce.
MACCHINA = os.environ.get("LAB_MACCHINA") or platform.node()
SISTEMA = "Sei un assistente che aiuta un investigatore a lavorare su un fascicolo. Rispondi in italiano, solo con ciò che è scritto nei documenti."


def chiama(percorso: str, corpo: dict | None = None, flusso: bool = False):
    """Una chiamata all'API di Ollama. Con `flusso` restituisce una alla volta le righe JSON di una risposta in streaming."""
    richiesta = urllib.request.Request(
        HOST + percorso,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Content-Type": "application/json"},
    )
    risposta = urllib.request.urlopen(richiesta, timeout=600)
    if flusso:
        return (json.loads(riga) for riga in risposta if riga.strip())
    return json.loads(risposta.read())


def documento(id_documento: str) -> str:
    file = next((FASCICOLO / "core").glob(f"{id_documento}-*"))
    return file.read_text(encoding="utf-8")


# --- scoring: pure functions, tested in tests/ -------------------------------------------------------------------

TIPOGRAFICI = str.maketrans(
    {**dict.fromkeys("\u2010\u2011\u2012\u2013\u2212", "-"), **dict.fromkeys("\u00a0\u2009\u202f", " ")}
)


def piano(testo: str) -> str:
    """I modelli scrivono «4 marzo» e DOC‑05 con spazi stretti e trattini tipografici: si rendono semplici prima di dare il voto."""  # noqa: RUF002 (l'esempio è il punto)
    return testo.translate(TIPOGRAFICI)


def semplice(valore) -> str:
    """Un valore come stringa confrontabile: senza spazi, maiuscole e accenti; 4200.00 vale 4200, 4.200 vale 4200. Il segno conta."""
    if valore is None:
        return "null"
    if isinstance(valore, (int, float)):
        return str(int(valore)) if float(valore).is_integer() else str(valore)
    testo = unicodedata.normalize("NFKD", piano(str(valore))).encode("ascii", "ignore").decode().lower().strip()
    if testo in ("", "null", "none", "non indicato", "non indicata", "n/d", "non specificato"):
        return "null"
    if re.fullmatch(r"-?\d{1,3}([.\s]\d{3})+(,\d+)?|-?\d+(,\d+)?", testo):  # 4.200,00 and 4200,00
        numero = float(testo.replace(".", "").replace(" ", "").replace(",", "."))
        return str(int(numero)) if numero.is_integer() else str(numero)
    if re.fullmatch(r"-?\d+(\.\d+)?", testo):
        numero = float(testo)
        return str(int(numero)) if numero.is_integer() else str(numero)
    return re.sub(r"\s+", "", testo)


def primo_json(testo: str) -> dict | None:
    """Il primo oggetto JSON in un testo: i modelli lo avvolgono in una frase o in un blocco ```json."""
    testo = piano(testo)
    for inizio in [m.start() for m in re.finditer(r"\{", testo)]:
        for fine in range(len(testo), inizio, -1):
            if testo[fine - 1] == "}":
                try:
                    valore = json.loads(testo[inizio:fine])
                except ValueError:
                    continue
                if isinstance(valore, dict):
                    return valore
    return None


def valuta_estrazione(testo: str, atteso: dict) -> tuple[bool, str]:
    ottenuto = primo_json(testo)
    if ottenuto is None:
        return False, "nessun JSON nella risposta"
    mancanti = [campo for campo in atteso if campo not in ottenuto]
    if mancanti:  # un dato atteso assente non è dimostrato da un campo che manca o che ha un altro nome
        return False, "campo mancante: " + ", ".join(mancanti)
    sbagliati = [
        f"{campo}: atteso {atteso[campo]!r}, ottenuto {ottenuto.get(campo)!r}"
        for campo in atteso
        if semplice(ottenuto.get(campo)) != semplice(atteso[campo])
    ]
    return (not sbagliati), "; ".join(sbagliati)


def valuta_sintesi(testo: str, deve: list[str], non_deve: list[str]) -> tuple[bool, str]:
    testo = piano(testo)
    mancanti = [p for p in deve if not re.search(p, testo, re.IGNORECASE)]
    vietati = [p for p in non_deve if re.search(p, testo, re.IGNORECASE)]
    motivi = ([f"manca: {' / '.join(mancanti)}"] if mancanti else []) + (
        [f"non doveva esserci: {' / '.join(vietati)}"] if vietati else []
    )
    return (not motivi), "; ".join(motivi)


def valuta_strumento(chiamate: list[dict], atteso: dict) -> tuple[bool, str]:
    if not chiamate:
        return False, "nessuna chiamata a uno strumento"
    funzione = chiamate[0].get("function", {})
    nome, argomenti = funzione.get("name"), funzione.get("arguments") or {}
    if isinstance(argomenti, str):
        argomenti = primo_json(argomenti) or {}
    if nome != atteso["strumento"]:
        return False, f"strumento: atteso {atteso['strumento']}, chiamato {nome}"
    sbagliati = [
        f"{k}: atteso {v!r}, ottenuto {argomenti.get(k)!r}"
        for k, v in atteso.get("argomenti", {}).items()
        if semplice(argomenti.get(k)) != semplice(v)
    ]
    sbagliati += [
        f"{k}: doveva contenere {v!r}, ottenuto {argomenti.get(k)!r}"
        for k, v in atteso.get("argomenti_contengono", {}).items()
        if semplice(v) not in semplice(argomenti.get(k))
    ]
    return (not sbagliati), "; ".join(sbagliati)


# --- one run -----------------------------------------------------------------------------------------------------


def chiedi(
    modello: str,
    capacita: list[str],
    domanda: dict,
    strumenti: list[dict],
    contesto: int,
    vincolato: bool,
    ragiona: bool = False,
) -> dict:
    """Fa una domanda e restituisce la risposta con le sue misure."""
    nomi = (
        sorted(p.name[:6] for p in (FASCICOLO / "core").glob("DOC-*"))
        if domanda["documenti"] == "tutti"
        else domanda["documenti"]
    )
    testo_documenti = "\n\n".join(documento(d) for d in nomi)
    messaggi = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": (testo_documenti + "\n\n" if testo_documenti else "") + domanda["domanda"]},
    ]
    corpo: dict = {
        "model": modello,
        "messages": messaggi,
        "stream": True,
        "options": {"temperature": 0, "seed": 7, "num_ctx": contesto, "num_predict": 8000 if ragiona else 600},
    }
    if "thinking" in capacita:
        corpo["think"] = ragiona  # spento di solito: il banco misura la risposta, non il ragionamento
    if domanda["tipo"] == "strumento":
        if "tools" not in capacita:
            return {"testo": "", "chiamate": [], "errore": "il modello non supporta gli strumenti"}
        corpo["tools"] = [{"type": "function", "function": s} for s in strumenti]
    if domanda["tipo"] in ("estrazione", "fascicolo") and vincolato:
        corpo["format"] = {
            "type": "object",
            "properties": {k: {} for k in domanda["atteso"]},
            "required": list(domanda["atteso"]),
        }
    inizio, primo, testo, chiamate, ultima = time.monotonic(), None, "", [], {}
    try:
        for pezzo in chiama("/api/chat", corpo, flusso=True):
            messaggio = pezzo.get("message", {})
            if primo is None and (messaggio.get("content") or messaggio.get("tool_calls")):
                primo = time.monotonic() - inizio
            testo += messaggio.get("content", "")
            chiamate += messaggio.get("tool_calls") or []
            ultima = pezzo
    except (urllib.error.URLError, TimeoutError, ValueError) as errore:
        return {"testo": testo, "chiamate": chiamate, "errore": f"{type(errore).__name__}: {errore}"}
    durata = ultima.get("eval_duration") or 0
    return {
        "testo": testo,
        "chiamate": chiamate,
        "errore": None,
        "primo_token_s": round(primo, 2) if primo is not None else None,
        "token": ultima.get("eval_count") or 0,
        "token_al_secondo": round(ultima["eval_count"] / (durata / 1e9), 1) if durata else None,
        "secondi": round(time.monotonic() - inizio, 1),
    }


def esegui(
    modello: str, contesto: int, vincolato: bool, etichetta: str | None, solo: list[str], ragiona: bool = False
) -> dict:
    banco = json.loads((QUI / "domande.json").read_text(encoding="utf-8"))
    try:
        scheda = chiama("/api/show", {"model": modello})
    except urllib.error.HTTPError:
        sys.exit(f"Modello non trovato: {modello}. Installarlo con: ollama pull {modello}")
    except urllib.error.URLError:
        sys.exit(f"Ollama non risponde su {HOST}. Avviarlo, poi riprovare.")
    capacita = scheda.get("capabilities", [])
    # Il modello si carica prima del cronometro, con la stessa finestra: il tempo al primo token non misura il caricamento.
    chiama("/api/generate", {"model": modello, "options": {"num_ctx": contesto}})
    print(
        f"\n{modello}  ·  contesto {contesto}{'  ·  JSON vincolato' if vincolato else ''}{'  ·  ' + etichetta if etichetta else ''}"
    )
    print(f"{GRIGIO}capacità dichiarate: {', '.join(capacita) or 'nessuna'}{FINE}")
    esiti = []
    for domanda in banco["domande"]:
        if solo and domanda["id"] not in solo:
            continue
        r = chiedi(modello, capacita, domanda, banco["strumenti"], contesto, vincolato, ragiona)
        if r["errore"]:
            ok, motivo = False, r["errore"]
        elif domanda["tipo"] in ("estrazione", "fascicolo"):
            ok, motivo = valuta_estrazione(r["testo"], domanda["atteso"])
        elif domanda["tipo"] == "sintesi":
            ok, motivo = valuta_sintesi(r["testo"], domanda["deve_contenere"], domanda.get("non_deve_contenere", []))
        else:
            ok, motivo = valuta_strumento(r["chiamate"], domanda["atteso"])
        print(
            f"{VERDE + '  ✓' if ok else ROSSO + '  ✗'} {domanda['id']} {domanda['titolo']}{FINE}"
            + (f"{GRIGIO}  {motivo}{FINE}" if motivo else "")
        )
        esiti.append(
            {
                "id": domanda["id"],
                "tipo": domanda["tipo"],
                "titolo": domanda["titolo"],
                "ok": ok,
                "motivo": motivo,
                **{k: r.get(k) for k in ("testo", "chiamate", "primo_token_s", "token", "token_al_secondo", "secondi")},
            }
        )
    nomi = {modello, modello + ":latest"}
    caricato = next(
        (m for m in chiama("/api/ps").get("models", []) if m.get("name") in nomi or m.get("model") in nomi), {}
    )

    def media(campo: str) -> float | None:
        """La media sulle domande che hanno questa misura: un modello che non risponde non ha un primo token."""
        valori = [e[campo] for e in esiti if e.get(campo) is not None]
        return round(sum(valori) / len(valori), 2) if valori else None

    riepilogo = {
        "modello": modello,
        "etichetta": etichetta,
        "contesto": contesto,
        "vincolato": vincolato,
        "ragiona": ragiona,
        "capacita": capacita,
        "quando": datetime.now().isoformat(timespec="seconds"),
        "macchina": MACCHINA,
        "parametri": scheda.get("details", {}).get("parameter_size"),
        "quantizzazione": scheda.get("details", {}).get("quantization_level"),
        "corrette": sum(e["ok"] for e in esiti),
        "domande": len(esiti),
        "per_tipo": {
            t: [sum(e["ok"] for e in esiti if e["tipo"] == t), sum(1 for e in esiti if e["tipo"] == t)]
            for t in ("estrazione", "fascicolo", "sintesi", "strumento")
        },
        "primo_token_s": media("primo_token_s"),
        "token_al_secondo": media("token_al_secondo"),
        "memoria_gb": round(caricato.get("size", 0) / 1e9, 1) or None,
        "in_gpu_gb": round(caricato.get("size_vram", 0) / 1e9, 1) or None,
        "secondi": round(sum(e["secondi"] or 0 for e in esiti), 1),
        "esiti": esiti,
    }
    colore = VERDE if riepilogo["corrette"] == riepilogo["domande"] else ROSSO
    print(
        f"{colore}  {riepilogo['corrette']} corrette su {riepilogo['domande']}{FINE}  ·  primo token {riepilogo['primo_token_s']} s  ·  {riepilogo['token_al_secondo']} token/s  ·  memoria {riepilogo['memoria_gb']} GB  ·  {riepilogo['secondi']} s in tutto"
    )
    return riepilogo


def salva(riepilogo: dict) -> None:
    """Scrive la prova in risultati/ e ricostruisce visore/risultati.js da tutte le prove salvate."""
    nome = re.sub(
        r"[^a-z0-9.]+",
        "-",
        (riepilogo["modello"] + ("-" + riepilogo["etichetta"] if riepilogo["etichetta"] else "")).lower(),
    ).strip("-")
    (QUI / "risultati").mkdir(exist_ok=True)
    (QUI / "risultati" / f"{nome}.json").write_text(
        json.dumps(riepilogo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    ricostruisci_visore()


def ricostruisci_visore() -> None:
    corse = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((QUI / "risultati").glob("*.json"))]
    # Prima il modello migliore, e ogni esperimento subito dopo la prova normale del suo modello.
    base = {c["modello"]: c["corrette"] / max(c["domande"], 1) for c in corse if "esiti" in c and not c["etichetta"]}
    corse.sort(key=lambda c: (-base.get(c["modello"], 0), c["modello"], c.get("etichetta") or ""))
    banco = json.loads((QUI / "domande.json").read_text(encoding="utf-8"))
    dati = {
        "domande": [
            {k: d.get(k) for k in ("id", "tipo", "titolo", "domanda", "atteso", "deve_contenere")}
            for d in banco["domande"]
        ],
        "corse": [c for c in corse if "esiti" in c],
        "agente": [c for c in corse if "agente" in c],
    }
    intestazione = "// File generato da banco.py (ricostruisci_visore) da risultati/*.json e domande.json. Non modificare a mano.\n"
    (QUI / "visore" / "risultati.js").write_text(
        intestazione + "window.RISULTATI = " + json.dumps(dati, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("modelli", nargs="*", help="nomi dei modelli come li conosce Ollama")
    parser.add_argument(
        "--ricostruisci",
        action="store_true",
        help="rifà visore/risultati.js dalle prove salvate, senza interrogare modelli",
    )
    parser.add_argument("--contesto", type=int, default=8192, help="finestra di contesto in token (num_ctx)")
    parser.add_argument("--vincolato", action="store_true", help="forza un JSON valido sulle domande di estrazione")
    parser.add_argument(
        "--ragiona",
        action="store_true",
        help="lascia ragionare il modello prima di rispondere (solo modelli con questa capacità)",
    )
    parser.add_argument("--etichetta", help="nome di questa prova nei risultati, per un esperimento")
    parser.add_argument("--solo", nargs="*", default=[], help="solo queste domande, per esempio E1 T2")
    parser.add_argument("--non-salvare", action="store_true")
    args = parser.parse_args()
    if args.ricostruisci:
        ricostruisci_visore()
        return
    if not args.modelli:
        parser.error("serve almeno un modello, oppure --ricostruisci")
    for modello in args.modelli:
        riepilogo = esegui(modello, args.contesto, args.vincolato, args.etichetta, args.solo, args.ragiona)
        if not args.non_salvare and (
            not args.solo or args.etichetta
        ):  # una prova parziale si salva solo con un nome suo
            salva(riepilogo)
        chiama("/api/generate", {"model": modello, "keep_alive": 0})  # libera la memoria prima del modello successivo
    if not args.non_salvare and (not args.solo or args.etichetta):
        print(f"\nRisultati: {(QUI / 'visore' / 'index.html').relative_to(QUI)} (aprire nel browser)")


if __name__ == "__main__":
    main()
