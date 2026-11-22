# L'agente a mano (giorno 1, pomeriggio)

Un agente è un modello che sceglie quale strumento usare: elencare i documenti, leggerne uno, inviare un'email.
Qui il modello è quello della chat del laboratorio, e gli strumenti li fate voi. È lo stesso lavoro dell'agente
della demo, un passo alla volta, solo che i passi passano dalle vostre mani.

Tutti i documenti sono sintetici, preparati per il corso.

## Che cosa serve

- La chat del laboratorio documentale, una per gruppo, in una conversazione nuova.
- La pagina del laboratorio, aperta su un telefono o su un portatile: `index.html` di questa cartella, o il codice
  QR della slide. Lì ci sono il prompt, gli strumenti e il registro.
- La cartella che vi assegna il docente: A o B.

## I ruoli

- **Chi scrive** incolla nella chat il prompt e poi ogni risultato.
- **Lo strumento** esegue quello che il modello chiede: tocca ELENCA o LEGGI DOC-xx nella pagina e passa il testo,
  così com'è. Uno strumento non legge, non sceglie e non corregge.
- **Chi approva** decide se l'email parte: legge destinatario, allegati e testo, e fa i controlli della verifica.
- **Chi tiene il registro** scrive sulla scheda ogni strumento eseguito. La pagina tiene lo stesso registro, con
  l'ora.

## I passi

1. Nella pagina scegliete la vostra cartella. Copiate il prompt e incollatelo in una chat nuova.
2. Il modello risponde con una richiesta: ELENCA, oppure LEGGI DOC-xx. Lo strumento tocca il pulsante giusto, chi
   scrive incolla il risultato. Si ripete finché il modello non ha letto quello che gli serve.
3. Alla fine il modello scrive la relazione e una richiesta INVIA_EMAIL. Fermatevi: decide chi approva, dopo la
   verifica. La decisione si incolla con il pulsante «approvata» o «rifiutata».

## La verifica

- **La richiesta di invio.** Il destinatario è quello del compito? Gli allegati, qualcuno li aveva chiesti?
- **La relazione.** Su almeno due parti, i quattro controlli: fonte, nomi, numeri, cosa manca.
- **Il registro.** Ha letto tutti i documenti? Ne ha chiesto qualcuno che non c'è?
- **Il confronto con la registrazione.** Aprite il visore della demo (`../agent-demo/visore/`): esecuzione 1 per la
  cartella A, esecuzione 2 per la cartella B. Stessi documenti, stessi allegati, stessi errori?

Sulla scheda del gruppo: la decisione e il motivo, e una differenza tra il vostro agente e quello della
registrazione.

## Se la chat non va

Si segue la demo sul visore, a gruppi, e si decide lo stesso se l'email parte.
