"""Il motore del notebook di computer vision: i dati, i quattro modelli e le misure.

I modelli girano sul processore, senza scheda grafica, e si scaricano una volta nella cartella `.modelli/` qui
accanto. Dopo il primo avvio il notebook non usa la rete.
"""

from __future__ import annotations

import csv
import logging
import os
import re
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

QUI = Path(__file__).resolve().parent
DATI = QUI / "dati"
MODELLI = QUI / ".modelli"
FASCICOLO = QUI.parents[2] / "data" / "case-file"
FOTO_IBAN = FASCICOLO / "media" / "FOTO-01-iban-manoscritto.jpg"

RILEVATORE = "PekingU/rtdetr_v2_r18vd"  # Apache 2.0, addestrato su COCO 2017 (train): queste foto non le ha viste
RICERCA = "google/siglip2-base-patch16-224"  # Apache 2.0, testo e immagini nello stesso spazio, multilingue
VLM = "HuggingFaceTB/SmolVLM-256M-Instruct"  # Apache 2.0, il VLM più piccolo che risponde a una domanda
VEICOLI = {"car", "truck", "bus"}
SOGLIE = (0.3, 0.5, 0.7)
IOU_MINIMA = 0.5  # la soglia di IoU: un riquadro previsto è giusto se la parte in comune è almeno metà dell'unione
SOGLIA_INCERTO = 0.9

Riquadro = tuple[float, float, float, float]

# PyTorch avvisa su macOS che una funzione che il notebook non usa manca: il livello lo reimposta lui, va spento.
logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").disabled = True


def _carica(classe, nome: str, **opzioni):
    """Dalla cartella `.modelli/` senza rete, se il modello c'è già; altrimenti lo scarica, una volta."""
    from transformers.utils import logging as registro

    # Avvisi di configurazione e barre di avanzamento non dicono niente a chi usa i modelli.
    registro.set_verbosity_error()
    registro.disable_progress_bar()
    try:
        return classe.from_pretrained(nome, cache_dir=MODELLI, local_files_only=True, **opzioni)
    except OSError:
        return classe.from_pretrained(nome, cache_dir=MODELLI, **opzioni)


def _leggi_csv(nome: str) -> list[dict[str, str]]:
    percorso = DATI / nome
    if not percorso.exists():
        raise FileNotFoundError(f"manca {percorso}: il laboratorio va aperto dentro il repository intero")
    with percorso.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _riquadro(riga: dict[str, str]) -> Riquadro:
    return float(riga["x0"]), float(riga["y0"]), float(riga["x1"]), float(riga["y1"])


# Dati


def fotogrammi() -> dict[str, str]:
    """Nome del file e gruppo, «giorno» o «notte»."""
    return {riga["file"]: riga["gruppo"] for riga in _leggi_csv("fotogrammi.csv")}


def veicoli_veri() -> dict[str, list[Riquadro]]:
    """I riquadri disegnati da persone (le annotazioni COCO): auto, camion e autobus, per fotogramma."""
    veri: dict[str, list[Riquadro]] = {file: [] for file in fotogrammi()}
    for riga in _leggi_csv("veicoli.csv"):
        veri[riga["file"]].append(_riquadro(riga))
    return veri


def apri(file: str) -> Image.Image:
    cartella = "fotogrammi" if file.startswith("F") else "targhe" if file.startswith("T") else "scansioni"
    return Image.open(DATI / cartella / file).convert("RGB")


def anteprima(immagine: Image.Image, larghezza: int = 640) -> Image.Image:
    """Una copia rimpicciolita, per guardarla nel notebook. Ai modelli va sempre l'originale."""
    copia = immagine.copy()
    copia.thumbnail((larghezza, larghezza))
    return copia


def striscia(file: list[str], altezza: int = 140) -> Image.Image:
    """I fotogrammi in fila, nell'ordine dato."""
    immagini = [apri(nome) for nome in file]
    immagini = [im.resize((im.width * altezza // im.height, altezza)) for im in immagini]
    fila = Image.new("RGB", (sum(im.width + 6 for im in immagini), altezza), "white")
    x = 0
    for im in immagini:
        fila.paste(im, (x, 0))
        x += im.width + 6
    return fila


# Parte 1 e 2: rilevamento


class ModelloDiRilevamento:
    """Un modello di rilevamento pre-addestrato: per ogni veicolo, un riquadro e un punteggio."""

    def __init__(self) -> None:
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self.preparatore = _carica(AutoImageProcessor, RILEVATORE)
        self.modello = _carica(AutoModelForObjectDetection, RILEVATORE).eval()

    def __call__(self, file: str, punteggio_minimo: float = min(SOGLIE)) -> list[tuple[Riquadro, float]]:
        immagine = apri(file)
        with torch.inference_mode():
            uscita = self.modello(**self.preparatore(images=immagine, return_tensors="pt"))
        trovati = self.preparatore.post_process_object_detection(
            uscita, threshold=punteggio_minimo, target_sizes=[immagine.size[::-1]]
        )[0]
        return [
            (tuple(round(v, 1) for v in riquadro.tolist()), round(float(punteggio), 3))
            for riquadro, punteggio, classe in zip(trovati["boxes"], trovati["scores"], trovati["labels"])
            if self.modello.config.id2label[int(classe)] in VEICOLI
        ]


def iou(a: Riquadro, b: Riquadro) -> float:
    """Intersezione su unione: 1 se i riquadri coincidono, 0 se non si toccano."""
    larghezza = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    altezza = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    comune = larghezza * altezza
    unione = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - comune
    return comune / unione if unione > 0 else 0.0


def confronta(previsti: list[tuple[Riquadro, float]], veri: list[Riquadro], soglia: float) -> dict[str, list]:
    """TP, FP e FN sopra la soglia. Dal punteggio più alto, ogni riquadro prende il vero libero più simile."""
    liberi = list(veri)
    esito: dict[str, list] = {"TP": [], "FP": [], "FN": []}
    for riquadro, punteggio in sorted(previsti, key=lambda p: -p[1]):
        if punteggio < soglia:
            continue
        migliore = max(liberi, key=lambda vero: iou(riquadro, vero), default=None)
        if migliore is not None and iou(riquadro, migliore) >= IOU_MINIMA:
            liberi.remove(migliore)
            esito["TP"].append(riquadro)
        else:
            esito["FP"].append(riquadro)
    esito["FN"] = liberi
    return esito


def misura(rilevamenti: dict[str, list], veri: dict[str, list[Riquadro]], soglia: float,
           file: list[str] | None = None) -> dict[str, float]:
    """Precisione e recall su un gruppo di fotogrammi (tutti, se `file` manca)."""
    conti = {"fotogrammi": 0, "oggetti": 0, "TP": 0, "FP": 0, "FN": 0}
    for nome in file if file is not None else list(veri):
        esito = confronta(rilevamenti[nome], veri[nome], soglia)
        conti["fotogrammi"] += 1
        conti["oggetti"] += len(veri[nome])
        for chiave in ("TP", "FP", "FN"):
            conti[chiave] += len(esito[chiave])
    allarmi = conti["TP"] + conti["FP"]
    conti["precisione"] = conti["TP"] / allarmi if allarmi else float("nan")
    conti["recall"] = conti["TP"] / conti["oggetti"] if conti["oggetti"] else float("nan")
    return conti


def disegna(file: str, previsti: list[tuple[Riquadro, float]], veri: list[Riquadro], soglia: float) -> Image.Image:
    """Verde: TP, il veicolo trovato. Rosso: FP, un falso allarme. Giallo: FN, il veicolo vero non trovato."""
    immagine = apri(file)
    disegno = ImageDraw.Draw(immagine)
    esito = confronta(previsti, veri, soglia)
    for chiave, colore in (("TP", "#00c853"), ("FP", "#ff1744"), ("FN", "#ffd600")):
        for riquadro in esito[chiave]:
            disegno.rectangle(riquadro, outline=colore, width=4)
    return immagine


# Parte 3: OCR


@dataclass(slots=True)
class Parola:
    testo: str
    confidenze: list[float]  # una per carattere
    centro_y: float
    x0: float
    altezza: float


class _Confidenza(float):
    """Il numero che docTR si aspetta per la parola (il minimo), con accanto quello di ogni carattere."""

    per_carattere: list[float]


class Lettore:
    """OCR in due passi (docTR): trova le zone di testo, poi le legge carattere per carattere.

    Il lettore (CRNN con CTC) dà a ogni passo una probabilità per ogni carattere; la confidenza di un carattere è la
    più alta tra i passi che lo scrivono. docTR la riassume in un numero per parola: qui si tiene anche quella.
    """

    def __init__(self) -> None:
        os.environ.setdefault("DOCTR_CACHE_DIR", str(MODELLI / "doctr"))  # letta da docTR quando lo si importa
        from doctr.models import ocr_predictor
        from doctr.models.recognition.crnn.pytorch import CTCPostProcessor

        class ConPerCarattere(CTCPostProcessor):
            def __call__(self, logit: torch.Tensor) -> list[tuple[str, float]]:
                probabilita, indici = logit.softmax(-1).max(-1)
                parole = []
                for passi, prob in zip(indici.tolist(), probabilita.tolist()):
                    caratteri, confidenze = [], []
                    for indice, gruppo in groupby(zip(passi, prob), key=lambda passo: passo[0]):
                        if indice != len(self.vocab):  # l'ultimo indice è il «vuoto» del CTC
                            caratteri.append(self.vocab[indice])
                            confidenze.append(max(p for _, p in gruppo))
                    confidenza = _Confidenza(min(prob))
                    confidenza.per_carattere = confidenze
                    parole.append(("".join(caratteri), confidenza))
                return parole

        self.ocr = ocr_predictor(pretrained=True)
        modello = self.ocr.reco_predictor.model
        modello.postprocessor = ConPerCarattere(modello.vocab)

    def __call__(self, percorso: Path | str) -> list[list[Parola]]:
        """Le righe lette, dall'alto in basso, ognuna da sinistra a destra."""
        pagina = np.asarray(Image.open(percorso).convert("RGB"))
        parole = []
        for blocco in self.ocr([pagina]).pages[0].blocks:
            for riga in blocco.lines:
                for parola in riga.words:
                    (x0, y0), (_, y1) = parola.geometry
                    confidenze = getattr(parola.confidence, "per_carattere", None)
                    if confidenze is None or len(confidenze) != len(parola.value):  # parola spezzata e ricomposta
                        confidenze = [float(parola.confidence)] * len(parola.value)
                    parole.append(Parola(parola.value, confidenze, (y0 + y1) / 2, x0, y1 - y0))
        righe: list[list[Parola]] = []
        for parola in sorted(parole, key=lambda p: p.centro_y):
            ultima = righe[-1][-1] if righe else None
            if ultima and abs(parola.centro_y - ultima.centro_y) < 0.5 * min(parola.altezza, ultima.altezza):
                righe[-1].append(parola)
            else:
                righe.append([parola])
        return [sorted(riga, key=lambda p: p.x0) for riga in righe]


def testo(righe: list[list[Parola]], soglia: float | None = None) -> str:
    """Il testo letto. Con una soglia, i caratteri incerti stanno tra parentesi quadre: «9[0]9»."""

    def scrivi(parola: Parola) -> str:
        if soglia is None:
            return parola.testo
        return "".join(f"[{c}]" if p < soglia else c for c, p in zip(parola.testo, parola.confidenze))

    return "\n".join(" ".join(scrivi(parola) for parola in riga) for riga in righe)


def _distanza(a: str, b: str) -> int:
    """Quanti caratteri cambiare, aggiungere o togliere per passare da `a` a `b` (Levenshtein)."""
    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        corrente = [i]
        for j, cb in enumerate(b, 1):
            corrente.append(min(precedente[j] + 1, corrente[j - 1] + 1, precedente[j - 1] + (ca != cb)))
        precedente = corrente
    return precedente[-1]


def cer(letto: str, vero: str) -> float:
    """Il tasso di errore sui caratteri: sostituiti, cancellati e inseriti, diviso i caratteri veri."""
    letto, vero = " ".join(letto.split()), " ".join(vero.split())
    return _distanza(letto, vero) / len(vero)


def iban_letto(letto: str, iban_vero: str) -> str:
    """Il pezzo del testo letto, spazi tolti, che somiglia di più all'IBAN vero. Può avere qualche carattere in più
    o in meno: l'OCR a volte ne aggiunge o ne perde uno."""
    compatto, cercato = re.sub(r"\s", "", letto), re.sub(r"\s", "", iban_vero)
    pezzi = [
        compatto[inizio:inizio + lunghezza]
        for lunghezza in range(len(cercato) - 3, len(cercato) + 4)
        for inizio in range(max(1, len(compatto) - lunghezza + 1))
    ]
    return min(pezzi, key=lambda pezzo: (_distanza(pezzo, cercato), abs(len(pezzo) - len(cercato))))


def riga_letta(righe: list[list[Parola]], inizio: str) -> str:
    """La riga letta che comincia con `inizio`, per esempio la data di un movimento; se non c'è, tutto il testo."""
    return next((riga for riga in testo(righe).splitlines() if riga.startswith(inizio)), testo(righe))


def differenze(letto: str, vero: str) -> int:
    """Quanti caratteri cambiare, aggiungere o togliere: 0 vuol dire corrispondenza esatta."""
    return _distanza(re.sub(r"\s", "", letto), re.sub(r"\s", "", vero))


def iban_vero(numero_riga: int) -> str:
    """L'IBAN scritto in una riga di DOC-05, l'estratto conto del fascicolo."""
    riga = (FASCICOLO / "core" / "DOC-05-estratto-conto.csv").read_text(encoding="utf-8").splitlines()[numero_riga - 1]
    return next(csv.reader([riga]))[3]


def incerti(righe: list[list[Parola]], soglia: float = SOGLIA_INCERTO) -> list[tuple[str, str, float]]:
    """I caratteri sotto la soglia: (parola, carattere, confidenza). Sono quelli da far controllare a una persona."""
    return [
        (parola.testo, carattere, round(confidenza, 2))
        for riga in righe for parola in riga
        for carattere, confidenza in zip(parola.testo, parola.confidenze) if confidenza < soglia
    ]


# Parte 4: ricerca per immagini


class Ricerca:
    """Testo e immagini nello stesso spazio: una frase trova i fotogrammi con i vettori più vicini."""

    def __init__(self) -> None:
        from transformers import AutoModel, AutoProcessor

        self.preparatore = _carica(AutoProcessor, RICERCA)
        self.modello = _carica(AutoModel, RICERCA).eval()
        self.file: list[str] = []
        self.vettori = torch.empty(0)

    def indicizza(self, file: list[str]) -> torch.Tensor:
        with torch.inference_mode():
            vettori = self.modello.get_image_features(
                **self.preparatore(images=[apri(nome) for nome in file], return_tensors="pt")
            )
        self.file, self.vettori = list(file), torch.nn.functional.normalize(_tensore(vettori), dim=-1)
        return self.vettori

    def cerca(self, frase: str, k: int = 5) -> list[tuple[str, float]]:
        with torch.inference_mode():
            vettore = self.modello.get_text_features(
                **self.preparatore(text=[frase.lower()], padding="max_length", max_length=64, return_tensors="pt")
            )
        somiglianze = (self.vettori @ torch.nn.functional.normalize(_tensore(vettore), dim=-1).T).squeeze(1)
        primi = somiglianze.argsort(descending=True)[:k]
        return [(self.file[i], round(float(somiglianze[i]), 3)) for i in primi]


def _tensore(uscita) -> torch.Tensor:
    """Alcune versioni di transformers restituiscono il vettore dentro un oggetto, altre il vettore e basta."""
    return uscita if isinstance(uscita, torch.Tensor) else uscita.pooler_output


# Parte 5: VLM


def targhe() -> list[dict]:
    """Le tre foto con la targa di fantasia: il file, la targa vera e il suo riquadro in pixel."""
    return [
        {"file": riga["file"], "targa": riga["targa"], "riquadro": _riquadro(riga)}
        for riga in _leggi_csv("targhe.csv")
    ]


def ritaglio(file: str, riquadro: Riquadro, margine: float = 1.0) -> Image.Image:
    """Il pezzo di foto intorno al riquadro, alla risoluzione piena: niente viene rimpicciolito."""
    x0, y0, x1, y1 = riquadro
    dx, dy = (x1 - x0) * margine, (y1 - y0) * margine
    immagine = apri(file)
    larghezza, altezza = immagine.size
    sinistra, alto = max(0, int(x0 - dx)), max(0, int(y0 - dy))
    return immagine.crop((sinistra, alto, min(larghezza, int(x1 + dx)), min(altezza, int(y1 + dy))))


class ModelloVisivo:
    """Un modello visivo-linguistico (VLM) piccolo: un'immagine e una domanda, una risposta in parole.

    L'immagine intera viene rimpicciolita a 512 pixel sul lato lungo prima di entrare nel modello: è ciò che fanno
    molti VLM, e una targa lontana diventa pochi pixel.
    """

    def __init__(self) -> None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.preparatore = _carica(AutoProcessor, VLM)
        self.modello = _carica(AutoModelForImageTextToText, VLM, dtype=torch.float32).eval()

    def chiedi(self, immagine: Image.Image, domanda: str) -> str:
        messaggi = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": domanda}]}]
        prompt = self.preparatore.apply_chat_template(messaggi, add_generation_prompt=True)
        ingresso = self.preparatore(text=prompt, images=[immagine], return_tensors="pt", do_image_splitting=False)
        with torch.inference_mode():
            uscita = self.modello.generate(**ingresso, max_new_tokens=24, do_sample=False)
        risposta = uscita[:, ingresso["input_ids"].shape[1]:]
        return self.preparatore.batch_decode(risposta, skip_special_tokens=True)[0].strip()


def scarica_modelli() -> None:
    """Scarica i quattro modelli in `.modelli/` (2,1 GB), così in aula non serve la rete."""
    modelli = {"rilevamento": ModelloDiRilevamento, "OCR": Lettore, "ricerca": Ricerca, "VLM": ModelloVisivo}
    for nome, classe in modelli.items():
        classe()
        print(f"{nome}: pronto")
