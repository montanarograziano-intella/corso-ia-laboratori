"""Confronta il modello di base e quello con l'adattatore sulla denuncia DOC-01 e sugli esempi mai visti.

Uso: python3 prova.py <modello> <cartella dell'adattatore> <cartella dei dati> <file di uscita .json>

Tre varianti, sugli stessi testi:
- base: il modello di base con la sola istruzione usata nell'addestramento;
- base_con_formato: il modello di base con un prompt che descrive il formato campo per campo;
- adattato: il modello con l'adattatore, con la sola istruzione.
Per ciascuna scrive le risposte e la quota di campi uguali alla scheda attesa.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from genera import ISTRUZIONE
from mlx_lm import generate, load

QUI = Path(__file__).resolve().parent
DOC_01 = QUI.parents[2] / "data" / "case-file" / "core" / "DOC-01-denuncia-neri.txt"
SCHEDA_DOC_01 = """TIPO: FRODE-TEL
DATA_DENUNCIA: 03/03/2025
DENUNCIANTE: NERI Giulia
DATA_FATTO: 03/03/2025
CANALE: SMS+TEL
IMPORTO_EUR: 4200,00
STRUMENTO: BONIFICO-IST
CODICE_COMUNICATO: N.D.
ALLEGATI: 1"""
FORMATO = """Compila la scheda sintetica dell'ufficio per questa denuncia. Rispondi solo con nove righe, in
quest'ordine, nella forma CAMPO: valore.
TIPO: uno tra FRODE-TEL (falso operatore al telefono), PHISHING (email o pagina falsa), MARKETPLACE (annunci e
compravendite), FALSO-PARENTE, INVESTIMENTO.
DATA_DENUNCIA: GG/MM/AAAA.
DENUNCIANTE: COGNOME tutto in maiuscolo, poi il nome con la sola iniziale maiuscola.
DATA_FATTO: GG/MM/AAAA.
CANALE: i canali usati dal truffatore tra SMS, TEL, EML, WEB, APP (WhatsApp), in quest'ordine, uniti da + senza
spazi. Un SMS che porta solo un codice di sicurezza non conta.
IMPORTO_EUR: solo cifre, senza punto delle migliaia, con ,00.
STRUMENTO: uno tra BONIFICO-IST, BONIFICO, CARTA, RICARICA, CRIPTO.
CODICE_COMUNICATO: SI, NO oppure N.D. se la denuncia non lo dice con certezza.
ALLEGATI: il numero dei documenti allegati.
Esempio di scheda:
TIPO: PHISHING
DATA_DENUNCIA: 14/01/2025
DENUNCIANTE: BIANCHI Mario
DATA_FATTO: 12/01/2025
CANALE: EML+WEB
IMPORTO_EUR: 1300,00
STRUMENTO: CARTA
CODICE_COMUNICATO: NO
ALLEGATI: 2"""


def campi(testo: str) -> dict[str, str]:
    """Legge le righe CAMPO: valore; ignora il resto."""
    trovati = {}
    for riga in testo.splitlines():
        nome, separatore, valore = riga.partition(":")
        if separatore and nome.strip().isupper():
            trovati[nome.strip()] = valore.strip()
    return trovati


def campi_giusti(risposta: str, attesa: str) -> tuple[int, int]:
    attesi, dati = campi(attesa), campi(risposta)
    return sum(dati.get(nome) == valore for nome, valore in attesi.items()), len(attesi)


def chiedi(modello, tokenizer, istruzione: str, denuncia: str) -> str:
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": f"{istruzione}\n\n{denuncia}"}], add_generation_prompt=True, tokenize=False
    )
    return generate(modello, tokenizer, prompt=prompt, max_tokens=400, verbose=False).strip()


def main() -> None:
    nome_modello, adattatore, dati, uscita = sys.argv[1:5]
    doc_01 = "\n".join(riga for riga in DOC_01.read_text(encoding="utf-8").splitlines()[1:])
    esempi = [json.loads(riga)["messages"] for riga in (Path(dati) / "test.jsonl").open(encoding="utf-8")]
    casi = [("DOC-01", doc_01, SCHEDA_DOC_01)] + [
        (f"test-{numero:02d}", m[0]["content"].split("\n\n", 1)[1], m[1]["content"]) for numero, m in enumerate(esempi)
    ]

    risultati: dict = {"modello": nome_modello, "varianti": {}}
    for variante, percorso, istruzione in (
        ("base", None, ISTRUZIONE),
        ("base_con_formato", None, FORMATO),
        ("adattato", adattatore, ISTRUZIONE),
    ):
        modello, tokenizer = load(nome_modello, adapter_path=percorso)
        giusti = totale = schede_complete = 0
        per_campo: dict[str, int] = {}
        risposte = {}
        for nome, denuncia, attesa in casi:
            risposta = chiedi(modello, tokenizer, istruzione, denuncia)
            ok, su = campi_giusti(risposta, attesa)
            if nome == "DOC-01":
                risposte[nome] = {"risposta": risposta, "campi_giusti": ok, "campi": su}
            else:
                giusti, totale = giusti + ok, totale + su
                dati = campi(risposta)
                for campo, valore in campi(attesa).items():
                    per_campo[campo] = per_campo.get(campo, 0) + (dati.get(campo) == valore)
                schede_complete += ok == su
                if nome in ("test-00", "test-01"):
                    risposte[nome] = {"risposta": risposta, "attesa": attesa, "campi_giusti": ok}
        risultati["varianti"][variante] = {
            "campi_giusti_test": giusti,
            "campi_test": totale,
            "schede_tutte_giuste": schede_complete,
            "schede": len(casi) - 1,
            "giusti_per_campo": per_campo,
            "esempi": risposte,
        }
        print(
            variante, f"{giusti}/{totale} campi, {schede_complete}/{len(casi) - 1} schede, DOC-01:", risposte["DOC-01"]
        )
        del modello

    Path(uscita).write_text(json.dumps(risultati, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
