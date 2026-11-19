# Installare e configurare i modelli locali

Serve una volta sola per ogni portatile, prima della lezione. I modelli pesano alcuni gigabyte: non si scaricano
in aula.

## Che cosa serve

| | Minimo | Consigliato |
|---|---|---|
| Memoria RAM | 8 GB | 16 GB |
| Spazio su disco | 12 GB liberi | 20 GB liberi |
| Python | 3.10 o successivo (3.12 per la parte 4: la installa uv) | |
| Ollama | versione recente (provato con la 0.40.15) | |
| uv | solo per la parte 4, l'agente del mattino | |

Con 8 GB si usano i quattro modelli di base, uno alla volta. Con 16 GB si possono aggiungere i tre facoltativi.

## 1. Installare Ollama

Scaricare il programma da <https://ollama.com/download> e installarlo. Poi, in un terminale:

```sh
ollama --version
```

Deve rispondere con un numero di versione. Se risponde «command not found», chiudere e riaprire il terminale.

## 2. Scaricare i modelli

Questo è l'elenco dei modelli del laboratorio: le altre schede rimandano qui.

I quattro modelli di base, 11 GB in tutto:

```sh
ollama pull qwen3.5:4b-q4_K_M
ollama pull qwen3.5:2b-q4_K_M
ollama pull phi4-mini
ollama pull gemma3:4b
```

| Modello | Su disco | Licenza | Perché c'è |
|---|---|---|---|
| `qwen3.5:4b-q4_K_M` | 3,3 GB | Apache 2.0 | Il riferimento: 4 miliardi di parametri, 4 bit |
| `qwen3.5:2b-q4_K_M` | 1,9 GB | Apache 2.0 | Lo stesso modello, metà taglia |
| `phi4-mini` | 2,5 GB | MIT | Un altro produttore |
| `gemma3:4b` | 3,4 GB | Gemma Terms of Use | Una licenza con condizioni; nessun supporto agli strumenti |

I tre facoltativi, per chi ha 16 GB di memoria (altri 10 GB su disco):

```sh
ollama pull qwen3.5:4b-q8_0
ollama pull bonsai-2:4b
ollama pull nemotron-3-nano:4b
```

| Modello | Su disco | Licenza | Perché c'è |
|---|---|---|---|
| `qwen3.5:4b-q8_0` | 5,2 GB | Apache 2.0 | Il riferimento a 8 bit, per il confronto sulla quantizzazione |
| `bonsai-2:4b` | 1,6 GB | Apache 2.0 | Pesi a tre valori: molto piccolo per la sua taglia |
| `nemotron-3-nano:4b` | 2,9 GB | NVIDIA Open Model License | Un'altra licenza con condizioni |

La licenza di un modello installato si legge con `ollama show <modello> --license`.

## 3. Controllare

```sh
ollama list
python3 banco.py qwen3.5:2b-q4_K_M --solo E1 --non-salvare
```

Su Windows, al posto di `python3` scrivere `py`.

Il primo comando elenca i modelli scaricati. Il secondo fa una domanda al modello più piccolo: deve comparire una
riga verde o rossa entro mezzo minuto. Se compare «Ollama non risponde», avviare il programma Ollama e riprovare.

## 4. Preparare la parte 4

La parte 4 usa il progetto del mattino, che ha bisogno di uv e di scaricare le sue dipendenze una volta, con la rete:

```sh
cd ../agent-lab
uv sync
cd ../local-models-lab
python3 agente_locale.py qwen3.5:2b-q4_K_M
```

L'ultimo comando dura qualche minuto e deve stampare una riga con «documenti letti».

## Senza rete: copiare i modelli da un altro computer

`ollama pull` ha bisogno di Internet. In alternativa si copia la cartella dei modelli da un computer che li ha già:

| Sistema | Cartella |
|---|---|
| macOS | `~/.ollama/models` |
| Linux (installazione standard) | `/usr/share/ollama/.ollama/models`, poi `sudo chown -R ollama:ollama` sulla cartella |
| Windows | `C:\Users\<utente>\.ollama\models` |

Copiare la cartella intera nello stesso percorso del computer di destinazione, a Ollama chiuso. Poi `ollama list`.

## Se i portatili non reggono: un solo computer per tutta l'aula

Un computer con i modelli installati può servire tutti gli altri sulla rete dell'aula.

Sul computer che serve i modelli:

```sh
OLLAMA_HOST=0.0.0.0 ollama serve
```

Sugli altri, al posto dell'indirizzo mettere quello del computer che serve i modelli:

```sh
# macOS e Linux
OLLAMA_HOST=http://192.0.2.10:11434 python3 banco.py qwen3.5:4b-q4_K_M
```

```powershell
# Windows, PowerShell
$env:OLLAMA_HOST = "http://192.0.2.10:11434"; python banco.py qwen3.5:4b-q4_K_M
```

Più gruppi sullo stesso computer si mettono in coda: i tempi misurati non sono più confrontabili tra gruppi, le
risposte corrette sì.
