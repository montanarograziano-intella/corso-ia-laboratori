"""L'agente di riferimento del laboratorio del giorno 4, parti 1 e 2.

Parte 1: il ciclo con un limite di passi, i tre strumenti di partenza e un quarto che legge i movimenti bancari.
Parte 2: un gate tipizzato sulla bozza di email, un punto di controllo umano prima di `invia_email`, e una traccia
di ogni passo.
"""

from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent, DeferredToolRequests, RunContext, ToolApproved, ToolDenied  # noqa: E402
from pydantic_ai.models import Model  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

import strumenti  # noqa: E402
from gate import DESTINATARI_AMMESSI, Decisione, applica_regole  # noqa: E402
from strumenti import Contesto  # noqa: E402

MAX_PASSI = 25  # richieste al modello in tutta l'esecuzione, comprese le riprese dopo un punto di controllo
ISTRUZIONI = """Sei un assistente che aiuta un investigatore di polizia giudiziaria a lavorare su un fascicolo.
Prima di rispondere leggi tutti i documenti, da DOC-01 a DOC-11, uno per uno. Per i movimenti del conto usa
leggi_movimenti, che dà la riga esatta di ogni movimento. Nella cronologia ogni evento sta su una riga che comincia con la data
e finisce con la fonte, nella forma [DOC-07, riga 12]. Se un dato non è nei documenti, scrivi "non indicato".
Per inviare un'email usa sempre lo strumento invia_email: non scrivere l'email nella risposta.
Rispondi in italiano."""
ISTRUZIONI_GATE = """Valuti la bozza di un'email destinata al PM. Rispondi con una decisione: "procedi" se ogni
evento ha una fonte e il testo è coerente, "chiedi" se hai dubbi, "ferma" se la bozza non va inviata. Indica la
tua confidenza tra 0 e 1, le fonti citate e il motivo in una frase."""


def leggi_movimenti(contesto: Contesto, data_iniziale: str, data_finale: str) -> str:
    """Il quarto strumento della parte 1: i movimenti del conto tra due date (GG/MM/AAAA), con la riga di origine."""
    doc = contesto.documenti.get("DOC-05")
    if doc is None:
        return "documento non trovato: DOC-05"

    def chiave(data: str) -> tuple[int, int, int]:
        giorno, mese, anno = (int(p) for p in data.strip().split("/"))
        return anno, mese, giorno

    try:
        inizio, fine = chiave(data_iniziale), chiave(data_finale)
    except ValueError:
        return "date non valide: usare il formato GG/MM/AAAA"
    righe = [(n, riga) for n, riga in enumerate(doc.righe, 1) if riga.strip() and not riga.startswith("#")]
    intestazione = next(csv.reader(io.StringIO(righe[0][1])))
    trovati = []
    for n, riga in righe[1:]:
        campi = dict(zip(intestazione, next(csv.reader(io.StringIO(riga))), strict=False))
        if inizio <= chiave(campi["data"]) <= fine:
            trovati.append(f"[DOC-05, riga {n}] {campi['data']} {campi['descrizione']} {campi['importo']} {campi['iban_destinatario']}".strip())
    return "\n".join(trovati) or "nessun movimento nell'intervallo"


def crea_agente(modello: Model | str) -> Agent[Contesto, str | DeferredToolRequests]:
    agente: Agent[Contesto, str | DeferredToolRequests] = Agent(modello, deps_type=Contesto, output_type=[str, DeferredToolRequests], instructions=ISTRUZIONI)

    def registra(ctx: RunContext[Contesto], nome: str, argomenti: dict, risultato: str) -> str:
        ctx.deps.traccia.scrivi("strumento", strumento=nome, argomenti=argomenti, risultato=risultato[:120])
        return risultato

    @agente.tool
    def cerca_nel_fascicolo(ctx: RunContext[Contesto], domanda: str) -> str:
        """Cerca nei documenti del fascicolo e restituisce le righe pertinenti con documento e numero di riga."""
        return registra(ctx, "cerca_nel_fascicolo", {"domanda": domanda}, strumenti.cerca_nel_fascicolo(ctx.deps, domanda))

    @agente.tool
    def leggi_documento(ctx: RunContext[Contesto], id_documento: str) -> str:
        """Legge un documento intero, con i numeri di riga. Identificativi da DOC-01 a DOC-11."""
        return registra(ctx, "leggi_documento", {"id_documento": id_documento}, strumenti.leggi_documento(ctx.deps, id_documento))

    @agente.tool(name="leggi_movimenti")
    def movimenti(ctx: RunContext[Contesto], data_iniziale: str, data_finale: str) -> str:
        """Restituisce i movimenti del conto (bonifici, addebiti, accrediti) tra due date, estremi inclusi, ognuno con la riga di origine. Date nel formato GG/MM/AAAA."""
        return registra(ctx, "leggi_movimenti", {"data_iniziale": data_iniziale, "data_finale": data_finale}, leggi_movimenti(ctx.deps, data_iniziale, data_finale))

    @agente.tool(requires_approval=True)
    def invia_email(ctx: RunContext[Contesto], destinatario: str, oggetto: str, testo: str, allegati: list[str]) -> str:
        """Invia un'email. `allegati` è l'elenco degli identificativi dei documenti da allegare; può essere vuoto."""
        return registra(ctx, "invia_email", {"destinatario": destinatario, "oggetto": oggetto, "allegati": allegati}, strumenti.invia_email(ctx.deps, destinatario, oggetto, testo, allegati))

    return agente


def valuta_bozza(modello: Model | str, contesto: Contesto, destinatario: str, testo: str) -> Decisione:
    """Il gate: un giudizio tipizzato del modello, poi le regole scritte in codice."""
    giudice: Agent[None, Decisione] = Agent(modello, output_type=Decisione, instructions=ISTRUZIONI_GATE)
    proposta = giudice.run_sync(f"Destinatario: {destinatario}\n\nBozza:\n{testo}").output
    decisione = applica_regole(proposta, destinatario, testo, contesto.documenti)
    contesto.traccia.scrivi("gate", esito=decisione.esito, confidenza=decisione.confidenza, fonti=decisione.fonti, motivo=decisione.motivo, proposta_del_modello=proposta.esito)
    return decisione


def esegui(modello: Model | str, contesto: Contesto, richiesta: str, chiedi_alla_persona, modello_gate: Model | str | None = None) -> str:
    """Porta l'agente fino in fondo. `chiedi_alla_persona(chiamata, decisione)` restituisce True, un ToolApproved o un ToolDenied."""
    agente = crea_agente(modello)
    limiti = UsageLimits(request_limit=MAX_PASSI)
    contesto.traccia.scrivi("richiesta", testo=richiesta, documenti=sorted(contesto.documenti))
    risultato = agente.run_sync(richiesta, deps=contesto, usage_limits=limiti)
    while isinstance(risultato.output, DeferredToolRequests):
        risposte = {}
        for chiamata in risultato.output.approvals:
            argomenti = chiamata.args_as_dict()
            decisione = valuta_bozza(modello_gate or modello, contesto, argomenti.get("destinatario", ""), argomenti.get("testo", ""))
            if decisione.esito == "ferma":
                risposta, esito, deciso_da = ToolDenied(f"Il gate ha fermato l'invio: {decisione.motivo}"), "fermata dal gate", "gate"
            else:
                risposta = chiedi_alla_persona(chiamata, decisione)
                if isinstance(risposta, ToolApproved) and risposta.override_args:
                    argomenti = risposta.override_args
                    # La persona può cambiare il destinatario, non allargare l'elenco di quelli ammessi.
                    if argomenti.get("destinatario") not in DESTINATARI_AMMESSI:
                        risposta = ToolDenied(f"Destinatario non in elenco: {argomenti.get('destinatario')}. L'email non è stata inviata.")
                esito = "rifiutata" if isinstance(risposta, ToolDenied) else "approvata"
                # Chi ha deciso davvero: la persona, oppure la risposta automatica usata per ripetere un'esecuzione.
                deciso_da = "LAB_RISPOSTA" if os.environ.get("LAB_RISPOSTA") else os.environ.get("USER", "operatore")
            contesto.traccia.scrivi("approvazione", strumento=chiamata.tool_name, argomenti={k: v for k, v in argomenti.items() if k != "testo"}, esito=esito, deciso_da=deciso_da)
            risposte[chiamata.tool_call_id] = risposta
        risultato = agente.run_sync(message_history=risultato.all_messages(), deferred_tool_results=risultato.output.build_results(approvals=risposte), deps=contesto, usage_limits=limiti, usage=risultato.usage)
    contesto.traccia.scrivi("risposta", testo=risultato.output)
    return risultato.output
