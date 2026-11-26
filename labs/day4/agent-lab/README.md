# Laboratorio: un agente in locale (giorno 4)

Due notebook, su un modello che gira sul portatile: niente chiavi, niente rete, tutti i dati sintetici.

| Notebook | Che cosa si fa | Durata |
|---|---|---|
| `notebook.ipynb` | Si **costruisce** l'agente in nove passi: il modello da solo, uno strumento, il ciclo, la traccia, il punto di controllo umano, il gate, il documento avvelenato. | lo esegue il docente; chi vuole lo segue |
| `valutazione.ipynb` | Si **misura** l'agente: undici compiti con la risposta nota, una prova per ogni impostazione, e il confronto. | 30-50 minuti, da soli o a gruppi |

Nessuna email viene inviata: nel primo notebook `invia_email` scrive un file in `lavoro/`, nel secondo registra solo
la richiesta.

## Preparare il portatile

Servono 16 GB di memoria (8 bastano per il modello piccolo), 8 GB liberi su disco e la rete per il primo avvio. I
comandi si scrivono in un terminale: su Windows «PowerShell», su macOS «Terminale».

### 1. Ollama, il programma che esegue i modelli

1. Scaricarlo da <https://ollama.com/download> e installarlo.
2. Avviarlo: su Windows e macOS è un'applicazione, e quando è accesa compare la sua icona vicino all'orologio.
3. Controllo, nel terminale: `ollama list`. Deve rispondere con un elenco, anche vuoto. Se risponde «could not
   connect», Ollama non è acceso.

### 2. I due modelli del laboratorio

```sh
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen3.5:2b-q4_K_M
```

Il primo pesa 3,3 GB, il secondo 1,9 GB: su una rete lenta servono diversi minuti. Si può proseguire con i passi
successivi mentre scaricano.

### 3. uv, il programma che installa Python e le librerie

- macOS e Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Poi **chiudere e riaprire il terminale**. Controllo: `uv --version`.

### 4. La cartella del corso

Chi l'ha già: entrarci e scrivere `git pull`. Chi non l'ha: clonarla con il comando della pagina del repository,
oppure scaricare lo ZIP da «Code», «Download ZIP» e scompattarlo.

### 5. Le librerie del laboratorio

Dalla cartella del corso:

```sh
cd labs/day4/agent-lab
uv sync
```

`uv sync` crea in questa cartella una cartella `.venv` con Python e le librerie. La prima volta scarica circa
400 MB.

## Aprire un notebook

Due modi. Il primo non richiede altro.

### Nel browser, con JupyterLab

Dalla cartella `labs/day4/agent-lab`:

```sh
uv run jupyter lab valutazione.ipynb
```

Si apre una scheda del browser con il notebook. Il terminale resta occupato finché JupyterLab è acceso: per
chiuderlo, Ctrl+C nel terminale.

### In Visual Studio Code

1. Installare le estensioni «Python» e «Jupyter» (icona dei quadratini a sinistra, cercare per nome).
2. «File», «Apri cartella», e scegliere **`labs/day4/agent-lab`**, non la cartella del corso: così il notebook
   trova i suoi file.
3. Aprire `valutazione.ipynb`.
4. In alto a destra, «Seleziona kernel», «Ambienti Python», e scegliere quello che contiene **`.venv`**.

In tutti e due i casi: una cella si esegue con Maiusc+Invio, e si procede dall'alto verso il basso. Se si riavvia
il kernel, si riparte dalla prima cella.

## Il notebook di valutazione in breve

Tutto ciò che si può cambiare sta in `Impostazioni`. Per cambiare una voce si scrive
`impostazioni.con(voce=valore)`: l'originale non cambia, e una voce scritta male viene rifiutata con l'elenco di
quelle valide.

| Voce | Valore di partenza | Che cosa cambia |
|---|---|---|
| `modello` | `"qwen3.5:4b-q4_K_M"` | quale modello risponde |
| `finestra_di_contesto` | `16000` | quanti token vede in una volta |
| `temperatura` | `0.0` | quanto variano le risposte |
| `ragionamento` | `False` | se il modello «pensa» prima di rispondere |
| `passi_massimi` | `8` | dopo quante richieste ci si ferma |
| `ricerca` | `"ibrida"` | `"parole"`, `"vettori"` oppure `"ibrida"` |
| `chunk_per_ricerca` | `5` | quante righe restituisce una ricerca |
| `strumenti` | i tre di base | le funzioni che l'agente può chiamare |
| `istruzioni` | il prompt di base | il prompt di sistema |
| `ripetizioni` | `1` | quante volte si esegue ogni compito |

Uno strumento è una funzione: il primo parametro è il fascicolo, gli altri sono ciò che il modello deve scrivere,
la frase tra triple virgolette è la descrizione che il modello legge. Il passo 5 del notebook ne aggiunge uno.

Le prove si salvano in `risultati/`, una per nome. Quelle che cominciano con `confronto-` sono già lì: fatte su un
portatile con 24 GB di memoria, servono da confronto e da riserva. Per ricominciare da capo, in una cella:
`from laboratorio import cancella_le_mie_prove; cancella_le_mie_prove()`.

## Se qualcosa non va

| Che cosa si vede | Che cosa vuol dire | Che cosa fare |
|---|---|---|
| «Ollama non risponde» | Ollama è spento | Avviarlo, poi rieseguire la cella |
| «model ... not found» | Il modello non è sul disco | `ollama pull <nome>` nel terminale |
| «non accetta strumenti» | Il modello non sa chiamare funzioni | È un risultato: la prova viene salvata con zero compiti. Scegliere un altro modello per continuare |
| `ModuleNotFoundError: laboratorio` | Il notebook è aperto dalla cartella sbagliata | Aprire la cartella `labs/day4/agent-lab`, come sopra |
| `ModuleNotFoundError` per un'altra libreria | Il kernel non è quello di `.venv` | «Seleziona kernel» in VS Code; oppure avviare con `uv run jupyter lab` |
| La prima ricerca resta ferma un minuto | Sta scaricando il modello di embedding, 1 GB, una volta sola | Aspettare; serve la rete |
| Una prova dura più di dieci minuti | Il portatile è lento per quel modello | Interrompere (quadrato in alto), poi usare `modello="qwen3.5:2b-q4_K_M"` o meno compiti: `prova(impostazioni, "breve", compiti=["R1", "R2", "A1", "Z2"])` |
| Il portatile rallenta molto | La memoria è piena | Chiudere altri programmi; usare il modello piccolo; `finestra_di_contesto=8000` |
| `uv` non viene trovato | Il terminale è quello di prima dell'installazione | Chiuderlo e riaprirlo |

## Cosa c'è nella cartella

| File | Contenuto |
|---|---|
| `notebook.ipynb` | Costruire l'agente. Sopra ogni cella: che cosa fare e che cosa mostra. |
| `valutazione.ipynb` | Misurare l'agente. Stessa forma. |
| `laboratorio.py` | Ciò che sta dietro il notebook di valutazione: le impostazioni, i tre strumenti, il ciclo dell'agente, il giudizio, la prova. Si può leggere: non usa framework. |
| `compiti.json` | Il golden dataset: i dodici compiti con la risposta nota (undici più la cronologia). |
| `risultati/` | Le prove salvate. |
| `strumenti.py`, `fascicolo.py`, `traccia.py` | Leggere un documento, scrivere un'email nella posta in uscita, caricare il fascicolo, scrivere la traccia. |
| `modello_finto.py` | Il modello finto del primo notebook: obbedisce sempre alla riga nascosta di DOC-09. |
| `soluzione/`, `esegui.py`, `confronta.py` | Un agente completo da terminale, scritto con un framework, e il confronto con la cronologia di riferimento: sono il punto di partenza dell'hackathon del giorno 5. |

La ricerca nel fascicolo è quella del notebook RAG (`../../day3/rag/rag.py`), con lo stesso modello di embedding.

Controlli, senza modello e senza rete: `uv run pytest`.
