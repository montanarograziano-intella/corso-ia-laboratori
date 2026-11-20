# Un fine-tuning sul fascicolo: il prima e il dopo della slide 93

Giorno 3, pomeriggio, slide 92-97. Un modello piccolo impara a compilare la scheda sintetica dell'ufficio a partire
da una denuncia. Il risultato è in `risultati.json`: è un fine-tuning eseguito davvero, non un esempio scritto a
mano.

| File | Che cos'è |
|---|---|
| `genera.py` | Scrive le denunce sintetiche con la loro scheda: 400 per l'addestramento, 40 di controllo, 40 mai viste |
| `prova.py` | Confronta il modello di base e quello adattato su DOC-01 e sulle 40 denunce mai viste |
| `risultati.json` | Le risposte e i conteggi dell'esecuzione del 18/11/2026 |

## La scheda

Nove righe, sempre nello stesso ordine. Le sigle e le forme sono una convenzione inventata per il corso: il modello
di base non può conoscerle.

```text
TIPO: FRODE-TEL
DATA_DENUNCIA: 03/03/2025
DENUNCIANTE: NERI Giulia
DATA_FATTO: 03/03/2025
CANALE: SMS+TEL
IMPORTO_EUR: 4200,00
STRUMENTO: BONIFICO-IST
CODICE_COMUNICATO: N.D.
ALLEGATI: 1
```

## Che cosa è stato fatto

- Modello di base: `mlx-community/Qwen2.5-1.5B-Instruct-4bit` (licenza Apache 2.0), 1,5 miliardi di parametri.
- Dati: 400 denunce sintetiche di cinque tipi di frode, scritte da `genera.py` combinando frasi diverse. DOC-01 non
  è tra queste, ma l'intestazione e alcune frasi delle denunce generate sono modellate su di essa.
- Addestramento: LoRA su 16 strati, 300 passi, 4 esempi per passo. Si addestra lo 0,34% dei pesi (5,3 milioni su
  1.544 milioni). L'adattatore è un file di 21 MB. Su un portatile con processore Apple M5 e 24 GB: circa sei minuti.

```sh
python3 genera.py dati
uvx --from mlx-lm mlx_lm.lora --model mlx-community/Qwen2.5-1.5B-Instruct-4bit --train --data dati \
  --fine-tune-type lora --num-layers 16 --batch-size 4 --iters 300 --learning-rate 1e-4 --seed 7 \
  --adapter-path adattatore
uv run --with mlx-lm python3 prova.py mlx-community/Qwen2.5-1.5B-Instruct-4bit adattatore dati risultati.json
```

`mlx-lm` gira solo su Mac con processore Apple. `dati/` e `adattatore/` non stanno nel repository: si rigenerano
con i tre comandi.

## Che cosa è uscito

| Variante | Campi giusti, 40 denunce mai viste | Schede tutte giuste | DOC-01 |
|---|---|---|---|
| Modello di base, con la sola istruzione | 0 su 360 | 0 su 40 | 0 su 9: ricopia la denuncia in grassetto |
| Modello di base, con il formato e un esempio nel prompt | 138 su 360 | 0 su 40 | 1 su 9 |
| Modello adattato, con la sola istruzione | 360 su 360 | 40 su 40 | 8 su 9 |

Il prompt della seconda riga descrive i nove campi, le sigle e le forme, e porta una scheda di esempio: è in
`prova.py`, alla voce `FORMATO`. I conteggi per campo sono in `risultati.json`, alla voce `giusti_per_campo`.

Che cosa dire in aula.

- **Slide 93, il prima e il dopo.** Con la stessa istruzione di una riga, il modello di base ricopia la denuncia e
  quello adattato scrive la scheda. Le due risposte su DOC-01 sono in `risultati.json`, alle voci `base` e
  `adattato`.
- **Slide 97, il confronto con un buon prompt.** Con il formato descritto il modello di base scrive nove righe
  nella forma giusta, ma sbaglia il contenuto: su 40 denunce indovina l'importo 30 volte, il tipo di frode 8, i
  canali 7. Su DOC-01 copia la scheda di esempio, nome compreso («BIANCHI Mario»): un modello così piccolo confonde
  l'esempio con la risposta. Per questo compito, con questo modello, il prompt non basta.
- **Slide 97, dove sbaglia il modello adattato.** Su DOC-01 sbaglia un campo: scrive `CODICE_COMUNICATO: NO`,
  mentre la denuncia dice «non ricordo se gli ho detto il codice» e la scheda giusta è `N.D.`. Le 40 denunce mai
  viste usano le stesse frasi di quelle dell'addestramento: il 360 su 360 dice che ha imparato quelle frasi. Appena
  la frase cambia un poco, come in DOC-01, un campo cade. È il motivo per cui si prova su documenti scritti da altri
  prima di fidarsi.

## Limiti

- Una sola esecuzione, con un solo seme. I conteggi possono cambiare di qualche unità.
- DOC-01 è una sola denuncia, e somiglia a quelle generate: non è una prova su testi scritti da altri.
- Il confronto usa un modello di base molto piccolo. Il 138 su 360 vale per questo modello: non dice quanto
  rende un buon prompt con un modello più grande.
- Le denunce di addestramento vengono da un generatore a frasi fisse: sono più regolari di quelle vere.
- Il modello è stato scelto perché si addestra in pochi minuti su un portatile, non perché sia il migliore.
