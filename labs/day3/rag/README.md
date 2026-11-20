# Notebook RAG: vettoriale o ibrida?

Giorno 3, pomeriggio, slide 128-129 (il banco di prova è presentato nella 127). 50 minuti, ognuno al proprio portatile.

Si cerca nel fascicolo in tre modi (parole chiave, vettoriale, ibrida), si misura quale trova il passo giusto su
quindici domande, poi un modello risponde citando le fonti. Tutti i dati sono sintetici.

## Avvio

Serve [`uv`](https://docs.astral.sh/uv/). Da questa cartella:

```sh
uv sync
cp env.esempio .env        # su Windows: copy env.esempio .env; poi aprire .env e scrivere la chiave data dai docenti
uv run jupyter lab notebook.ipynb
```

In alternativa a JupyterLab, chi usa già Visual Studio Code può aprire lì il notebook: servono le estensioni Python
e Jupyter, poi `uv sync`, aprire questa cartella, aprire `notebook.ipynb` e scegliere come kernel l'ambiente `.venv`
della cartella (Seleziona kernel, Ambienti Python). Ciò che serve al kernel, `ipykernel`, è già tra le librerie.

`uv sync` scarica le librerie (serve la rete, una volta). La cella `indice = Indice()` scarica il modello di
embedding, 1 GB, nella cartella `.modelli/` qui accanto, se non c'è già. Per scaricarlo prima, dal terminale:
`uv run python -c "from rag import Indice; Indice()"`. Tutto gira sul processore, senza scheda grafica.

La chiave serve solo per la parte 3. Se manca, o se la rete non va, il notebook usa le risposte già calcolate in
`risposte_precalcolate.json`, e dice perché e con quale modello sono state calcolate. Le parti 1, 2 e 4 funzionano
senza rete, dopo il primo avvio.

Con un modello locale (`LAB_MODEL=ollama:...`) il prompt con tutto il fascicolo è di circa 16.000 caratteri: la
finestra di contesto di Ollama va portata ad almeno 16.000 token, altrimenti l'inizio del prompt, con le istruzioni,
viene tagliato senza avviso.

## Che cosa c'è

| File | Che cos'è |
|---|---|
| `notebook.ipynb` | Il notebook, in quattro parti: indice, tre ricerche, risposta con le fonti, tabella |
| `rag.py` | I passi del corpus e le tre ricerche |
| `risposte.py` | Il prompt con le fonti e la chiamata al modello |
| `banco.csv` | Le quindici domande, ciascuna con il passo in cui sta la risposta |
| `distrattori/` | Cinque documenti di un'altra frode, con altri nomi, date, importi e IBAN |
| `prova_banco.py` | La tabella delle tre ricerche, dal terminale: `uv run prova_banco.py --k 5` |
| `precalcola.py` | Ricalcola le risposte di riserva con il modello scritto in `.env` |

## Il corpus

I dieci documenti di base del fascicolo (`data/case-file/core/`) e i cinque distrattori: 146 passi. Un passo è una
riga; nei verbali è una domanda con la sua risposta, e porta il numero di riga della risposta. `DOC-05:8` è la riga
8 del file di DOC-05.

I distrattori raccontano una frode simile ai danni di un'altra persona, in un altro mese: stessa forma dei
documenti, altri nomi, altri importi, altri IBAN. Servono a vedere se una ricerca li confonde con i nostri. Non
fanno parte del fascicolo dell'hackathon, e la banca e la località non compaiono in nessun altro documento del corso.

È una trappola voluta. Le domande non nominano la vittima e un passo è una riga sola, che non dice di quale caso
parla: per le domande 9 e 12-15 anche l'altra frode ha una riga che «risponde». Per la 15, il primo bonifico
dell'altra persona è del 17/02/2025, e nei passi dati al modello entra l'estratto conto DOC-52. Il banco conta giusto
solo il passo del nostro caso. Nella parte 3 una risposta può citare una fonte che esiste e parlare del caso
sbagliato: è il punto da far notare, e si vede aprendo il documento citato.

## Le domande

| Tipo | Domande | Che cosa mette alla prova |
|---|---|---|
| identificativo | 1-6 | Un IBAN, un orario, un indirizzo IP scritti esattamente |
| parafrasi | 7-12 | La domanda usa parole diverse dal documento; la 10 chiede in italiano di una chat in inglese |
| contraddizione | 13-14 | Due documenti dicono cose diverse: devono tornare tutti e due |
| senza risposta | 15 | Il fascicolo non lo dice. Resta fuori dalla tabella: si guarda che cosa risponde il modello |

Nella colonna `passi_attesi`, `A|B` chiede uno dei due passi; `A & B|C` chiede A e anche uno tra B e C.

## Che cosa deve uscire

Misurato il 20/11/2026 su un Mac con processore Apple, con BM25 e con il modello
`sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (licenza Apache 2.0) nella copia ONNX che scarica
`fastembed`. Su altri processori i numeri non sono stati rimisurati.
Il numero è quante domande hanno il passo atteso tra i primi risultati. Con i primi 3 e con i primi 5 la tabella è
la stessa: quando il passo giusto c'è, sta già tra i primi tre.

| Tipo | Domande | Parole chiave | Vettoriale | Ibrida |
|---|---|---|---|---|
| identificativo | 6 | 6 | 2 | 6 |
| parafrasi | 6 | 1 | 4 | 2 |
| contraddizione | 2 | 1 | 1 | 2 |
| totale | 14 | 8 | 7 | 10 |

Che cosa si legge, per la slide 129:

- La ricerca per parole chiave trova tutti gli identificativi e una sola parafrasi; la vettoriale trova quattro
  parafrasi su sei e due identificativi su sei. Nessuna delle due basta da sola.
- L'ibrida è la migliore nel totale (10 su 14, contro 8 e 7) e tiene tutti gli identificativi.
- Solo l'ibrida riporta le due versioni di tutte e due le contraddizioni: la ricerca per parole ne completa una
  (la 13), la vettoriale l'altra (la 14). È il senso in cui «solo l'ibrida» è vero: per tipo di domanda. Non c'è
  invece una singola domanda che trovi solo l'ibrida.
- Sulle parafrasi l'ibrida perde contro la vettoriale (2 contro 4): le parole in comune con passi sbagliati li
  spingono in alto. È il suo limite, da dire.
- Le domande 8 e 12 non le trova nessuna delle tre. La 12 si usa nella parte 3: il modello riceve cinque passi
  sbagliati, si guarda che cosa risponde.

## Per chi conduce

La scheda con i tempi, ciò che deve comparire a ogni cella e le risposte attese è `TUTOR.md`, che resta ai docenti:
non è nella copia dei partecipanti.

- Il modello di embedding pesa 1 GB (senza PyTorch): conviene farlo scaricare la mattina, con l'ultima riga della
  slide 4a. Il confronto è stato rifatto con altri quattro modelli multilingue, da 250 MB a 2,2 GB: con tutti la
  ricerca per parole trova gli identificativi e quasi nessuna parafrasi, la vettoriale il contrario, e nessuna
  domanda è trovata solo dall'ibrida. Con il modello da 250 MB l'ibrida non è la migliore nel totale (9 contro 10
  della vettoriale): per questo si usa quello da 1 GB.
- L'ibrida è una somma dei reciproci dei posti (reciprocal rank fusion), senza pesi. Un passo senza nessuna parola
  della domanda non prende punti dalla ricerca per parole, e la ricerca per parole da sola non lo restituisce.
- `.env` si rilegge a ogni esecuzione della cella che lo carica, e vince sulle variabili già impostate. Una chiamata
  al modello che dura più di tre minuti si interrompe e il notebook passa alla risposta già calcolata.
- `onnxruntime` è fermo sotto la 1.24: le versioni successive non si installano sui Mac Intel né su macOS prima
  del 14.
- Le risposte di riserva dicono, nel file, con quale modello e quando sono state calcolate. Vanno ricalcolate con
  il modello dell'aula: `uv run precalcola.py`, con `.env` compilato.
- Controlli senza modello: `uv run pytest`.
