"""Costruisce la cartella `dati/` del notebook: per i docenti, una volta, con la rete. I partecipanti non lo eseguono.

    uv run prepara_dati.py

Che cosa scrive:

- `dati/fotogrammi/`: 29 foto di strade e parcheggi del set di validazione COCO 2017, 24 di giorno e 5 di notte o al
  crepuscolo, con licenza CC BY 2.0 o CC BY-SA 2.0. Le persone e le targhe vere sono sfocate.
  `dati/veicoli.csv` ha i riquadri veri (auto, camion, autobus) dalle annotazioni COCO (CC BY 4.0).
- `dati/targhe/`: tre foto ingrandite tre volte, con una targa di fantasia, non valida, al posto di quella vera.
- `dati/scansioni/`: DOC-01, DOC-05 e DOC-10 del fascicolo stampati come scansioni, con timbro, sfocatura e rumore,
  e accanto il testo vero di ciascuna.
- `dati/crediti.csv`: l'autore, la pagina Flickr, la licenza e le modifiche di ogni foto.

Le foto di COCO si scaricano da images.cocodataset.org (in https, dal suo indirizzo S3), il carattere delle
scansioni (DejaVu Sans) da GitHub.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import random
import tarfile
import textwrap
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

QUI = Path(__file__).resolve().parent
DATI = QUI / "dati"
FASCICOLO = QUI.parents[2] / "data" / "case-file" / "core"
SCARICATI = QUI / ".scaricati"
os.environ.setdefault("DOCTR_CACHE_DIR", str(QUI / ".modelli" / "doctr"))

# images.cocodataset.org è un bucket S3: in https risponde solo con il suo indirizzo S3.
COCO = ("http://images.cocodataset.org/", "https://s3.amazonaws.com/images.cocodataset.org/")
ANNOTAZIONI = COCO[1] + "annotations/annotations_trainval2017.zip"
# Il carattere di Pillow non ha le lettere accentate: le stamperebbe come quadratini.
DEJAVU = ("https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2",
          "fa9ca4d13871dd122f61258a80d01751d603b4d3ee14095d65453b4e846e17d7")
VEICOLI = {"car", "truck", "bus"}
LICENZE = {4: ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/"),
           5: ("CC BY-SA 2.0", "https://creativecommons.org/licenses/by-sa/2.0/")}
# Scelte a mano tra le foto di validazione COCO con licenza CC BY o CC BY-SA e almeno due veicoli: strade e
# parcheggi, persone lontane. Di notte ce ne sono solo cinque: è il punto della slide 43.
GIORNO = [423617, 429109, 196759, 148719, 85376, 78823, 124798, 356169, 542625, 326627, 142472, 566758,
          362682, 531036, 89556, 452321, 227511, 369751, 550691, 568290, 284725, 514376, 393226, 93154]
NOTTE = [170545, 269632, 84170, 176037, 225532]
# Targhe e volti che il rilevatore di testo non trova, in pixel della foto COCO: controllati a occhio, uno per uno.
DA_SFOCARE = {
    89556: [(196, 330, 226, 358)], 227511: [(102, 333, 134, 352)], 393226: [(536, 243, 562, 260)],
    176037: [(400, 258, 430, 278), (458, 235, 496, 272)], 142472: [(212, 408, 241, 421)],
    550691: [(130, 314, 158, 327)], 423617: [(520, 440, 556, 462)], 138979: [(164, 297, 190, 320)],
    85376: [(366, 356, 422, 380), (455, 385, 480, 402)], 542625: [(449, 179, 473, 194), (615, 180, 637, 194)],
    124798: [(421, 332, 441, 342), (506, 329, 519, 338), (558, 323, 572, 333), (471, 328, 482, 336)],
    284725: [(146, 336, 168, 354), (74, 264, 91, 281)],
}
# Il nome che Flickr mostra per l'autore, letto sulla pagina di ogni foto il 20/11/2026. Quelle che mancano non sono
# più su Flickr: si cita COCO.
AUTORI = {  # cspell:disable
    423617: "SgTransport", 429109: "Oran Viriyincy", 196759: "Rusty Clark ~ 100K Photos", 148719: "dave_7",
    85376: "Isha Zubeidi", 78823: "Dan Phiffer", 124798: "J", 356169: "Doug Kerr", 542625: "Paul Sableman",
    326627: "Kristian Thøgersen", 142472: "Elliott Brown", 566758: "Paul Sableman", 362682: "Selmer van Alten",
    531036: "Elliott Brown", 452321: "Aubrey", 227511: "Jamie", 369751: "Carl Lacey", 550691: "Aubrey",
    568290: "Alfenaar", 284725: "bfishadow", 514376: "Yuri Levchenko", 393226: "Mr. Brian", 93154: "Oran Viriyincy",
    170545: "Brian Rawson-Ketchum", 84170: "SgTransport", 176037: "Metropolitan Transportation Authority",
    225532: "Jason McHuff", 57149: "Jack",
}  # cspell:enable
# Targhe di fantasia nel formato italiano, con lettere che le targhe italiane non usano (I, O, Q, U), ciascuna sopra
# la targa vera della foto (riquadro in pixel della foto COCO, misurato a occhio).
TARGHE = {
    57149: ("AQ 482 UO", (355, 334, 391, 355)),
    206487: ("QI 715 XO", (562, 340, 620, 369)),
    138979: ("UO 309 KQ", (403, 323, 453, 356)),
}
INGRANDIMENTO = 3
SCANSIONI = {"DOC-01": "DOC-01-denuncia-neri.txt", "DOC-05": "DOC-05-estratto-conto.csv",
             "DOC-10": "DOC-10-comunicazione-banca.txt"}


def scarica(url: str) -> bytes:
    url = url.replace(*COCO, 1)
    richiesta = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(richiesta, timeout=60) as risposta:
        return risposta.read()


def annotazioni_coco() -> dict:
    SCARICATI.mkdir(exist_ok=True)
    archivio = SCARICATI / "annotations_trainval2017.zip"
    if not archivio.exists():
        archivio.write_bytes(scarica(ANNOTAZIONI))
    with zipfile.ZipFile(archivio) as z:
        return json.loads(z.read("annotations/instances_val2017.json"))


def carattere_scansioni(corpo: int) -> ImageFont.FreeTypeFont:
    file = SCARICATI / "DejaVuSans.ttf"
    if not file.exists():
        url, impronta = DEJAVU
        archivio = scarica(url)
        if hashlib.sha256(archivio).hexdigest() != impronta:
            raise RuntimeError(f"{url} non è l'archivio atteso")
        with tarfile.open(fileobj=io.BytesIO(archivio), mode="r:bz2") as tar:
            SCARICATI.mkdir(exist_ok=True)
            file.write_bytes(tar.extractfile("dejavu-fonts-ttf-2.37/ttf/DejaVuSans.ttf").read())
    return ImageFont.truetype(file, corpo)


def credito(id_: int, meta: dict, file: str, modifiche: str) -> dict:
    """Autore e pagina Flickr, la citazione chiesta da CC BY; per le foto tolte da Flickr, la pagina COCO."""
    if id_ in AUTORI:
        autore, pagina = AUTORI[id_], pagina_flickr(meta["flickr_url"])
    else:
        autore, pagina = "non indicato, foto tolta da Flickr", f"https://cocodataset.org/#explore?id={id_}"
    return {"file": file, "coco_id": id_, "autore": autore, "pagina": pagina, "licenza": LICENZE[meta["license"]][0],
            "licenza_url": LICENZE[meta["license"]][1], "modifiche": modifiche}


def pagina_flickr(flickr_url: str) -> str:
    """Il collegamento stabile alla foto su Flickr, che porta alla pagina dell'autore: la citazione chiesta da CC BY."""
    return f"https://www.flickr.com/photo.gne?id={flickr_url.rsplit('/', 1)[1].split('_')[0]}"


def sfoca(im: Image.Image, riquadri: list[tuple[float, float, float, float]]) -> Image.Image:
    for x0, y0, x1, y1 in riquadri:
        x0, y0, x1, y1 = (round(v) for v in (x0, y0, x1, y1))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        zona = im.crop((x0, y0, x1, y1))
        raggio = max(4, min(x1 - x0, y1 - y0) // 3)
        im.paste(zona.resize((max(1, (x1 - x0) // 8), max(1, (y1 - y0) // 8))).resize(zona.size).filter(
            ImageFilter.GaussianBlur(raggio)), (x0, y0))
    return im


def scritte_sui_veicoli(rilevatore, im: Image.Image, veicoli: list[tuple]) -> list[tuple]:
    """Riquadri di testo con la forma di una targa, nella parte bassa di un veicolo: si sfocano."""
    W, H = im.size
    pagina = rilevatore([np.asarray(im)])[0]
    scritte = []
    for (x0, y0), (x1, y1) in (b[:4].reshape(2, 2) for b in pagina["words"]):
        x0, x1, y0, y1 = x0 * W, x1 * W, y0 * H, y1 * H
        cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        for vx0, vy0, vx1, vy1 in veicoli:
            dentro = vx0 <= cx <= vx1 and vy0 + 0.25 * (vy1 - vy0) <= cy <= vy1
            if dentro and 1.2 <= w / max(h, 1) <= 8 and w <= 0.5 * (vx1 - vx0):
                scritte.append((x0 - 0.2 * w, y0 - 0.4 * h, x1 + 0.2 * w, y1 + 0.4 * h))
                break
    return scritte


def targa(testo: str, larghezza: int, altezza: int) -> Image.Image:
    im = Image.new("RGB", (larghezza, altezza), "white")
    d = ImageDraw.Draw(im)
    blu, fascia = (0, 51, 153), int(larghezza * 0.08)
    d.rectangle([0, 0, larghezza - 1, altezza - 1], outline="black", width=max(1, altezza // 28))
    d.rectangle([3, 3, fascia, altezza - 4], fill=blu)
    d.rectangle([larghezza - fascia, 3, larghezza - 4, altezza - 4], fill=blu)
    d.text((fascia // 2, int(altezza * 0.75)), "I", font=ImageFont.load_default(size=int(fascia * 0.7)), fill="white",
           anchor="mm")
    corpo = int(altezza * 0.7)
    while d.textlength(testo, font=ImageFont.load_default(size=corpo)) > (larghezza - 2 * fascia) * 0.92:
        corpo -= 1
    d.text((larghezza // 2, altezza // 2), testo, font=ImageFont.load_default(size=corpo), fill="black", anchor="mm")
    return im


def righe_del_documento(documento: str) -> list[str]:
    """Il testo come lo si stampa: le righe dei documenti, e l'estratto conto DOC-05 come una tabella."""
    righe = (FASCICOLO / SCANSIONI[documento]).read_text(encoding="utf-8").splitlines()
    if documento != "DOC-05":
        return [pezzo for riga in righe for pezzo in (textwrap.wrap(riga, 84) or [""])]
    intestazione = [riga.lstrip("# ") for riga in righe if riga.startswith("#")]
    tabella = list(csv.reader(riga for riga in righe if not riga.startswith("#")))
    titoli = ["Data", "Descrizione", "Importo", "IBAN destinatario"]
    return [pezzo for riga in intestazione for pezzo in textwrap.wrap(riga, 84)] + [""] + [
        f"{a:<12}{b:<22}{c:>10}   {d}".rstrip() for a, b, c, d in [titoli] + tabella[1:]
    ]


def scansione(righe: list[str], seme: int) -> Image.Image:
    caso = random.Random(seme)
    larghezza, altezza = 1240, 1754  # A4 a 150 punti per pollice
    pagina = Image.new("RGB", (larghezza, altezza), (246, 245, 240))
    d = ImageDraw.Draw(pagina)
    carattere = carattere_scansioni(22)  # stessa larghezza di riga del carattere di Pillow a 24
    for i, riga in enumerate(righe):
        d.text((90, 110 + 38 * i), riga, font=carattere, fill=(25, 25, 30))
    timbro = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    dt, rosso = ImageDraw.Draw(timbro), (170, 30, 40, 190)
    dt.ellipse([10, 10, 290, 290], outline=rosso, width=8)
    dt.ellipse([40, 40, 260, 260], outline=rosso, width=3)
    dt.text((150, 150), "PROTOCOLLO", font=ImageFont.load_default(size=34), fill=rosso, anchor="mm")
    timbro = timbro.rotate(caso.uniform(-25, 25))
    pagina.paste(timbro, (caso.randint(700, 880), caso.randint(120, 260)), timbro)
    pagina = pagina.rotate(caso.uniform(-1.2, 1.2), fillcolor=(246, 245, 240), resample=Image.BICUBIC)
    pagina = pagina.filter(ImageFilter.GaussianBlur(caso.uniform(0.9, 1.2)))
    rumore = np.random.default_rng(seme).normal(0, 9, (altezza, larghezza, 1))
    return Image.fromarray((np.asarray(pagina) + rumore).clip(0, 255).astype(np.uint8))


def main() -> None:
    from doctr.models import detection_predictor

    rilevatore = detection_predictor("fast_base", pretrained=True)
    coco = annotazioni_coco()
    categorie = {c["id"]: c["name"] for c in coco["categories"]}
    immagini = {im["id"]: im for im in coco["images"]}
    per_immagine: dict[int, list[dict]] = {}
    for a in coco["annotations"]:
        per_immagine.setdefault(a["image_id"], []).append(a)

    def riquadri(id_: int, nomi: set[str]) -> list[tuple[float, float, float, float]]:
        return [(x, y, x + w, y + h) for a in per_immagine[id_] if categorie[a["category_id"]] in nomi
                for x, y, w, h in [a["bbox"]]]

    for cartella in ("fotogrammi", "targhe", "scansioni"):
        (DATI / cartella).mkdir(parents=True, exist_ok=True)
    crediti, veri, foto, targhe = [], [], [], []
    for numero, (id_, gruppo) in enumerate([(i, "giorno") for i in GIORNO] + [(i, "notte") for i in NOTTE], 1):
        meta = immagini[id_]
        im = Image.open(io.BytesIO(scarica(meta["coco_url"]))).convert("RGB")
        veicoli = riquadri(id_, VEICOLI)
        sfoca(im, riquadri(id_, {"person"}) + scritte_sui_veicoli(rilevatore, im, veicoli) + DA_SFOCARE.get(id_, []))
        nome = f"F{numero:02d}.jpg"
        im.save(DATI / "fotogrammi" / nome, quality=88)
        foto.append({"file": nome, "gruppo": gruppo})
        veri += [{"file": nome, "x0": round(x0, 1), "y0": round(y0, 1), "x1": round(x1, 1), "y1": round(y1, 1)}
                 for x0, y0, x1, y1 in veicoli]
        crediti.append(credito(id_, meta, f"fotogrammi/{nome}", "persone e targhe sfocate"))
    for numero, (id_, (testo, (x0, y0, x1, y1))) in enumerate(TARGHE.items(), 1):
        meta = immagini[id_]
        im = Image.open(io.BytesIO(scarica(meta["coco_url"]))).convert("RGB")
        scritte = scritte_sui_veicoli(rilevatore, im, riquadri(id_, VEICOLI))
        sfoca(im, riquadri(id_, {"person"}) + scritte + DA_SFOCARE.get(id_, []))
        # Ingrandita tre volte: la targa di fantasia, nitida, copre quella vera, sfocata.
        im = im.resize((im.width * INGRANDIMENTO, im.height * INGRANDIMENTO), Image.LANCZOS)
        finta = targa(testo, (x1 - x0) * INGRANDIMENTO, (y1 - y0) * INGRANDIMENTO)
        posto = (x0 * INGRANDIMENTO, y0 * INGRANDIMENTO)
        im.paste(finta, posto)
        nome = f"T{numero}.jpg"
        im.save(DATI / "targhe" / nome, quality=85)
        targhe.append({"file": nome, "targa": testo, "x0": posto[0], "y0": posto[1],
                       "x1": posto[0] + finta.width, "y1": posto[1] + finta.height})
        crediti.append(credito(id_, meta, f"targhe/{nome}",
                               "persone e targhe sfocate, ingrandita, targa di fantasia aggiunta"))
    for seme, documento in enumerate(SCANSIONI, 1):
        righe = righe_del_documento(documento)
        scansione(righe, seme).save(DATI / "scansioni" / f"{documento}.jpg", quality=72)
        (DATI / "scansioni" / f"{documento}.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")

    for nome, righe in (("fotogrammi.csv", foto), ("veicoli.csv", veri), ("targhe.csv", targhe),
                        ("crediti.csv", crediti)):
        with (DATI / nome).open("w", encoding="utf-8", newline="") as file:
            scrittore = csv.DictWriter(file, fieldnames=list(righe[0]))
            scrittore.writeheader()
            scrittore.writerows(righe)
    print(f"{len(foto)} fotogrammi, {len(veri)} veicoli, {len(targhe)} targhe, {len(SCANSIONI)} scansioni in {DATI}")


if __name__ == "__main__":
    main()
