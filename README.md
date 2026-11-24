# Laboratori del corso di intelligenza artificiale

Il materiale dei laboratori al computer: il codice di partenza, i documenti su cui lavorare e le istruzioni.

Tutti i dati sono sintetici e scritti per il corso: persone, luoghi, conti, numeri di telefono e indirizzi non
esistono. I domini finiscono in `.invalid` e gli indirizzi IP sono quelli riservati alla documentazione.

## Che cosa c'è

| Cartella | Giorno | Che cos'è |
|---|---|---|
| `labs/day1/document-lab/` | 1, pomeriggio | Il laboratorio documentale: i quattro compiti, la scheda del gruppo, i documenti numerati |
| `labs/day1/agent-lab/` | 1, pomeriggio | L'agente a mano: voi fate gli strumenti, il modello chiede; si apre `index.html` |
| `labs/day1/agent-demo/visore/` | 1, pomeriggio | La demo dell'agente, da sfogliare nel browser: si apre `index.html` |
| `labs/day3/visione/` | 3, mattina | Un notebook: cinque modelli di visione misurati su un piccolo test set |
| `labs/day3/rag/` | 3, pomeriggio | Un notebook: tre modi di cercare nel fascicolo, e le risposte con la fonte |
| `labs/day3/fine-tuning/` | 3, pomeriggio | Un esempio da leggere: un modello piccolo adattato a compilare una scheda |
| `labs/day4/agent-lab/` | 4, mattina | Un agente che lavora su un fascicolo, con controlli e traccia |
| `labs/day4/local-models-lab/` | 4, pomeriggio | Modelli piccoli sul proprio portatile, messi a confronto |
| `data/case-file/` | 1, 3, 4 e 5 | Il fascicolo: dieci documenti, un undicesimo in HTML, la foto di un IBAN |

Ogni laboratorio ha il suo `README.md`, con i comandi da eseguire. Si parte da lì.

## Per cominciare

Servono `git` e [`uv`](https://docs.astral.sh/uv/). Poi:

```sh
git clone <indirizzo di questo repository>
cd <cartella clonata>/labs/day4/agent-lab
uv sync
```

## Prima del giorno 3

I due notebook del giorno 3 scaricano circa 4,6 GB: vanno preparati prima, da una rete veloce. Servono 5 GB liberi e
una mezz'ora. Dopo aver installato `uv` (su Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`;
su macOS e Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`), chiudere e riaprire il terminale, poi:

```sh
cd <cartella clonata>/labs/day3/visione
uv sync
uv run python -c "import visione; visione.scarica_modelli()"
cd ../rag
uv sync
uv run python -c "from rag import Archivio; Archivio()"
```

Su un Mac con processore Intel il notebook di `labs/day3/visione` non funziona: si prepara solo quello di `rag`.

## Ricevere le novità

Nei giorni successivi i docenti aggiungono materiale. Per riceverlo, dalla cartella clonata:

```sh
git pull
```

## Le chiavi

Le chiavi dei modelli le danno i docenti in aula. Vanno solo nel file `.env` del laboratorio, che git ignora: non
si scrivono in nessun altro file e non si pubblicano.

## Uso

Materiale didattico riservato ai partecipanti del corso. Tutti i diritti riservati.
