# Laboratorio: un agente in locale (giorno 4)

Ogni gruppo costruisce, in un notebook e su un modello locale, un agente che lavora sul fascicolo sintetico: cerca,
legge i documenti, prepara un'email per il PM. Poi gli aggiunge una traccia, un punto di controllo umano e un gate,
e lo prova su un documento con un'istruzione nascosta.

Tutti i dati sono sintetici. `invia_email` non invia nulla: scrive un file in `lavoro/notebook/<nome>/posta-in-uscita`.

## Avvio

`notebook.ipynb` è il laboratorio, in nove passi, senza chiavi e senza rete: si parte dal modello da solo e
a ogni passo si aggiunge un pezzo (uno strumento, il ciclo, la traccia, il punto di controllo umano, il gate, il
documento avvelenato). Il ciclo e i controlli sono scritti nelle celle, senza framework.

Serve Ollama avviato, con il modello di riferimento: `ollama pull qwen3.5:4b-q4_K_M`. Poi, da questa cartella:

```sh
uv sync
uv run jupyter lab notebook.ipynb
```

Chi usa Visual Studio Code apre `notebook.ipynb` e sceglie come kernel l'ambiente `.venv` della cartella.

- Il modello si cambia nella prima cella, oppure con `LAB_OLLAMA_MODEL=<nome> uv run jupyter lab notebook.ipynb`. Deve
  accettare gli strumenti: `gemma3:4b` non li accetta e `phi4-mini` non li chiama.
- Lo strumento di ricerca è la ricerca del laboratorio RAG (`../../day3/rag/rag.py`), costruita sui documenti del
  fascicolo: `crea_ricerca(modo="ibrida", k=5)` nel passo 2 fissa il modo (`"parole"`, `"vettori"`, `"ibrida"`) e
  quanti passi restituire. Usa lo stesso modello di embedding da 1 GB, in `../../day3/rag/.modelli/`: se non c'è
  già, la prima esecuzione lo scarica.
- La finestra di contesto è fissata a 16.000 token a ogni richiesta: non serve creare una variante del modello.
- Il passo 8 usa prima un modello finto (`modello_finto.py`) che obbedisce sempre alla riga nascosta di DOC-09:
  non usa la rete e mostra che i controlli fermano l'invio qualunque cosa faccia il modello.
- Le esecuzioni lasciano fascicolo, posta in uscita e traccia in `lavoro/notebook/<nome>/`.

Ollama si installa da <https://ollama.com/download>. Chi vuole provare un altro modello nel passo 9 scarica anche
`qwen3.5:2b-q4_K_M`.

## Cosa c'è nella cartella

| File | Contenuto |
|---|---|
| `notebook.ipynb` | Il laboratorio. Sopra ogni cella: che cosa fare e che cosa mostra. |
| `strumenti.py`, `fascicolo.py`, `traccia.py` | Leggere un documento, scrivere un'email nella posta in uscita, caricare il fascicolo, scrivere la traccia. |
| `modello_finto.py` | Il modello finto del passo 8: obbedisce sempre alla riga nascosta di DOC-09. |
| `soluzione/`, `esegui.py`, `confronta.py` | Un agente completo da terminale, scritto con un framework, e il confronto con la cronologia di riferimento. Non servono al notebook: sono il punto di partenza dell'hackathon del giorno 5. |

Controlli, senza modello e senza rete: `uv run pytest`.
