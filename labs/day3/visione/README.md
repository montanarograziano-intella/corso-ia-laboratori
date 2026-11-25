# Notebook di computer vision: un test set

Giorno 3, mattina, slide 43a. Ognuno al proprio portatile.

Cinque modelli di visione su un piccolo test set, ognuno con la sua misura: rilevamento di veicoli a tre soglie, la
recall di giorno e di notte, l'OCR su tre scansioni e un IBAN scritto a mano, la ricerca di fotogrammi con una frase,
un VLM che legge una targa.

## Avvio

Serve [`uv`](https://docs.astral.sh/uv/). Da questa cartella:

```sh
uv sync
uv run python -c "import visione; visione.scarica_modelli()"
uv run jupyter lab notebook.ipynb
```

`uv sync` scarica le librerie (1,1 GB, con PyTorch per il processore). La seconda riga scarica i quattro modelli,
2,1 GB in tutto, nella cartella `.modelli/` qui accanto: va fatta prima della lezione, con la rete. Dopo, il notebook
gira senza rete e senza scheda grafica. Con Visual Studio Code: estensioni Python e Jupyter, poi il kernel `.venv`
di questa cartella.

Il laboratorio va aperto dentro il repository intero: FOTO-01 sta in `data/case-file/media/`.

Non gira sui Mac con processore Intel: PyTorch non pubblica più versioni per quei Mac. Chi ne ha uno lavora in coppia.

## Che cosa c'è

| File | Che cos'è |
|---|---|
| `notebook.ipynb` | Il notebook, in cinque parti: rilevamento, gruppi, OCR, ricerca per immagini, VLM; ogni domanda ha la sua risposta |
| `visione.py` | I dati, i quattro modelli e le misure |
| `dati/fotogrammi/` | 29 foto di strade e parcheggi: 24 di giorno, 5 di notte o al crepuscolo |
| `dati/veicoli.csv` | I riquadri veri di auto, camion e autobus, uno per riga |
| `dati/scansioni/` | DOC-01, DOC-05 e DOC-10 del fascicolo stampati come scansioni, con il testo vero accanto |
| `dati/targhe/` | Tre foto con una targa di fantasia al posto di quella vera; `dati/targhe.csv` dice dov'è |
| `dati/crediti.csv` | Fonte, licenza e modifiche di ogni foto |
| `prepara_dati.py` | Per i docenti: ricostruisce `dati/` da COCO e dal fascicolo |
| `test_visione.py` | Controlli senza modelli: `uv run pytest` |

## Il test set

- **Fotogrammi.** Dal set di validazione di [COCO 2017](https://cocodataset.org), scelti a mano tra le foto con
  licenza CC BY 2.0 o CC BY-SA 2.0. Persone e targhe vere sono sfocate. I riquadri sono le annotazioni COCO
  (licenza CC BY 4.0) delle classi auto, camion e autobus. Le foto derivate da una CC BY-SA restano CC BY-SA.
- **Scansioni.** Il testo del fascicolo (sintetico) stampato su una pagina A4, storta di un grado, sfocata, con
  rumore e un timbro. DOC-05 è stampato come tabella.
- **FOTO-01.** Il primo IBAN di DOC-05 scritto a mano e fotografato, dal fascicolo.
- **Targhe.** Tre foto di COCO ingrandite tre volte, con sopra la targa vera una targa di fantasia nel formato
  italiano. Sono targhe non valide: usano le lettere I, O, Q e U, che le targhe italiane non usano.

## I modelli

| Parte | Modello | Licenza | Peso |
|---|---|---|---|
| 1-2 | `PekingU/rtdetr_v2_r18vd` (RT-DETR v2), addestrato su COCO 2017 train: i fotogrammi non li ha visti | Apache 2.0 | 80 MB |
| 3 | docTR: `fast_base` trova le zone di testo, `crnn_vgg16_bn` le legge | Apache 2.0 | 125 MB |
| 4 | `google/siglip2-base-patch16-224` (SigLIP 2), testo e immagini nello stesso spazio, multilingue | Apache 2.0 | 1,4 GB |
| 5 | `HuggingFaceTB/SmolVLM-256M-Instruct`, il VLM | Apache 2.0 | 0,5 GB |

L'OCR dà una confidenza per carattere: il lettore di docTR scrive il testo passo per passo, con una probabilità per
ogni carattere a ogni passo (CTC). La confidenza di un carattere è la più alta tra i passi che lo scrivono. docTR la
riassume in un numero per parola; `visione.py` tiene anche quella dei singoli caratteri.

## Che cosa deve uscire

Misurato il 20/11/2026 su un Mac con processore Apple: il notebook intero gira in circa 20 secondi, più il
caricamento dei modelli. Su un portatile senza scheda grafica conviene contare cinque o dieci volte tanto.

| Parte | Misura | Valore |
|---|---|---|
| 1 | Precisione a soglia 0,3 / 0,5 / 0,7 | 0,45 / 0,82 / 0,94 |
| 1 | Recall a soglia 0,3 / 0,5 / 0,7 | 0,84 / 0,76 / 0,63 |
| 2 | Recall di giorno, soglia 0,5 | 0,80 su 142 veicoli |
| 2 | Recall di notte, soglia 0,5 | 0,52 su 25 veicoli |
| 3 | CER DOC-01 / DOC-05 / DOC-10 | 1,9% / 3,3% / 1,6% |
| 3 | IBAN esatti | 2 su 3 |
| 4 | recall@5 | 5 su 5, 4 al primo posto |
| 5 | Targhe esatte, foto intera / ritaglio | 0 su 3 / 3 su 3 |

## Per chi conduce

La scheda con i tempi, ciò che deve comparire e le risposte attese è `TUTOR.md`, che resta ai docenti.

- I dati sono già nel repository: `prepara_dati.py` serve solo a ricostruirli (scarica 240 MB di annotazioni COCO
  in `.scaricati/` e 32 foto). Le immagini escono identiche a ogni esecuzione.
- Persone e targhe sono sfocate da `prepara_dati.py`: le targhe con il modello che trova il testo, più
  riquadri di targhe e volti controllati a occhio. Prima di aggiungere una foto, va guardata a piena risoluzione.
- `dati/crediti.csv` dà per ogni foto l'autore, la pagina Flickr e la licenza. Quattro foto (F15, F26, T2, T3) non
  sono più su Flickr: per loro l'autore non è noto e la pagina è quella di COCO.
- Controlli senza modelli: `uv run pytest`.
