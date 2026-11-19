# Laboratorio: modelli locali a confronto (giorno 4, pomeriggio)

Ogni gruppo fa girare lo stesso banco di prova su più modelli installati sul proprio portatile, e confronta
quattro numeri: risposte corrette, tempo al primo token, token al secondo, memoria. Poi cambia una sola cosa e
misura la differenza. Alla fine prova l'agente del mattino con un modello locale.

Tutti i dati sono sintetici. Nessun testo esce dal portatile.

## Prima di cominciare

- Modelli installati: vedi [INSTALLAZIONE.md](INSTALLAZIONE.md).
- Aprire un terminale in questa cartella: `labs/day4/local-models-lab`.
- Controllo: `ollama list` deve elencare i modelli.
- Su Windows, al posto di `python3` scrivere `py`.

## Che cosa c'è nella cartella

| File | Contenuto |
|---|---|
| `banco.py` | Il banco di prova. Non va modificato: si esegue. |
| `domande.json` | Le quindici domande, con le risposte attese. |
| `visore/index.html` | I risultati di tutte le prove, fianco a fianco. Si apre nel browser. |
| `agente_locale.py` | Prova l'agente del mattino con un modello locale. |
| `risultati/` | Un file per ogni prova. All'inizio contiene le prove fatte dai docenti. |
| `SCHEDA.md` | La scheda di confronto da compilare, una per gruppo. |

## Il banco di prova

Quindici domande sul fascicolo, con risposta nota:

- **E1-E6, estrazione:** un dato da un documento, in JSON. E6 chiede un dato che nel documento non c'è.
- **F1-F3, fascicolo intero:** la domanda arriva insieme a tutti e dieci i documenti. Con le impostazioni
  del banco ci stanno. Il gruppo A vede che cosa succede quando non stanno nella finestra di contesto.
- **S1-S3, riassunto:** in italiano, con i fatti che devono comparire. S3 parte da una chat in inglese.
- **T1-T3, strumenti:** il modello deve chiamare lo strumento giusto con gli argomenti giusti.

Ogni domanda dà una riga verde (corretta) o rossa (sbagliata, con il motivo). Le impostazioni sono fisse, quindi
le prove di gruppi diversi si possono confrontare.

## Parte 1: la stessa prova su tutti i modelli (30 minuti)

```sh
python3 banco.py qwen3.5:4b-q4_K_M qwen3.5:2b-q4_K_M phi4-mini gemma3:4b
```

Ogni modello impiega meno di un minuto. Poi aprire `visore/index.html` nel browser: una colonna per modello, una
riga per domanda. Un clic su una casella mostra la risposta attesa e quella del modello.

Da scrivere sulla [scheda del gruppo](SCHEDA.md), per ogni modello: risposte corrette, tempo al primo token, token
al secondo, memoria.

Da guardare insieme:

1. Quale modello inventa un dato che non c'è (E6)? Che cosa ha scritto?
2. Quale riassunto è scritto bene ma sbagliato? Aprire S3.
3. Chi non riesce a chiamare uno strumento, e come sbaglia (T1-T3)?

## Parte 2: un esperimento per gruppo (15 minuti)

Ogni gruppo cambia una sola cosa e riesegue. L'opzione `--etichetta` dà un nome alla prova, così nel visore sta
accanto all'originale.

| Gruppo | Che cosa cambia | Comando |
|---|---|---|
| A | La finestra di contesto, da 8192 a 2048 token | `python3 banco.py qwen3.5:4b-q4_K_M --contesto 2048 --etichetta contesto-2k` |
| B | La quantizzazione, da 4 a 8 bit (16 GB di memoria) | `python3 banco.py qwen3.5:4b-q8_0` |
| C | Il ragionamento: il modello pensa prima di rispondere | Due comandi, sotto la tabella |
| D | La taglia a parità di tutto il resto | Confrontare `qwen3.5:4b-q4_K_M` e `qwen3.5:2b-q4_K_M` domanda per domanda |

Per il gruppo C, le stesse sei domande senza e con il ragionamento. Tre il modello le sbaglia, tre le sa già:

```sh
python3 banco.py qwen3.5:2b-q4_K_M --solo E1 E2 E6 F1 S1 S3 --etichetta senza-ragionamento
python3 banco.py qwen3.5:2b-q4_K_M --solo E1 E2 E6 F1 S1 S3 --ragiona --etichetta con-ragionamento
```

Domanda per tutti: che cosa è cambiato nei quattro numeri, e ne valeva la pena?

Per il gruppo A: aprire nel visore la domanda F1 della prova con il contesto piccolo. Il modello ha segnalato
che gli mancava un pezzo del fascicolo?

## Parte 3: le licenze (15 minuti)

```sh
ollama show qwen3.5:4b-q4_K_M --license
ollama show gemma3:4b --license
```

Per i due modelli qui sopra, le tre domande della slide 52: possiamo usarlo per questo scopo, in questo luogo, e possiamo
modificarlo e ridistribuirlo? La risposta va cercata nel testo, non nel nome della licenza.

## Parte 4: l'agente del mattino, in locale (15 minuti)

```sh
python3 agente_locale.py qwen3.5:4b-q4_K_M
```

Lo script fa girare l'agente di riferimento del mattino con il modello locale, e dice quanti documenti ha letto,
se ha inviato l'email, quanti eventi della cronologia ha trovato e quanto ci ha messo. Dura da tre a cinque
minuti. Il risultato compare in fondo al visore.

Per vedere dove sta il cambio, aprire il progetto del mattino in VS Code:

```sh
code ../agent-lab
```

In `esegui.py`, la riga con `LAB_MODEL`: il modello è una stringa. Stamattina era quella di un servizio esterno,
ora è `ollama:<modello>`. Il resto del codice non cambia.

Poi riprovare con un modello più piccolo:

```sh
python3 agente_locale.py qwen3.5:2b-q4_K_M
```

Domanda: il modello che risponde meglio al banco di prova è anche quello che lavora meglio come agente?

Poi aprire nel visore la sezione dell'agente e guardare `nemotron-3-nano:4b`: 14 su 15 sul banco, quanti documenti
letti? Il banco dà i documenti nella domanda e chiede una chiamata sola; l'agente deve decidere da sé che cosa
leggere.

## Da consegnare

La scheda compilata, con l'ultima riga: quale modello per quale compito, e che cosa costa. Le schede dei gruppi
si mettono insieme sulla slide 69.
