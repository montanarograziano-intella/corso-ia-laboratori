"""Come il laboratorio di valutazione mostra i risultati: tabelle con spunte, croci e barre dentro un notebook,
testo allineato fuori. Qui non c'è logica dell'agente: solo presentazione.

I colori sono scelti per leggersi su sfondo chiaro e su sfondo scuro. Ogni testo che arriva da un modello passa da
`testo()`, che lo rende innocuo dentro l'HTML.
"""

from __future__ import annotations

import sys
from html import escape

VERDE, ROSSO, GIALLO, GRIGIO = "#2da44e", "#cf222e", "#bf8700", "#8c959f"
SFONDO = {
    VERDE: "rgba(45,164,78,.16)",
    ROSSO: "rgba(207,34,46,.14)",
    GIALLO: "rgba(191,135,0,.16)",
    GRIGIO: "rgba(140,149,159,.14)",
}
# Le targhette hanno testo bianco su un fondo pieno e più scuro: si leggono su sfondo chiaro e su sfondo scuro.
PIENO = {VERDE: "#1a7f37", ROSSO: "#cf222e", GIALLO: "#9a6700", GRIGIO: "#6e7781"}
CELLA = "padding:6px 12px;text-align:left;vertical-align:top;border-bottom:1px solid rgba(140,149,159,.3)"


def in_un_notebook() -> bool:
    return "ipykernel" in sys.modules


def mostra(html: str, alternativa: str) -> None:
    """Dentro un notebook disegna l'HTML; in un terminale stampa il testo."""
    if in_un_notebook():
        from IPython.display import HTML, display

        display(HTML(html))
    else:
        print(alternativa)


def testo(valore: object) -> str:
    return escape(str(valore))


def nome(valore: object) -> str:
    """Un nome tecnico (un modello, una voce) in carattere a spaziatura fissa, su una riga sola."""
    return f'<code style="white-space:nowrap">{testo(valore)}</code>'


def etichetta(scritta: str, colore: str) -> str:
    """Una piccola targhetta colorata, per esempio «✓ corretto»."""
    stile = f"display:inline-block;padding:1px 9px;border-radius:10px;font-weight:600;color:#fff;background:{PIENO[colore]};white-space:nowrap"
    return f'<span style="{stile}">{testo(scritta)}</span>'


def spunta(vero: bool, si: str = "✓", no: str = "✗") -> str:
    return etichetta(si, VERDE) if vero else etichetta(no, ROSSO)


def colore_del_rapporto(giusti: int, totale: int) -> str:
    if totale == 0:
        return GRIGIO
    return VERDE if giusti == totale else ROSSO if giusti == 0 else GIALLO


def rapporto(giusti: int, totale: int) -> str:
    """«3/6» colorato: verde se tutti, rosso se nessuno, giallo in mezzo."""
    return (
        etichetta(f"{giusti}/{totale}", colore_del_rapporto(giusti, totale))
        if totale
        else '<span style="opacity:.5">-</span>'
    )


def barra(giusti: int, totale: int, larghezza: int = 120) -> str:
    """Una barra che si riempie in proporzione, con il numero accanto."""
    piena = round(larghezza * giusti / totale) if totale else 0
    colore = colore_del_rapporto(giusti, totale)
    return (
        '<span style="white-space:nowrap">'
        f'<span style="display:inline-block;width:{larghezza}px;height:10px;border-radius:5px;background:{SFONDO[GRIGIO]};vertical-align:middle">'
        f'<span style="display:block;width:{piena}px;height:10px;border-radius:5px;background:{colore}"></span></span>'
        f' <b style="margin-left:6px">{giusti} su {totale}</b></span>'
    )


def tabella(intestazioni: list[str], righe: list[list[str]], numeri: tuple[int, ...] = ()) -> str:
    """Una tabella HTML. Le celle sono già HTML: chi le prepara usa `testo()` per i testi. `numeri`: colonne a destra."""

    def cella(tag: str, contenuto: str, colonna: int) -> str:
        allinea = ";text-align:right" if colonna in numeri else ""
        return f'<{tag} style="{CELLA}{allinea}">{contenuto}</{tag}>'

    testa = "".join(cella("th", testo(i), n) for n, i in enumerate(intestazioni))
    corpo = "".join("<tr>" + "".join(cella("td", c, n) for n, c in enumerate(riga)) + "</tr>" for riga in righe)
    return f'<table style="border-collapse:collapse;margin:6px 0"><thead><tr>{testa}</tr></thead><tbody>{corpo}</tbody></table>'


class Avanzamento:
    """Una tabella che cresce una riga alla volta mentre la prova gira. In un terminale stampa una riga di testo."""

    def __init__(self, intestazioni: list[str], numeri: tuple[int, ...] = ()) -> None:
        self.intestazioni, self.numeri, self.righe, self.schermo = intestazioni, numeri, [], None
        if in_un_notebook():
            from IPython.display import HTML, display

            self.schermo = display(HTML(""), display_id=True)

    def _disegna(self, html: str) -> None:
        from IPython.display import HTML

        self.schermo.update(HTML(html))

    def riga(self, celle_html: list[str], alternativa: str) -> None:
        if self.schermo is None:
            print(alternativa)
            return
        self.righe.append(celle_html)
        self._disegna(tabella(self.intestazioni, self.righe, self.numeri))

    def chiudi(self, html: str, alternativa: str) -> None:
        """Alla fine la tabella lascia il posto a una riga di riepilogo: il dettaglio lo mostra `tabella()`."""
        if self.schermo is None:
            print(alternativa)
        else:
            self._disegna(html)


def avviso(frase: str, colore: str = GIALLO) -> None:
    mostra(riquadro(testo(frase), "", colore), frase)


def riquadro(titolo_html: str, corpo_html: str, colore: str = GRIGIO) -> str:
    """Un riquadro con una riga colorata a sinistra: per un avviso o per un errore da leggere."""
    stile = (
        f"border-left:4px solid {colore};background:{SFONDO[colore]};padding:8px 14px;margin:8px 0;border-radius:4px"
    )
    return f'<div style="{stile}"><div style="font-weight:600;margin-bottom:4px">{titolo_html}</div>{corpo_html}</div>'


def misure(voci: list[tuple[str, str]]) -> str:
    """Una fila di numeri grandi con la loro didascalia sotto."""
    blocchi = "".join(
        f'<div style="display:inline-block;margin:4px 28px 4px 0"><div style="font-size:1.5em;font-weight:600">{valore}</div>'
        f'<div style="opacity:.7;font-size:.9em">{testo(nome)}</div></div>'
        for nome, valore in voci
    )
    return f'<div style="margin:6px 0">{blocchi}</div>'
