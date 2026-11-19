# Laboratori del corso di intelligenza artificiale

Il materiale dei laboratori al computer: il codice di partenza, i documenti su cui lavorare e le istruzioni.

Tutti i dati sono sintetici e scritti per il corso: persone, luoghi, conti, numeri di telefono e indirizzi non
esistono. I domini finiscono in `.invalid` e gli indirizzi IP sono quelli riservati alla documentazione.

## Che cosa c'è

| Cartella | Giorno | Che cos'è |
|---|---|---|
| `labs/day4/agent-lab/` | 4, mattina | Un agente che lavora su un fascicolo, con controlli e traccia |
| `labs/day4/local-models-lab/` | 4, pomeriggio | Modelli piccoli sul proprio portatile, messi a confronto |
| `data/case-file/` | 3, 4 e 5 | Il fascicolo: dieci documenti, più uno con un'istruzione nascosta |

Ogni laboratorio ha il suo `README.md`, con i comandi da eseguire. Si parte da lì.

## Per cominciare

Servono `git` e [`uv`](https://docs.astral.sh/uv/). Poi:

```sh
git clone <indirizzo di questo repository>
cd <cartella clonata>/labs/day4/agent-lab
uv sync
```

Nei giorni successivi i docenti aggiungono materiale. Per riceverlo, dalla cartella clonata:

```sh
git pull
```

## Le chiavi

Le chiavi dei modelli le danno i docenti in aula. Vanno solo nel file `.env` del laboratorio, che git ignora: non
si scrivono in nessun altro file e non si pubblicano.

## Uso

Materiale didattico riservato ai partecipanti del corso. Tutti i diritti riservati.
