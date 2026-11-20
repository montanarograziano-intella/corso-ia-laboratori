"""Genera denunce sintetiche con la loro scheda nel formato dell'ufficio.

Uso: python3 genera.py <cartella di uscita> [--n 400] [--seme 7]

Scrive train.jsonl, valid.jsonl e test.jsonl nel formato a messaggi che `mlx_lm.lora` legge.
Tutti i dati sono inventati: nomi, luoghi, importi e numeri non corrispondono a persone o fatti reali.
La denuncia DOC-01 del fascicolo non entra in nessuno dei tre file, ma l'intestazione e alcune frasi le somigliano:
è una prova mai vista, non una prova scritta da un'altra mano.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

ISTRUZIONE = "Compila la scheda sintetica dell'ufficio per questa denuncia."

NOMI = [
    "Marta", "Luca", "Elena", "Sergio", "Chiara", "Davide", "Paola", "Franco", "Silvia", "Aldo", "Rita", "Enzo",
    "Laura", "Piero", "Teresa", "Bruno", "Nadia", "Carlo", "Irene", "Guido", "Lucia", "Renato", "Emma", "Tullio",
]  # fmt: skip
COGNOMI = [
    "Bassi", "Conti", "Ferri", "Galli", "Leoni", "Moro", "Pagani", "Rota", "Sala", "Testa", "Vitali", "Zanetti",
    "Costa", "Fabbri", "Grasso", "Longo", "Marini", "Orlando", "Piras", "Serra", "Valli", "Donati", "Riva", "Sarti",
]  # fmt: skip
LUOGHI = ["Borgovecchio", "Portonuovo", "Colleverde", "Pietralta", "Rivachiara", "Montesole", "Vallefiorita"]
MESI = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
    "novembre", "dicembre",
]  # fmt: skip

# tipo -> canali di ciascun racconto (stesso ordine), strumenti possibili, racconti. Nei racconti: {ora} {importo} {strumento_testo}.
CASI: dict[str, dict] = {
    "FRODE-TEL": {
        "canali": [("SMS", "TEL"), ("TEL",), ("TEL",)],
        "strumenti": ["BONIFICO-IST", "BONIFICO"],
        "racconti": [
            "Alle {ora} ho ricevuto un SMS a nome della mia banca che parlava di un accesso sospetto. "
            "Subito dopo mi ha telefonato una persona che si è presentata come addetto antifrode. "
            "Mi ha convinto a mettere al sicuro i risparmi e ho eseguito {strumento_testo} di {importo} euro.",
            "Mi ha chiamato un uomo che diceva di lavorare per la banca. Sosteneva che qualcuno stesse svuotando "
            "il conto. Su sua indicazione ho fatto {strumento_testo} di {importo} euro verso un conto che mi ha "
            "dettato lui.",
            "Verso le {ora} squilla il telefono: una voce gentile, dice di essere dell'assistenza clienti. "
            "Mi tiene in linea a lungo e mi guida passo passo. Alla fine risulta partito {strumento_testo} "
            "di {importo} euro.",
        ],
    },
    "PHISHING": {
        "canali": [("EML", "WEB"), ("SMS", "WEB"), ("EML", "WEB")],
        "strumenti": ["BONIFICO", "CARTA", "BONIFICO-IST"],
        "racconti": [
            "Ho ricevuto un'email che sembrava della banca e chiedeva di aggiornare i dati. Ho aperto il "
            "collegamento e ho inserito le credenziali. Il giorno stesso ho trovato {strumento_testo} di "
            "{importo} euro che non ho mai disposto.",
            "Alle {ora} mi arriva un SMS con un indirizzo internet: diceva che il conto sarebbe stato "
            "sospeso. Ho compilato la pagina. Poco dopo sul conto compare {strumento_testo} di {importo} euro.",
            "Un'email con il logo dell'istituto mi invitava a confermare l'identità. Ho seguito il link senza "
            "sospettare. Mi sono accorto dopo di {strumento_testo} di {importo} euro a favore di uno sconosciuto.",
        ],
    },
    "MARKETPLACE": {
        "canali": [("WEB", "APP"), ("WEB",), ("WEB",)],
        "strumenti": ["RICARICA", "BONIFICO", "CARTA"],
        "racconti": [
            "Su un sito di annunci ho trovato un telefono usato. Il venditore mi ha scritto su WhatsApp e ha chiesto "
            "il pagamento anticipato. Ho fatto {strumento_testo} di {importo} euro e la merce non è mai arrivata.",
            "Vendevo una bicicletta online. L'acquirente mi ha fatto andare allo sportello automatico dicendo "
            "che così avrei ricevuto il denaro: invece ho eseguito io {strumento_testo} di {importo} euro.",
            "Ho risposto a un'inserzione per un affitto estivo. Mi hanno chiesto la caparra con "
            "{strumento_testo} di {importo} euro. Da quel momento nessuno ha più risposto.",
        ],
    },
    "FALSO-PARENTE": {
        "canali": [("APP",), ("APP",), ("TEL",)],
        "strumenti": ["BONIFICO-IST", "RICARICA", "BONIFICO"],
        "racconti": [
            "Mi è arrivato un messaggio su WhatsApp da un numero che non conoscevo: «mamma, ho rotto il telefono, questo è "
            "il numero nuovo». Chiedeva aiuto per un pagamento urgente. Ho disposto {strumento_testo} di "
            "{importo} euro.",
            "Alle {ora} una persona mi ha scritto su WhatsApp fingendosi mio figlio. Diceva di avere un debito da saldare "
            "in giornata. Ho mandato {importo} euro con {strumento_testo}.",
            "Ha telefonato un sedicente avvocato: mio nipote avrebbe causato un incidente e serviva una "
            "cauzione. Ho pagato {importo} euro con {strumento_testo}.",
        ],
    },
    "INVESTIMENTO": {
        "canali": [("WEB", "TEL"), ("APP", "WEB"), ("TEL", "WEB")],
        "strumenti": ["BONIFICO", "CRIPTO", "CARTA"],
        "racconti": [
            "Ho visto una pubblicità su guadagni sicuri e ho lasciato il mio numero. Un consulente mi ha "
            "richiamato più volte. Ho versato {importo} euro con {strumento_testo} su una piattaforma che ora "
            "non si apre più.",
            "Un conoscente mi ha proposto su WhatsApp un investimento. All'inizio vedevo i profitti su un sito. "
            "Quando ho chiesto di ritirare mi hanno chiesto altre commissioni. In tutto ho perso {importo} "
            "euro, pagati con {strumento_testo}.",
            "Mi hanno contattato per telefono offrendo titoli ad alto rendimento. Ho eseguito "
            "{strumento_testo} di {importo} euro. Il sito è sparito dopo una settimana.",
        ],
    },
}

STRUMENTO_TESTO = {
    "BONIFICO-IST": ["un bonifico istantaneo", "un bonifico immediato dal telefono"],
    "BONIFICO": ["un bonifico", "un bonifico ordinario"],
    "CARTA": ["un pagamento con la carta", "un addebito sulla carta di credito"],
    "RICARICA": ["una ricarica su una carta prepagata", "una ricarica di carta prepagata"],
    "CRIPTO": ["un acquisto di criptovaluta", "un trasferimento in criptovalute"],
}
ORDINE_CANALI = ["SMS", "TEL", "EML", "WEB", "APP"]
CODICE_TESTO = {
    "SI": [
        "Mi è stato chiesto il codice di sicurezza arrivato sul telefono e l'ho comunicato.",
        "Ho letto al telefono il codice di sicurezza che mi era arrivato.",
    ],
    "NO": ["Non ho comunicato a nessuno il codice di sicurezza.", "Mi hanno chiesto un codice ma non l'ho dato."],
    "N.D.": ["Non ricordo se ho comunicato il codice che mi è arrivato.", ""],
}
ALLEGATI_TESTO = {
    0: ["", "Non ho documenti da allegare."],
    1: ["Allego una schermata del messaggio.", "Allego la ricevuta dell'operazione."],
    2: ["Allego due schermate della conversazione.", "Allego la ricevuta e una schermata."],
    3: ["Allego tre documenti: ricevuta, schermata e copia del messaggio.", "Allego tre schermate."],
}
INTESTAZIONI = [
    "Verbale di ricezione di denuncia-querela orale\nCommissariato di P.S. di {luogo} (località di fantasia) · "
    "{data_lunga}, ore {ora_verbale}\nAvanti al sottoscritto ufficiale di P.G. è presente {nome} {cognome}, "
    "che dichiara:",
    "DENUNCIA-QUERELA\nUfficio denunce di {luogo} (località di fantasia), {data_lunga}\nIl giorno sopra "
    "indicato si presenta {nome} {cognome}, che espone quanto segue.",
    "Verbale di denuncia sporta da {nome} {cognome}\n{luogo} (località di fantasia), {data_lunga} alle "
    "{ora_verbale}",
]
CHIUSURE = [
    "Chiedo che si proceda nei confronti dei responsabili.\nLetto, confermato e sottoscritto.",
    "Sporgo formale querela contro ignoti.\nLetto, confermato e sottoscritto: {nome} {cognome}.",
    "Mi riservo di integrare la denuncia. Letto e sottoscritto.",
]


def importo_testo(valore: int, caso: random.Random) -> str:
    """Scrive l'importo come lo scrive una persona: con o senza punto delle migliaia."""
    if valore >= 1000 and caso.random() < 0.7:
        return f"{valore:,}".replace(",", ".")
    return str(valore)


def data_lunga(giorno: date) -> str:
    return f"{giorno.day} {MESI[giorno.month - 1]} {giorno.year}"


def un_esempio(caso: random.Random) -> dict:
    """Restituisce una denuncia e la sua scheda."""
    tipo = caso.choice(list(CASI))
    spec = CASI[tipo]
    nome, cognome, luogo = caso.choice(NOMI), caso.choice(COGNOMI), caso.choice(LUOGHI)
    denuncia = date(2024, 1, 1) + timedelta(days=caso.randrange(0, 700))
    ritardo = caso.choice([0, 0, 0, 1, 1, 2, 3, 5, 9])
    fatto = denuncia - timedelta(days=ritardo)
    strumento = caso.choice(spec["strumenti"])
    valore = caso.choice([180, 250, 390, 480, 650, 900, 1200, 1500, 1850, 2400, 3100, 4750, 6000, 8900, 12500])
    codice = caso.choice(["SI", "NO", "N.D."]) if tipo in ("FRODE-TEL", "PHISHING") else "N.D."
    allegati = caso.choice([0, 1, 1, 2, 3])
    ora = f"{caso.randrange(8, 21)}:{caso.choice(['05', '12', '20', '30', '41', '48'])}"

    quale = caso.randrange(len(spec["racconti"]))
    # Ogni racconto ha i suoi canali. Un SMS che porta solo un codice non conta come canale della frode.
    canali = spec["canali"][quale]
    racconto = spec["racconti"][quale].format(
        ora=ora, importo=importo_testo(valore, caso), strumento_testo=caso.choice(STRUMENTO_TESTO[strumento])
    )
    quando = (
        f"I fatti sono di oggi, {data_lunga(fatto)}."
        if ritardo == 0
        else f"I fatti risalgono al {data_lunga(fatto)}."
    )
    righe = [
        caso.choice(INTESTAZIONI).format(
            luogo=luogo,
            data_lunga=data_lunga(denuncia),
            ora_verbale=f"{caso.randrange(9, 19)}:{caso.choice(['00', '15', '40'])}",
            nome=nome,
            cognome=cognome,
        ),
        f"Io sottoscritto/a {nome} {cognome}, residente a {luogo}, espongo quanto segue.",
    ]
    frase_codice = caso.choice(CODICE_TESTO[codice]) if tipo in ("FRODE-TEL", "PHISHING") else ""
    corpo = [quando, racconto, frase_codice, caso.choice(ALLEGATI_TESTO[allegati])]
    if caso.random() < 0.3:  # l'ordine in cui una persona racconta non è sempre lo stesso
        corpo[0], corpo[1] = corpo[1], corpo[0]
    righe += [riga for riga in corpo if riga]
    righe.append(caso.choice(CHIUSURE).format(nome=nome, cognome=cognome))

    scheda = "\n".join(
        [
            f"TIPO: {tipo}",
            f"DATA_DENUNCIA: {denuncia:%d/%m/%Y}",
            f"DENUNCIANTE: {cognome.upper()} {nome}",
            f"DATA_FATTO: {fatto:%d/%m/%Y}",
            f"CANALE: {'+'.join(c for c in ORDINE_CANALI if c in canali)}",
            f"IMPORTO_EUR: {valore},00",
            f"STRUMENTO: {strumento}",
            f"CODICE_COMUNICATO: {codice}",
            f"ALLEGATI: {allegati}",
        ]
    )
    return {
        "messages": [
            {"role": "user", "content": f"{ISTRUZIONE}\n\n" + "\n".join(righe)},
            {"role": "assistant", "content": scheda},
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uscita", type=Path)
    parser.add_argument("--n", type=int, default=400, help="esempi di addestramento")
    parser.add_argument("--seme", type=int, default=7)
    args = parser.parse_args()

    caso = random.Random(args.seme)
    args.uscita.mkdir(parents=True, exist_ok=True)
    for nome, quanti in (("train", args.n), ("valid", 40), ("test", 40)):
        with (args.uscita / f"{nome}.jsonl").open("w", encoding="utf-8") as file:
            for _ in range(quanti):
                file.write(json.dumps(un_esempio(caso), ensure_ascii=False) + "\n")
        print(f"{nome}: {quanti} esempi")


if __name__ == "__main__":
    main()
