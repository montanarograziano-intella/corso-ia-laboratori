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

Riquadro = tuple[float, float, float, float]  # in pixel: sinistra, alto, destra, basso

# PyTorch avvisa su macOS che una funzione che il notebook non usa manca: il livello lo reimposta lui, va spento.
logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").disabled = True


def _carica_modello(classe, nome: str, **opzioni):
    """Dalla cartella `.modelli/` senza rete, se il modello c'è già; altrimenti lo scarica, una volta."""
    from transformers.utils import logging as transformers_logging

    # Avvisi di configurazione e barre di avanzamento non dicono niente a chi usa i modelli.
    transformers_logging.set_verbosity_error()
    transformers_logging.disable_progress_bar()
    try:
        return classe.from_pretrained(nome, cache_dir=MODELLI, local_files_only=True, **opzioni)
    except OSError:
        return classe.from_pretrained(nome, cache_dir=MODELLI, **opzioni)


def _leggi_csv(nome: str) -> list[dict[str, str]]:
    """Le righe di un file CSV di `dati/`, ognuna come dizionario colonna → valore."""
    percorso = DATI / nome
    if not percorso.exists():
        raise FileNotFoundError(f"manca {percorso}: il laboratorio va aperto dentro il repository intero")
    with percorso.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _riquadro_dalla_riga(riga: dict[str, str]) -> Riquadro:
    """Il riquadro scritto nelle colonne x0, y0, x1, y1 di una riga CSV."""
    return float(riga["x0"]), float(riga["y0"]), float(riga["x1"]), float(riga["y1"])


# Dati


def fotogrammi() -> dict[str, str]:
    """Nome del file e gruppo, «giorno» o «notte»."""
    return {riga["file"]: riga["gruppo"] for riga in _leggi_csv("fotogrammi.csv")}


def veicoli_veri() -> dict[str, list[Riquadro]]:
    """I riquadri disegnati da persone (le annotazioni COCO): auto, camion e autobus, per fotogramma."""
    veri: dict[str, list[Riquadro]] = {file: [] for file in fotogrammi()}
    for riga in _leggi_csv("veicoli.csv"):
        veri[riga["file"]].append(_riquadro_dalla_riga(riga))
    return veri


def apri_immagine(file: str) -> Image.Image:
    """Un fotogramma (F…), una foto di targa (T…) o una scansione, dal nome del file."""
    cartella = "fotogrammi" if file.startswith("F") else "targhe" if file.startswith("T") else "scansioni"
    return Image.open(DATI / cartella / file).convert("RGB")


def anteprima(immagine: Image.Image, larghezza: int = 640) -> Image.Image:
    """Una copia rimpicciolita, per guardarla nel notebook. Ai modelli va sempre l'originale."""
    copia = immagine.copy()
    copia.thumbnail((larghezza, larghezza))
    return copia


def affianca_fotogrammi(file: list[str], altezza: int = 140) -> Image.Image:
    """I fotogrammi in fila, nell'ordine dato, tutti alla stessa altezza."""
    immagini = [apri_immagine(nome) for nome in file]
    immagini = [im.resize((im.width * altezza // im.height, altezza)) for im in immagini]
    fila = Image.new("RGB", (sum(im.width + 6 for im in immagini), altezza), "white")
    x = 0
    for im in immagini:
        fila.paste(im, (x, 0))
        x += im.width + 6  # 6 pixel bianchi tra un fotogramma e l'altro
    return fila


# Parte 1 e 2: rilevamento


class ModelloDiRilevamento:
    """Un modello di rilevamento pre-addestrato: per ogni veicolo, un riquadro e un punteggio."""

    def __init__(self) -> None:
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self.preparatore = _carica_modello(AutoImageProcessor, RILEVATORE)
        self.modello = _carica_modello(AutoModelForObjectDetection, RILEVATORE).eval()

    def __call__(self, file: str, punteggio_minimo: float = min(SOGLIE)) -> list[tuple[Riquadro, float]]:
        """I veicoli trovati nel fotogramma con punteggio da `punteggio_minimo` in su: (riquadro, punteggio)."""
        immagine = apri_immagine(file)
        with torch.inference_mode():
            uscita = self.modello(**self.preparatore(images=immagine, return_tensors="pt"))
        trovati = self.preparatore.post_process_object_detection(
            uscita, threshold=punteggio_minimo, target_sizes=[immagine.size[::-1]]
        )[0]
        # Il modello trova tutte le 80 classi di COCO: si tengono solo auto, camion e autobus.
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


def classifica_riquadri(previsti: list[tuple[Riquadro, float]], veri: list[Riquadro], soglia: float) -> dict[str, list]:
    """TP, FP e FN sopra la soglia. Dal punteggio più alto, ogni riquadro prende il vero libero più simile."""
    veri_liberi = list(veri)
    esiti: dict[str, list] = {"TP": [], "FP": [], "FN": []}
    for riquadro, punteggio in sorted(previsti, key=lambda p: -p[1]):
        if punteggio < soglia:
            continue
        migliore = max(veri_liberi, key=lambda vero: iou(riquadro, vero), default=None)
        if migliore is not None and iou(riquadro, migliore) >= IOU_MINIMA:
            # Un veicolo vero conta una volta sola: un secondo riquadro sullo stesso veicolo è un FP.
            veri_liberi.remove(migliore)
            esiti["TP"].append(riquadro)
        else:
            esiti["FP"].append(riquadro)
    esiti["FN"] = veri_liberi
    return esiti


def misura_rilevamento(
    rilevamenti: dict[str, list], veri: dict[str, list[Riquadro]], soglia: float, file: list[str] | None = None
) -> dict[str, float]:
    """Conteggi, precisione e recall su un gruppo di fotogrammi (tutti, se `file` manca)."""
    conteggi = {"fotogrammi": 0, "veicoli": 0, "TP": 0, "FP": 0, "FN": 0}
    for nome in file if file is not None else list(veri):
        esiti = classifica_riquadri(rilevamenti[nome], veri[nome], soglia)
        conteggi["fotogrammi"] += 1
        conteggi["veicoli"] += len(veri[nome])
        for chiave in ("TP", "FP", "FN"):
            conteggi[chiave] += len(esiti[chiave])
    allarmi = conteggi["TP"] + conteggi["FP"]
    conteggi["precisione"] = conteggi["TP"] / allarmi if allarmi else float("nan")
    conteggi["recall"] = conteggi["TP"] / conteggi["veicoli"] if conteggi["veicoli"] else float("nan")
    return conteggi


def _contorna(immagine: Image.Image, riquadro: Riquadro, colore: str) -> None:
    """Un contorno sottile appena fuori dal riquadro, per non coprire gli oggetti piccoli."""
    spessore = max(immagine.size) // 320  # 2 pixel su una foto di 640, 6 su una ingrandita tre volte
    x0, y0, x1, y1 = riquadro
    fuori = (x0 - spessore, y0 - spessore, x1 + spessore, y1 + spessore)
    ImageDraw.Draw(immagine).rectangle(fuori, outline=colore, width=spessore)


def disegna_riquadri(file: str, riquadri: list[Riquadro]) -> Image.Image:
    """I riquadri veri in blu, prima di qualunque modello."""
    immagine = apri_immagine(file)
    for riquadro in riquadri:
        _contorna(immagine, riquadro, "#2979ff")
    return immagine


def disegna_esiti(
    file: str, previsti: list[tuple[Riquadro, float]], veri: list[Riquadro], soglia: float
) -> Image.Image:
    """Verde: TP, il veicolo trovato. Rosso: FP, un falso allarme. Giallo: FN, il veicolo vero non trovato."""
    immagine = apri_immagine(file)
    esiti = classifica_riquadri(previsti, veri, soglia)
    for chiave, colore in (("TP", "#00c853"), ("FP", "#ff1744"), ("FN", "#ffd600")):
        for riquadro in esiti[chiave]:
            _contorna(immagine, riquadro, colore)
    return immagine


# Parte 3: OCR


@dataclass(slots=True)
class Parola:
    """Una parola letta dall'OCR, con la sua posizione sulla pagina (in frazioni di pagina, da 0 a 1)."""

    testo: str
    confidenze: list[float]  # una per carattere
    centro_y: float
    x0: float
    altezza: float


class _Confidenza(float):
    """Il numero che docTR si aspetta per la parola (il minimo), con accanto quello di ogni carattere."""

    per_carattere: list[float]


class LettoreOCR:
    """OCR in due passi (docTR): trova le zone di testo, poi le legge carattere per carattere.

    Il lettore (CRNN con CTC) dà a ogni passo una probabilità per ogni carattere; la confidenza di un carattere è la
    più alta tra i passi che lo scrivono. docTR la riassume in un numero per parola: qui si tiene anche quella.
    """

    def __init__(self) -> None:
        os.environ.setdefault("DOCTR_CACHE_DIR", str(MODELLI / "doctr"))  # letta da docTR quando lo si importa
        from doctr.models import ocr_predictor
        from doctr.models.recognition.crnn.pytorch import CTCPostProcessor

        class CTCConConfidenzaPerCarattere(CTCPostProcessor):
            """Il post-processore di docTR che, oltre alla parola, tiene la confidenza di ogni carattere."""

            def __call__(self, logit: torch.Tensor) -> list[tuple[str, float]]:
                probabilita, indici = logit.softmax(-1).max(-1)
                parole = []
                for passi, prob in zip(indici.tolist(), probabilita.tolist()):
                    caratteri, confidenze = [], []
                    # I passi consecutivi con lo stesso indice scrivono un carattere solo.
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
        modello.postprocessor = CTCConConfidenzaPerCarattere(modello.vocab)

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
        # docTR divide la pagina in blocchi: si ricompongono le righe della pagina dall'altezza delle parole.
        righe: list[list[Parola]] = []
        for parola in sorted(parole, key=lambda p: p.centro_y):
            ultima = righe[-1][-1] if righe else None
            if ultima and abs(parola.centro_y - ultima.centro_y) < 0.5 * min(parola.altezza, ultima.altezza):
                righe[-1].append(parola)
            else:
                righe.append([parola])
        return [sorted(riga, key=lambda p: p.x0) for riga in righe]


def testo_letto(righe: list[list[Parola]], soglia: float | None = None) -> str:
    """Il testo letto. Con una soglia, i caratteri incerti stanno tra parentesi quadre: «9[0]9»."""

    def scrivi(parola: Parola) -> str:
        if soglia is None:
            return parola.testo
        return "".join(f"[{c}]" if p < soglia else c for c, p in zip(parola.testo, parola.confidenze))

    return "\n".join(" ".join(scrivi(parola) for parola in riga) for riga in righe)


def _distanza_di_levenshtein(a: str, b: str) -> int:
    """Quanti caratteri cambiare, aggiungere o togliere per passare da `a` a `b`."""
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
    return _distanza_di_levenshtein(letto, vero) / len(vero)


def iban_piu_simile(letto: str, iban_vero: str) -> str:
    """Il pezzo del testo letto, spazi tolti, che somiglia di più all'IBAN vero. Può avere qualche carattere in più
    o in meno: l'OCR a volte ne aggiunge o ne perde uno."""
    compatto, cercato = re.sub(r"\s", "", letto), re.sub(r"\s", "", iban_vero)
    # Tutti i pezzi lunghi quanto l'IBAN, con fino a tre caratteri in più o in meno.
    pezzi = [
        compatto[inizio : inizio + lunghezza]
        for lunghezza in range(len(cercato) - 3, len(cercato) + 4)
        for inizio in range(max(1, len(compatto) - lunghezza + 1))
    ]
    return min(pezzi, key=lambda pezzo: (_distanza_di_levenshtein(pezzo, cercato), abs(len(pezzo) - len(cercato))))


def riga_che_inizia_con(righe: list[list[Parola]], inizio: str) -> str:
    """La riga letta che comincia con `inizio`, per esempio la data di un movimento; se non c'è, tutto il testo."""
    testo = testo_letto(righe)
    return next((riga for riga in testo.splitlines() if riga.startswith(inizio)), testo)


def caratteri_da_correggere(letto: str, vero: str) -> int:
    """Quanti caratteri cambiare, aggiungere o togliere, spazi esclusi: 0 vuol dire corrispondenza esatta."""
    return _distanza_di_levenshtein(re.sub(r"\s", "", letto), re.sub(r"\s", "", vero))


def iban_vero(numero_riga: int) -> str:
    """L'IBAN scritto in una riga del CSV di DOC-05, l'estratto conto del fascicolo (la riga 1 è l'intestazione)."""
    riga = (FASCICOLO / "core" / "DOC-05-estratto-conto.csv").read_text(encoding="utf-8").splitlines()[numero_riga - 1]
    return next(csv.reader([riga]))[3]


def caratteri_incerti(righe: list[list[Parola]], soglia: float = SOGLIA_INCERTO) -> list[tuple[str, str, float]]:
    """I caratteri sotto la soglia: (parola, carattere, confidenza). Sono quelli da far controllare a una persona."""
    return [
        (parola.testo, carattere, round(confidenza, 2))
        for riga in righe
        for parola in riga
        for carattere, confidenza in zip(parola.testo, parola.confidenze)
        if confidenza < soglia
    ]


# Parte 4: ricerca per immagini


class RicercaPerImmagini:
    """Testo e immagini nello stesso spazio: una frase trova i fotogrammi con i vettori più vicini."""

    def __init__(self) -> None:
        from transformers import AutoModel, AutoProcessor

        self.preparatore = _carica_modello(AutoProcessor, RICERCA)
        self.modello = _carica_modello(AutoModel, RICERCA).eval()
        self.file: list[str] = []
        self.vettori = torch.empty(0)

    def indicizza(self, file: list[str]) -> torch.Tensor:
        """Trasforma ogni fotogramma in un vettore di lunghezza 1 e li tiene per le ricerche."""
        with torch.inference_mode():
            vettori = self.modello.get_image_features(
                **self.preparatore(images=[apri_immagine(nome) for nome in file], return_tensors="pt")
            )
        self.file, self.vettori = list(file), torch.nn.functional.normalize(_come_tensore(vettori), dim=-1)
        return self.vettori

    def cerca(self, frase: str, k: int = 5) -> list[tuple[str, float]]:
        """I `k` fotogrammi più vicini alla frase, dal più vicino: (file, somiglianza del coseno)."""
        with torch.inference_mode():
            vettore = self.modello.get_text_features(
                **self.preparatore(text=[frase.lower()], padding="max_length", max_length=64, return_tensors="pt")
            )
        # Tra vettori di lunghezza 1, il prodotto scalare è la somiglianza del coseno.
        somiglianze = (self.vettori @ torch.nn.functional.normalize(_come_tensore(vettore), dim=-1).T).squeeze(1)
        primi = somiglianze.argsort(descending=True)[:k]
        return [(self.file[i], round(float(somiglianze[i]), 3)) for i in primi]


def _come_tensore(uscita) -> torch.Tensor:
    """Alcune versioni di transformers restituiscono il vettore dentro un oggetto, altre il vettore e basta."""
    return uscita if isinstance(uscita, torch.Tensor) else uscita.pooler_output


# Parte 5: VLM


def targhe_di_fantasia() -> list[dict]:
    """Le tre foto con la targa di fantasia: il file, la targa vera e il suo riquadro in pixel."""
    return [
        {"file": riga["file"], "targa": riga["targa"], "riquadro": _riquadro_dalla_riga(riga)}
        for riga in _leggi_csv("targhe.csv")
    ]


def ritaglia_intorno(file: str, riquadro: Riquadro, margine: float = 1.0) -> Image.Image:
    """Il pezzo di foto intorno al riquadro, alla risoluzione piena: niente viene rimpicciolito.

    `margine` è lo spazio aggiunto su ogni lato, in multipli della larghezza e dell'altezza del riquadro.
    """
    x0, y0, x1, y1 = riquadro
    dx, dy = (x1 - x0) * margine, (y1 - y0) * margine
    immagine = apri_immagine(file)
    larghezza, altezza = immagine.size
    sinistra, alto = max(0, int(x0 - dx)), max(0, int(y0 - dy))
    return immagine.crop((sinistra, alto, min(larghezza, int(x1 + dx)), min(altezza, int(y1 + dy))))


class ModelloVisivoLinguistico:
    """Un modello visivo-linguistico (VLM) piccolo: un'immagine e una domanda, una risposta in parole.

    L'immagine intera viene rimpicciolita a 512 pixel sul lato lungo prima di entrare nel modello: è ciò che fanno
    molti VLM, e una targa lontana diventa pochi pixel.
    """

    def __init__(self) -> None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.preparatore = _carica_modello(AutoProcessor, VLM)
        self.modello = _carica_modello(AutoModelForImageTextToText, VLM, dtype=torch.float32).eval()

    def chiedi(self, immagine: Image.Image, domanda: str) -> str:
        """La risposta del modello alla domanda sull'immagine, al massimo 24 token, sempre la stessa."""
        messaggi = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": domanda}]}]
        prompt = self.preparatore.apply_chat_template(messaggi, add_generation_prompt=True)
        # Senza suddivisione l'immagine entra intera, rimpicciolita: una targa lontana resta di pochi pixel.
        ingresso = self.preparatore(text=prompt, images=[immagine], return_tensors="pt", do_image_splitting=False)
        with torch.inference_mode():
            uscita = self.modello.generate(**ingresso, max_new_tokens=24, do_sample=False)
        risposta = uscita[:, ingresso["input_ids"].shape[1] :]  # solo i token nuovi, senza la domanda
        return self.preparatore.batch_decode(risposta, skip_special_tokens=True)[0].strip()


def scarica_modelli() -> None:
    """Scarica i quattro modelli in `.modelli/` (2,1 GB), così in aula non serve la rete."""
    modelli = {
        "rilevamento": ModelloDiRilevamento,
        "OCR": LettoreOCR,
        "ricerca": RicercaPerImmagini,
        "VLM": ModelloVisivoLinguistico,
    }
    for nome, classe in modelli.items():
        classe()
        print(f"{nome}: pronto")
