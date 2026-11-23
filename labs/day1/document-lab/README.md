# Laboratorio documentale (giorno 1, pomeriggio)

Quattro compiti sul fascicolo di Giulia Neri, nell'ordine: 15 minuti per i primi tre, 10 per l'ultimo. Ogni gruppo
lavora su un solo account della chat messa a disposizione dai docenti. Non si scrive codice.

Tutti i documenti sono sintetici, preparati per il corso.

**I documenti:** gli originali, da incollare nella chat, sono in `data/case-file/core/`; le copie numerate, da leggere
durante i controlli, in `numerati/`, accanto a questo file.

## Come si lavora

- **Ruoli.** Una persona scrive i prompt. Le altre controllano la risposta sui documenti, riga per riga.
- **Una chat nuova per ogni compito.** Così il modello non mescola i documenti del compito prima.
- **Solo i documenti che servono.** Per ogni compito si incolla nel prompt solo il testo indicato, copiato dal file
  originale. Si copia tutto il file, dalla prima all'ultima riga.
- **Le righe.** Per i controlli si legge la copia numerata, dove ogni riga ha il suo numero. Quando scrivete una
  fonte, scrivetela così: «DOC-01, riga 9».
- **Il prompt.** Lo scrivete voi, con le parti della slide 86: ruolo e compito, contesto, formato, vincoli, esempi.
  Se la risposta non regge, correggete il prompt e riprovate.

## I quattro controlli

Su ogni risposta, in quest'ordine (slide 82):

1. **Fonte?** Ogni frase si ritrova nel documento? Cercatela e segnate la riga.
2. **Nomi?** Persone e ruoli sono quelli giusti? Chi ha detto che cosa?
3. **Numeri?** Date, importi e orari coincidono con il documento? Un dato che il documento non ha è inventato.
4. **Cosa manca?** Manca qualcosa che il documento dice?

Quello che trovate va scritto sulla [scheda del gruppo](SCHEDA.md), una riga per compito.

## Compito 1: riassumere la denuncia (15 minuti)

**Da incollare:** DOC-01, `DOC-01-denuncia-neri.txt`.

**Come si parte:** con questo prompt, così com'è.

> Riassumi la denuncia qui sotto in pochi punti.

**Poi:** passate la risposta ai quattro controlli e correggete il prompt finché il riassunto non regge: in ordine
cronologico, con data e ora di ogni fatto, solo dalla denuncia, con la frase da cui viene ogni punto tra
virgolette, «non indicato» quando un dato manca, e alla fine l'elenco di che cosa ha escluso (slide 100).

**I quattro controlli sul riassunto:**

- **Fonte:** per ogni punto, cercate nella denuncia la frase citata e segnate la riga. Se non la trovate, il punto
  non regge.
- **Nomi:** chi è la denunciante, chi ha chiamato, per conto di chi diceva di chiamare.
- **Numeri:** ogni data, ora e importo del riassunto deve essere scritto nella denuncia. Un orario che la denuncia
  non dà è inventato, anche se sembra plausibile.
- **Cosa manca:** rileggete la denuncia dall'inizio e confrontatela con il riassunto e con l'elenco delle
  esclusioni. C'è qualcosa che conta per l'indagine e che è sparito?

**Sulla scheda:** il riassunto dopo il controllo, con data, ora e riga per ogni fatto, e che cosa ha escluso il
modello.

## Compito 2: estrarre la tabella (15 minuti)

**Da incollare, nello stesso prompt:** DOC-01, `DOC-01-denuncia-neri.txt`, e DOC-05, `DOC-05-estratto-conto.csv`
(i movimenti del conto, trascritti dalla signora Neri dall'applicazione della banca).

**Che cosa chiedere:** una tabella di tre colonne, Campo, Valore, Fonte, con una riga per campo anche quando il
dato manca. I campi:

| Campo | Cosa contiene |
|---|---|
| Denunciante | Nome e cognome |
| Data e ora | Del primo contatto del truffatore |
| Canale | SMS, telefono, email, social |
| Importo | In euro, una riga per ogni bonifico in uscita |
| Destinatario | IBAN o carta, una riga per ogni bonifico in uscita |

In Fonte il modello scrive da quale documento prende il valore e riporta la frase o la riga, tra virgolette
(slide 98). Se il dato manca: «non indicato» in Valore e un trattino in Fonte.

**I quattro controlli sulla tabella:**

- **Fonte:** cercate ogni frase della colonna Fonte nel documento. Se c'è e dice quello, scrivete sulla
  scheda il documento e il numero di riga. Se non la trovate, la riga non regge.
- **Nomi:** la denunciante è la persona giusta? Il valore viene dal documento che il modello dichiara?
- **Numeri:** confrontate cifra per cifra importi, date, orari e IBAN con il documento. Un IBAN si legge a gruppi
  di quattro caratteri.
- **Cosa manca:** ci sono tutti i campi? Ogni bonifico in uscita ha il suo importo e il suo destinatario?

**Sulla scheda:** la tabella compilata da voi dopo il controllo, con documento e riga per ogni valore.

## Compito 3: confrontare le due testimonianze (15 minuti)

**Da incollare, nello stesso prompt:** DOC-02, `DOC-02-verbale-paolo-neri.txt`, e DOC-03,
`DOC-03-verbale-anna-riva.txt`.

**Che cosa chiedere:** dove le due testimonianze coincidono e dove divergono, con la frase di ciascuna (slide 102).
Quando una delle due non parla di un punto, il modello deve scriverlo. Non deve dire chi ha ragione.

**I quattro controlli sul confronto:**

- **Fonte:** ogni frase riportata deve stare nel verbale giusto, alla riga che trovate nella copia numerata.
- **Nomi:** chi ha detto che cosa? Chi era presente ai fatti e chi riferisce quello che gli è stato raccontato?
- **Numeri:** confrontate date, orari e importi dei due verbali uno per uno, anche quelli che il modello dà come
  uguali.
- **Cosa manca:** rileggete i due verbali per intero. Ci sono punti che il modello non ha messo in tabella?

**Sulla scheda:** l'elenco delle divergenze, con la frase di ciascun testimone e le righe.

## Compito 4: tradurre dall'inglese (10 minuti)

**Da incollare:** DOC-08, `DOC-08-chat-inglese.txt`.

**Che cosa chiedere:** prima la traduzione in italiano. Poi, in una chat nuova, la ritraduzione in inglese del testo
italiano, senza incollare l'originale (slide 103). Infine confrontate la ritraduzione con l'originale, riga per
riga: dove non coincidono, si torna all'originale.

**I quattro controlli sulla traduzione:**

- **Fonte:** ogni riga tradotta corrisponde a una riga dell'originale? Il modello ha aggiunto frasi o spiegazioni?
- **Nomi:** i nomi utente sono rimasti identici? Chi dice che cosa a chi? Compare un nome che l'originale non ha?
- **Numeri:** date, orari e indicazioni di tempo devono restare identici, nella traduzione e nella ritraduzione.
- **Cosa manca:** c'è una riga, o una parte di riga, che si è persa?

Ricordate: la traduzione dell'AI è una bozza di lavoro. Per un atto serve un traduttore.

## Da consegnare

Una [scheda](SCHEDA.md) per gruppo, con:

- il riassunto del compito 1, con la riga per ogni fatto;
- la tabella di estrazione del compito 2, con documento e riga per ogni valore;
- l'elenco delle divergenze tra le due testimonianze del compito 3;
- una riga per compito: che cosa hanno trovato i quattro controlli.

Le schede si discutono insieme dopo la pausa (slide 122-125).
