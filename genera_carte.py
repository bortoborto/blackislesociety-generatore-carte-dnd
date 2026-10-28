#!/usr/bin/env python3
"""
Genera le carte incantesimo in A3 (5 x 5 carte per pagina, fronte/retro)
a partire dal CSV degli incantesimi.

Produce due PDF:
  - carte_scure_A3.pdf  : layout scuro, identico alla versione precedente
  - carte_chiare_A3.pdf : layout chiaro (consuma molto meno inchiostro)

Uso:
    pip install reportlab pillow
    python genera_carte.py incantesimi_completo_it.csv

Opzioni utili:
    --testo auto|completo|breve   testo da usare sulla carta (default: auto)
    --solo scuro|chiaro           genera un solo layout
    --senza-retro                 non inserisce le pagine del retro
    --senza-diagrammi             non disegna i diagrammi di gittata/area
    --senza-pagina                non stampa "SRD 5.2.1 · p. N" in fondo alla descrizione
    --classe mago                 stampa solo gli incantesimi di una classe
    --per-classe                  crea anche una cartella per classe (Bardo/, Mago/, ...)
                                  con dentro i PDF scuro e chiaro di quella classe
    --solo-classi                 come --per-classe, ma senza i PDF completi
    --retro-standard              nei PDF per classe usa il retro normale
                                  (di default ogni classe ha il suo retro)
    --bis                         edizione Black Isle Society: fronte in bianco e
                                  nero e in versione chiara, retro nero con il logo
                                  (logo in assets/logo_bis.png o con --logo PERCORSO)
    --poker                       carte formato poker (63 x 88 mm) con la cornice
                                  grafica, logo nel cartiglio e retro tutto nero;
                                  crea le versioni scura, bianco e nero e chiara
    --foglio A3|A4                foglio per --poker (A3: 16 carte, A4: 9 carte)
    --nero-k                      retro nero come 100% K in CMYK (solo inchiostro nero)
    --piega                       (con --poker) fronte e retro con logo affiancati sullo
                                  stesso lato: si stampa solo il fronte del foglio e si
                                  piega. A3 orizzontale: 9 carte, A4 orizzontale: 4 carte
    --fronte-standard             nei PDF per classe usa il fronte normale
                                  (di default il fronte e' tinto nel colore della classe)
    --out-dir cartella            dove salvare i PDF

Con --testo auto (default) la descrizione completa viene rimpicciolita fino a
un minimo leggibile; se ancora non entra, la carta usa la descrizione breve.
Alla fine lo script elenca le carte in cui è successo.
"""
import argparse
import csv
import datetime
import io
import os
import re
import sys
from xml.sax.saxutils import escape

from PIL import Image, ImageOps, ImageEnhance
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONTS = os.path.join(BASE, "fonts")

# --------------------------------------------------------------------------
# Geometria (in punti PDF), misurata sul PDF originale
# --------------------------------------------------------------------------
PAGE_W, PAGE_H = 841.89, 1190.55          # A3
COLS, ROWS = 5, 5
MARGIN_X, MARGIN_Y = 10.1, 10.1
PITCH_X, PITCH_Y = 166.2, 235.7
CARD_W, CARD_H = 157.0, 226.5
CARD_R = 5.0

PAD_X = 6.0                 # margine interno sinistro/destro
SEP1_Y = 34.0               # linea sotto il titolo (dall'alto della carta)
STATS_Y = 43.5              # centro della riga gittata/durata/tempo
SEP2_Y = 52.5               # linea sotto la riga statistiche
TEXT_TOP = 56.0             # inizio del testo
FOOT_SEP_Y = 208.0          # linea sopra il piede
FOOT_Y = 217.0              # centro icone del piede
DIAGRAM_H = 34.0

# --------------------------------------------------------------------------
# Temi
# --------------------------------------------------------------------------
THEMES = {
    "scuro": dict(
        page_bg="#575757", cut="#818181",
        card_fill="#373737", card_fill_top="#3a3a3a", card_border="#242424",
        sep="#575757", title="#ffffff", text="#f2f2f2", stat_text="#f2f2f2",
        dice="#ede8a7", damage="#e6a0a8", save="#ede8a7", dist="#9cb4d7",
        cond="#e6a0a8", hl_box="#8a8a8a", hl_icon="#e5894d",
        ring_fill="#2b2b2b", ring_stroke="#9a9a9a", ring_text="#d8d8d8",
        grid="#ffffff", grid_alpha=0.10, diag_line="#ffffff", diag_label="#dddddd",
        start="#9cd7e8", end="#e64545", area="#e64545",
        icon_mode="orig", back="dark",
    ),
    "chiaro": dict(
        page_bg="#ffffff", cut="#bdbdbd",
        card_fill="#fbf8f2", card_fill_top="#fbf8f2", card_border="#b9ae9c",
        sep="#d8cfbf", title="#2a2a2a", text="#262626", stat_text="#2a2a2a",
        dice="#8a6400", damage="#b3283a", save="#8a6400", dist="#245c9e",
        cond="#b3283a", hl_box="#b0a48f", hl_icon="#c0632a",
        ring_fill="#ffffff", ring_stroke="#8c8270", ring_text="#3a3a3a",
        grid="#5a4f3f", grid_alpha=0.16, diag_line="#3a3a3a", diag_label="#3a3a3a",
        start="#2a8fb0", end="#c62828", area="#c62828",
        icon_mode="light", back="light",
    ),
}

# tema bianco e nero (edizione Black Isle Society): niente colori,
# le evidenziazioni diventano grassetto
THEMES["bn"] = dict(
    page_bg="#ffffff", cut="#b5b5b5",
    card_fill="#ffffff", card_fill_top="#ffffff", card_border="#000000",
    sep="#9a9a9a", title="#000000", text="#000000", stat_text="#000000",
    dice="#000000", damage="#000000", save="#000000", dist="#000000",
    cond="#000000", hl_box="#555555", hl_icon="#000000",
    ring_fill="#ffffff", ring_stroke="#000000", ring_text="#000000",
    grid="#000000", grid_alpha=0.16, diag_line="#000000", diag_label="#000000",
    start="#000000", end="#000000", area="#000000",
    icon_mode="bw", back="bis", hl_bold=True,
)

SCUOLE = ["abiurazione", "ammaliamento", "divinazione", "evocazione",
          "illusione", "invocazione", "necromanzia", "trasmutazione"]
ORDINE_CLASSI = ["bardo", "chierico", "druido", "paladino", "ranger",
                 "stregone", "warlock", "mago"]
# colore di ogni classe per i retri dedicati (--per-classe).
# Tavolozza ispirata ai colori delle classi usati da D&D Beyond (valori approssimativi).
COLORI_CLASSE = {
    "bardo": "#ab6dac", "chierico": "#91a1b2", "druido": "#7a853b",
    "paladino": "#b59e54", "ranger": "#507f62", "stregone": "#992e2e",
    "warlock": "#7b469b", "mago": "#2a50a1",
}
ROMANI = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]

# --------------------------------------------------------------------------
# Font
# --------------------------------------------------------------------------
def registra_font():
    nomi = {"F": "Ubuntu-Regular.ttf", "F-M": "Ubuntu-Medium.ttf",
            "F-B": "Ubuntu-Bold.ttf", "F-I": "Ubuntu-Italic.ttf"}
    if all(os.path.exists(os.path.join(FONTS, f)) for f in nomi.values()):
        for k, f in nomi.items():
            pdfmetrics.registerFont(TTFont(k, os.path.join(FONTS, f)))
    else:
        print("Font Ubuntu non trovato in ./fonts, uso DejaVu Sans se disponibile.")
        try:
            pdfmetrics.registerFont(TTFont("F", "DejaVuSans.ttf"))
            pdfmetrics.registerFont(TTFont("F-B", "DejaVuSans-Bold.ttf"))
            pdfmetrics.registerFont(TTFont("F-M", "DejaVuSans-Bold.ttf"))
            pdfmetrics.registerFont(TTFont("F-I", "DejaVuSans-Oblique.ttf"))
        except Exception:
            sys.exit("Nessun font utilizzabile: metti i file Ubuntu-*.ttf nella cartella fonts/")
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("F", normal="F", bold="F-B", italic="F-I", boldItalic="F-B")

# --------------------------------------------------------------------------
# Icone
# --------------------------------------------------------------------------
_ICON_CACHE = {}

def icona(nome, mode):
    """Restituisce un ImageReader dell'icona, adattata al tema."""
    key = (nome, mode)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    path = os.path.join(ASSETS, nome + ".png")
    if not os.path.exists(path):
        _ICON_CACHE[key] = None
        return None
    im = Image.open(path).convert("RGBA")
    if mode == "bw":
        a = im.split()[3].point(lambda v: 0 if v < 70 else min(255, int((v - 70) * 1.5)))
        im = Image.new("RGBA", im.size, (0, 0, 0, 255))
        im.putalpha(a)
    if mode == "light":
        r, g, b, a = im.split()
        rgb = Image.merge("RGB", (r, g, b))
        # icone bianche/grigie (componenti): diventano grigio scuro
        if nome.startswith("comp_"):
            rgb = Image.new("RGB", im.size, (70, 70, 70))
        else:
            # scurisce leggermente e rimuove l'alone chiaro
            rgb = ImageEnhance.Brightness(rgb).enhance(0.68)
            a = a.point(lambda v: 0 if v < 70 else min(255, int((v - 70) * 1.4)))
        im = Image.merge("RGBA", (*rgb.split(), a))
    rd = ImageReader(im)
    _ICON_CACHE[key] = (rd, im.size)
    return _ICON_CACHE[key]


def disegna_icona(c, nome, x, y_center, h, mode, align="left"):
    """Disegna l'icona alta h, centrata verticalmente; ritorna la larghezza."""
    ic = icona(nome, mode)
    if not ic:
        return 0
    rd, (w0, h0) = ic
    w = h * w0 / h0
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    c.drawImage(rd, x, y_center - h / 2, w, h, mask="auto")
    return w

# --------------------------------------------------------------------------
# Normalizzazione dei campi
# --------------------------------------------------------------------------
def breve_gittata(g):
    g0 = (g or "").strip()
    low = g0.lower()
    if low.startswith("contatto"):
        return "gittata_contatto", "Contatto"
    if low.startswith("incantatore") or low.startswith("sé"):
        return "gittata_incantatore", "Sé"
    m = re.match(r"([\d.,]+)\s*(metri|metro|m|chilometri|chilometro|km)\b", low)
    if m:
        unit = "km" if m.group(2).startswith(("chil", "km")) else "m"
        return "gittata_distanza", f"{m.group(1)} {unit}"
    return "gittata_distanza", g0[:14]


def breve_durata(d):
    d0 = (d or "").strip()
    low = d0.lower()
    conc = low.startswith("concentrazione")
    if low.startswith("istantanea"):
        return "durata_istantanea", "Istantanea"
    m = re.search(r"(\d+)\s*(round|minut[oi]|or[ae]|giorn[oi]|anni?)", low)
    if m:
        n, u = m.group(1), m.group(2)
        u = {"r": "r", "m": "min", "o": "h", "g": "g", "a": "anni"}[u[0]]
        txt = f"{n} {u}" + ("*" if conc else "")
        return ("durata_concentrazione" if conc else "durata_tempo"), txt
    if "dissolt" in low:
        return "durata_tempo", "Permanente"
    if "speciale" in low:
        return "durata_tempo", "Speciale"
    return ("durata_concentrazione" if conc else "durata_tempo"), d0[:12]


def breve_tempo(breve, completo):
    b = (breve or completo or "").strip()
    low = b.lower()
    if low.startswith("reazione"):
        return "tempo_reazione", "Reazione"
    if low.startswith("azione bonus"):
        return "tempo_bonus", "Bonus"
    if low.startswith("azione"):
        return "tempo_azione", "Azione"
    m = re.match(r"(\d+)\s*(minut[oi]|or[ae])", low)
    if m:
        u = "min" if m.group(2).startswith("min") else "h"
        return "tempo_lungo", f"{m.group(1)} {u}"
    return "tempo_lungo", b[:10]


def trigger_tempo(completo):
    """Testo dell'innesco (reazioni e punizioni), se presente."""
    t = (completo or "").strip()
    low = t.lower()
    if low.startswith("reazione") or (low.startswith("azione bonus") and len(t) > 14):
        t = t[0].upper() + t[1:]
        return t
    return ""

# --------------------------------------------------------------------------
# Testo con evidenziazioni
# --------------------------------------------------------------------------
HL_RE = re.compile(
    r"(?P<dice>\b\d*d\d+(?:\s*[+−]\s*\d+)?\b)"
    r"|(?P<damage>danni\s+(?:da\s+|di\s+)?(?:acido|freddo|fuoco|fulmine|tuono|veleno|forza)\b"
    r"|danni\s+(?:necrotici|radiosi|psichici|contundenti|perforanti|taglienti)\b)"
    r"|(?P<save>tir[oi]\s+salvezza\s+su\s+(?:Forza|Destrezza|Costituzione|Intelligenza|Saggezza|Carisma)"
    r"|attacc[oh]i?\s+(?:a\s+distanza\s+|in\s+mischia\s+)?con\s+(?:l')?incantesimo(?:\s+in\s+mischia|\s+a\s+distanza)?)"
    r"|(?P<dist>\b\d+(?:,\d+)?\s+(?:metri|metro|centimetri|chilometri)\b)"
    r"|(?P<cond>\b(?:svantaggio|vantaggio)\b)",
    re.IGNORECASE,
)


def evidenzia(testo, th):
    out = []
    pos = 0
    for m in HL_RE.finditer(testo):
        out.append(escape(testo[pos:m.start()]))
        col = th[m.lastgroup]
        frag = escape(m.group(0))
        if th.get("hl_bold") and m.lastgroup in ("dice", "damage", "save"):
            frag = f"<b>{frag}</b>"
        out.append(f'<font color="{col}">{frag}</font>')
        pos = m.end()
    out.append(escape(testo[pos:]))
    return "".join(out)


def markup(par, th):
    """Converte **grassetto** e aggiunge le evidenziazioni."""
    parti = re.split(r"\*\*(.+?)\*\*", par)
    out = []
    for i, p in enumerate(parti):
        if i % 2 == 1:
            out.append(f"<b>{escape(p)}</b>")
        else:
            out.append(evidenzia(p, th))
    return "".join(out)

# --------------------------------------------------------------------------
# Diagrammi gittata / area
# --------------------------------------------------------------------------
NUM = r"(\d+(?:,\d+)?)"

def num(s):
    return float(s.replace(",", "."))


def analizza_area(r):
    testo = " ".join([r.get("gittata", ""), r.get("descrizione_completa", ""),
                      r.get("descrizione_breve", "")]).lower()
    pats = [
        ("cono", rf"cono\s+(?:di|lungo)\s+{NUM}\s+m"),
        ("linea", rf"linea\s+(?:lunga\s+)?{NUM}\s+m"),
        ("linea", rf"linea\s+(?:larga\s+[\d,]+\s+metri\s+e\s+)?lunga\s+{NUM}\s+m"),
        ("cubo", rf"cubo\s+(?:con\s+spigolo\s+)?di\s+{NUM}\s+m"),
        ("quadrato", rf"quadrat[oi]\s+(?:con\s+lato\s+)?di\s+{NUM}\s+m"),
        ("sfera", rf"sfera\s+(?:del\s+|dal\s+|di\s+)?(?:raggio\s+(?:di\s+)?)?{NUM}\s+m"),
        ("sfera", rf"cilindro\s+(?:del\s+|dal\s+)?raggio\s+di\s+{NUM}\s+m"),
        ("sfera", rf"raggio\s+(?:di\s+)?{NUM}\s+m"),
        ("emanazione", rf"emanazione\s+di\s+{NUM}\s+m"),
    ]
    best = None
    for kind, p in pats:
        m = re.search(p, testo)
        if m and (best is None or m.start() < best[2]):
            best = (kind, num(m.group(1)), m.start())
    return (best[0], best[1]) if best else None


def disegna_griglia(c, x, y, w, h, th, cell):
    gcol = HexColor(th["grid"])
    cx, cy = x + w / 2, y + h / 2
    c.saveState()
    c.setLineWidth(0.3)
    nx = int(w / cell) + 1
    ny = int(h / cell) + 1
    for i in range(nx + 1):
        xx = cx + (i - nx / 2) * cell
        if xx < x or xx > x + w:
            continue
        for j in range(ny):
            y0 = cy + (j - ny / 2) * cell
            y1 = y0 + cell
            y0, y1 = max(y0, y), min(y1, y + h)
            if y1 <= y0:
                continue
            d = max(abs(xx - cx) / (w / 2), abs((y0 + y1) / 2 - cy) / (h / 2))
            a = th["grid_alpha"] * max(0, 1 - d ** 2)
            c.setStrokeColor(gcol, alpha=a)
            c.line(xx, y0, xx, y1)
    for j in range(ny + 1):
        yy = cy + (j - ny / 2) * cell
        if yy < y or yy > y + h:
            continue
        for i in range(nx):
            x0 = cx + (i - nx / 2) * cell
            x1 = x0 + cell
            x0, x1 = max(x0, x), min(x1, x + w)
            if x1 <= x0:
                continue
            d = max(abs((x0 + x1) / 2 - cx) / (w / 2), abs(yy - cy) / (h / 2))
            a = th["grid_alpha"] * max(0, 1 - d ** 2)
            c.setStrokeColor(gcol, alpha=a)
            c.line(x0, yy, x1, yy)
    c.restoreState()


def etichetta(c, x, y, txt, th, size=4.6):
    c.setFont("F", size)
    c.setFillColor(HexColor(th["diag_label"]))
    c.drawCentredString(x, y, txt)


def fmt_m(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{s} m"


def disegna_diagramma(c, r, x, y, w, h, th):
    """Disegna il diagramma; ritorna True se c'era qualcosa da disegnare."""
    gtype, gtxt = breve_gittata(r.get("gittata", ""))
    area = analizza_area(r)
    dist = None
    if gtype == "gittata_distanza":
        m = re.match(r"([\d,]+)\s*(m|km)", gtxt)
        if m:
            dist = num(m.group(1)) * (1000 if m.group(2) == "km" else 1)
    if dist is None and area is None:
        return False
    cx, cy = x + w / 2, y + h / 2
    start_c, end_c = HexColor(th["start"]), HexColor(th["end"])
    if area is None:
        # linea di gittata
        cell = max(4.0, min(7.0, (w - 24) / max(dist / 1.5, 1)))
        disegna_griglia(c, x, y, w, h, th, cell)
        L = min(w - 24, max(30, (dist / 1.5) * cell))
        x0, x1 = cx - L / 2, cx + L / 2
        c.setStrokeColor(HexColor(th["diag_line"]))
        c.setLineWidth(0.6)
        c.setDash(1.6, 1.4)
        c.line(x0 + 2.6, cy, x1 - 2.6, cy)
        c.setDash()
        c.setLineWidth(0.9)
        c.setStrokeColor(start_c)
        c.circle(x0, cy, 2.4, stroke=1, fill=0)
        c.setStrokeColor(end_c)
        c.circle(x1, cy, 2.4, stroke=1, fill=0)
        etichetta(c, cx, cy + 3.2, fmt_m(dist) if dist < 1000 else f"{dist/1000:g} km".replace(".", ","), th)
        return True

    kind, size = area
    span = size * (2 if kind in ("sfera", "emanazione") else 1)
    span = max(span, 3)
    lim = (h - 9) if kind in ("sfera", "emanazione", "cubo", "quadrato", "cono") else (w - 14)
    unit = min(6.5 / 1.5, lim / span)          # punti per metro
    cell = unit * 1.5
    while cell < 2.8:                           # griglia piu' rada se le caselle sono minuscole
        cell *= 2
    disegna_griglia(c, x, y, w, h, th, cell)
    ac = HexColor(th["area"])
    c.setStrokeColor(ac)
    c.setLineWidth(0.8)
    c.setFillColor(ac, alpha=0.22)
    lab = ""
    if kind in ("sfera", "emanazione"):
        R = size * unit
        c.circle(cx, cy, R, stroke=1, fill=1)
        c.setFillColor(start_c if kind == "emanazione" else end_c)
        c.circle(cx, cy, 1.2, stroke=0, fill=1)
        lab = ("raggio " if kind == "sfera" else "emanazione ") + fmt_m(size)
        ly = min(cy + R + 2.2, y + h - 4)
    elif kind in ("cubo", "quadrato"):
        S = size * unit
        c.rect(cx - S / 2, cy - S / 2, S, S, stroke=1, fill=1)
        lab = ("cubo " if kind == "cubo" else "quadrato ") + fmt_m(size)
        ly = min(cy + S / 2 + 2.2, y + h - 4)
    elif kind == "cono":
        L = size * unit
        x0 = cx - L / 2
        p = c.beginPath()
        p.moveTo(x0, cy)
        p.lineTo(x0 + L, cy + L / 2)
        p.lineTo(x0 + L, cy - L / 2)
        p.close()
        c.drawPath(p, stroke=1, fill=1)
        c.setStrokeColor(start_c)
        c.circle(x0, cy, 2.2, stroke=1, fill=0)
        lab = "cono " + fmt_m(size)
        ly = y + h - 4
    else:  # linea
        L = min(size * unit, w - 10)
        x0 = cx - L / 2
        c.rect(x0, cy - 1.5, L, 3, stroke=1, fill=1)
        c.setStrokeColor(start_c)
        c.circle(x0, cy, 2.2, stroke=1, fill=0)
        lab = "linea " + fmt_m(size)
        ly = cy + 4
    etichetta(c, cx, ly, lab, th)
    if dist:
        etichetta(c, x + w - 16, y + 2, "gittata " + fmt_m(dist), th, 4.2)
    return True

# --------------------------------------------------------------------------
# Corpo del testo
# --------------------------------------------------------------------------
def blocchi_testo(r, th, fs, modo_testo):
    """Costruisce la lista di blocchi (tipo, Paragraph)."""
    lead = fs * 1.2
    st = ParagraphStyle("t", fontName="F", fontSize=fs, leading=lead,
                        textColor=HexColor(th["text"]), alignment=TA_JUSTIFY,
                        spaceAfter=fs * 0.55)
    st_small = ParagraphStyle("s", parent=st, alignment=TA_LEFT)
    completo = (r.get("descrizione_completa") or "").strip()
    usa_breve = modo_testo == "breve" or not completo
    testo = r["descrizione_breve"] if usa_breve else completo
    blocchi = []
    for par in [p for p in testo.split("\n") if p.strip()]:
        blocchi.append(("p", Paragraph(markup(par, th), st)))
    mat = (r.get("materiale") or "").strip()
    if mat:
        mat = mat[0].upper() + mat[1:]
        blocchi.append(("icon:comp_m", Paragraph(escape(mat), st_small)))
    trig = trigger_tempo(r.get("tempo_di_lancio", ""))
    if trig:
        tipo = "tempo_reazione" if trig.lower().startswith("reazione") else "tempo_bonus"
        blocchi.append((f"icon:{tipo}", Paragraph(evidenzia(trig, th), st_small)))
    for campo in ("livelli_superiori", "trucchetto_potenziato"):
        v = (r.get(campo) or "").strip()
        if v:
            blocchi.append(("box", Paragraph(markup(v, th), st_small)))
    return blocchi, usa_breve


def misura(blocchi, w, fs):
    tot = 0
    for tipo, p in blocchi:
        if tipo == "p":
            _, h = p.wrap(w, 1000)
            tot += h + fs * 0.55
        elif tipo.startswith("icon:"):
            _, h = p.wrap(w - fs * 1.7, 1000)
            tot += h + fs * 0.45
        else:
            _, h = p.wrap(w - 8 - fs * 1.6, 1000)
            tot += h + 6 + fs * 0.5
    return tot


def disegna_blocchi(c, blocchi, x, y_top, w, fs, th, mode):
    y = y_top
    for tipo, p in blocchi:
        if tipo == "p":
            _, h = p.wrap(w, 1000)
            p.drawOn(c, x, y - h)
            y -= h + fs * 0.55
        elif tipo.startswith("icon:"):
            nome = tipo.split(":", 1)[1]
            _, h = p.wrap(w - fs * 1.7, 1000)
            disegna_icona(c, nome, x, y - fs * 0.62, fs * 1.15, mode)
            p.drawOn(c, x + fs * 1.7, y - h)
            y -= h + fs * 0.45
        else:
            iw = fs * 1.6
            _, h = p.wrap(w - 8 - iw, 1000)
            bh = h + 6
            c.saveState()
            c.setStrokeColor(HexColor(th["hl_box"]))
            c.setLineWidth(0.5)
            c.setDash(1.5, 1.2)
            c.roundRect(x, y - bh, w, bh, 2, stroke=1, fill=0)
            c.restoreState()
            # doppia freccia (chevron) come nell'originale
            c.saveState()
            c.setStrokeColor(HexColor(th["hl_icon"]))
            c.setLineWidth(0.6)
            ix, iy = x + 4 + iw * 0.35, y - 3 - fs * 0.55
            for dy in (0, fs * 0.38):
                c.line(ix - fs * 0.32, iy - fs * 0.15 - dy, ix, iy + fs * 0.15 - dy)
                c.line(ix, iy + fs * 0.15 - dy, ix + fs * 0.32, iy - fs * 0.15 - dy)
            c.restoreState()
            p.drawOn(c, x + 4 + iw, y - 3 - h)
            y -= bh + fs * 0.5
    return y

# --------------------------------------------------------------------------
# Carta
# --------------------------------------------------------------------------
def disegna_titolo(c, nome, x0, x1, y_center, th):
    c.setFillColor(HexColor(th["title"]))
    w = x1 - x0
    for size in (12.5, 12, 11.5, 11):
        if pdfmetrics.stringWidth(nome, "F-M", size) <= w:
            c.setFont("F-M", size)
            c.drawString(x0, y_center - size * 0.35, nome)
            return
    # due righe
    parole = nome.split()
    for size in (10.5, 10, 9.5, 9, 8.5, 8, 7.5, 7):
        righe, cur = [], ""
        for p in parole:
            t = (cur + " " + p).strip()
            if pdfmetrics.stringWidth(t, "F-M", size) <= w:
                cur = t
            else:
                righe.append(cur)
                cur = p
        righe.append(cur)
        if len(righe) <= 2 and all(pdfmetrics.stringWidth(rr, "F-M", size) <= w for rr in righe):
            c.setFont("F-M", size)
            lead = size * 1.02
            top = y_center + (len(righe) - 1) * lead / 2 - size * 0.35
            for i, rr in enumerate(righe):
                c.drawString(x0, top - i * lead, rr)
            return
    c.setFont("F-M", 7)
    c.drawString(x0, y_center - 2.5, nome[:28])


def disegna_livello(c, livello, cx, cy, th):
    c.saveState()
    c.setFillColor(HexColor(th["ring_fill"]))
    c.setStrokeColor(HexColor(th["ring_stroke"]))
    c.setLineWidth(1.1)
    c.circle(cx, cy, 8.6, stroke=1, fill=1)
    c.setLineWidth(0.4)
    c.circle(cx, cy, 7.2, stroke=1, fill=0)
    txt = ROMANI[livello]
    size = 9 if len(txt) <= 2 else (7.2 if len(txt) == 3 else 6.4)
    c.setFillColor(HexColor(th["ring_text"]))
    c.setFont("F-M", size)
    c.drawCentredString(cx, cy - size * 0.36, txt)
    c.restoreState()


def disegna_carta(c, r, ox, oy, th, opts, report):
    """ox, oy: angolo in basso a sinistra della carta."""
    mode = th["icon_mode"]
    top = oy + CARD_H

    def Y(d):  # distanza dall'alto della carta -> coordinata PDF
        return top - d

    # sfondo carta
    c.saveState()
    c.setFillColor(HexColor(th["card_fill"]))
    c.setStrokeColor(HexColor(th["card_border"]))
    c.setLineWidth(0.8)
    c.roundRect(ox, oy, CARD_W, CARD_H, CARD_R, stroke=1, fill=1)
    c.restoreState()

    # intestazione
    scuola = (r.get("scuola") or "").strip().lower()
    disegna_icona(c, f"scuola_{scuola}", ox + 4.5, Y(17.5), 25, mode)
    disegna_titolo(c, r["nome"], ox + 36, ox + CARD_W - 28, Y(17.5), th)
    disegna_livello(c, int(r["livello"]), ox + CARD_W - 16.5, Y(17.5), th)

    c.setStrokeColor(HexColor(th["sep"]))
    c.setLineWidth(0.7)
    for d in (SEP1_Y, SEP2_Y, FOOT_SEP_Y):
        c.line(ox + PAD_X, Y(d), ox + CARD_W - PAD_X, Y(d))

    # statistiche
    ih, fsz = 9.5, 8.2
    c.setFillColor(HexColor(th["stat_text"]))
    c.setFont("F", fsz)
    gi, gt = breve_gittata(r.get("gittata"))
    di, dt = breve_durata(r.get("durata"))
    ti, tt = breve_tempo(r.get("tempo_di_lancio_breve"), r.get("tempo_di_lancio"))
    yc = Y(STATS_Y)
    # sinistra
    x = ox + PAD_X
    w = disegna_icona(c, gi, x, yc, ih, mode)
    c.drawString(x + w + 1.8, yc - fsz * 0.35, gt)
    # centro
    tw = pdfmetrics.stringWidth(dt, "F", fsz)
    iw = ih * 1.1
    xs = ox + CARD_W / 2 + 2 - (iw + 1.8 + tw) / 2
    w = disegna_icona(c, di, xs, yc, ih, mode)
    c.drawString(xs + w + 1.8, yc - fsz * 0.35, dt)
    # destra
    tw = pdfmetrics.stringWidth(tt, "F", fsz)
    xr = ox + CARD_W - PAD_X
    c.drawString(xr - tw, yc - fsz * 0.35, tt)
    disegna_icona(c, ti, xr - tw - 1.8, yc, ih, mode, align="right")

    # testo + diagramma
    tx, tw_ = ox + PAD_X, CARD_W - 2 * PAD_X
    avail = FOOT_SEP_Y - 3 - TEXT_TOP
    if not opts.senza_pagina and riferimento(r):
        avail -= 6.5
    vuole_diag = not opts.senza_diagrammi and (analizza_area(r) or breve_gittata(r.get("gittata"))[0] == "gittata_distanza")
    scelta = None
    modo = opts.testo
    tentativi = []
    if modo in ("auto", "completo"):
        tentativi.append("completo")
    if modo in ("auto", "breve"):
        tentativi.append("breve")
    for mt in tentativi:
        min_fs = 4.4 if mt == "completo" and modo == "auto" else 3.6
        fs = 6.3
        while fs >= min_fs - 1e-6:
            blocchi, usa_breve = blocchi_testo(r, th, fs, mt)
            h = misura(blocchi, tw_, fs)
            if vuole_diag and h + DIAGRAM_H + 2 <= avail:
                scelta = (blocchi, fs, True, usa_breve)
                break
            if h <= avail and (not vuole_diag or fs < 5.4):
                scelta = (blocchi, fs, False, usa_breve)
                break
            fs -= 0.1
        if scelta:
            break
    if not scelta:
        blocchi, usa_breve = blocchi_testo(r, th, 3.6, tentativi[-1])
        scelta = (blocchi, 3.6, False, usa_breve)
        report["troppo_lunghe"].append(r["nome"])
    blocchi, fs, con_diag, usa_breve = scelta
    if usa_breve and (r.get("descrizione_completa") or "").strip():
        report["breve"].append(r["nome"])
    yend = disegna_blocchi(c, blocchi, tx, Y(TEXT_TOP), tw_, fs, th, mode)
    if con_diag:
        disegna_diagramma(c, r, tx, yend - DIAGRAM_H - 1, tw_, DIAGRAM_H, th)
    if not opts.senza_pagina:
        disegna_riferimento(c, r, tx + tw_, Y(FOOT_SEP_Y - 2.2), th)

    # piede: componenti a sinistra, classi a destra
    fy = Y(FOOT_Y)
    fh = 10
    x = ox + PAD_X
    comps = (r.get("componenti") or "").upper()
    for k, nome in (("V", "comp_v"), ("S", "comp_s"), ("M", "comp_m")):
        if k in comps:
            x += disegna_icona(c, nome, x, fy, fh, mode) + 1.8
    if (r.get("rituale") or "").strip().lower().startswith("s"):
        disegna_icona(c, "rituale", x, fy, fh, mode)
    classi = [k.strip().lower() for k in (r.get("classi") or "").split(",") if k.strip()]
    classi = [k for k in ORDINE_CLASSI if k in classi]
    x = ox + CARD_W - PAD_X
    for k in reversed(classi):
        x -= disegna_icona(c, f"classe_{k}", x, fy, fh, mode, align="right") + 1.4

# --------------------------------------------------------------------------
# Pagine
# --------------------------------------------------------------------------
def retro_image(tipo):
    path = os.path.join(ASSETS, "retro.jpg")
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGB")
    if tipo == "light":
        g = ImageOps.grayscale(im)
        g = ImageOps.autocontrast(g, cutoff=1)
        g = ImageOps.invert(g)
        im = ImageOps.colorize(g, black="#c4b8a2", white="#fbf8f2")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    buf.seek(0)
    return ImageReader(buf)


def _mix(a, b, t):
    a, b = HexColor(a), HexColor(b)
    r = [int(255 * (x + (y - x) * t)) for x, y in ((a.red, b.red), (a.green, b.green), (a.blue, b.blue))]
    return "#%02x%02x%02x" % tuple(r)


def tema_classe(base, classe):
    """Variante del tema con il fronte tinto nel colore della classe.
    Le tinte restano leggere (chiaro) o profonde (scuro) per non perdere contrasto:
    testo ed evidenziazioni non cambiano."""
    col = COLORI_CLASSE[classe]
    th = dict(base)
    if base["back"] == "dark":
        th.update(
            page_bg=_mix(col, "#000000", 0.62),
            cut=_mix(col, "#ffffff", 0.25),
            card_fill=_mix(col, "#2c2c2c", 0.80),
            card_border=_mix(col, "#000000", 0.75),
            sep=_mix(col, "#2c2c2c", 0.45),
            ring_fill=_mix(col, "#1c1c1c", 0.80),
            ring_stroke=_mix(col, "#ffffff", 0.45),
            hl_box=_mix(col, "#ffffff", 0.35),
            grid=_mix(col, "#ffffff", 0.75),
        )
    else:
        th.update(
            page_bg="#ffffff",
            cut=_mix(col, "#ffffff", 0.55),
            card_fill=_mix(col, "#ffffff", 0.93),
            card_border=col,
            sep=_mix(col, "#ffffff", 0.60),
            title=_mix(col, "#000000", 0.62),
            ring_fill="#ffffff",
            ring_stroke=col,
            ring_text=_mix(col, "#000000", 0.55),
            hl_box=_mix(col, "#ffffff", 0.35),
            grid=_mix(col, "#000000", 0.30),
        )
    return th


def retro_classe_image(classe, tipo):
    """Motivo del retro colorato con il colore della classe."""
    path = os.path.join(ASSETS, "retro.jpg")
    col = COLORI_CLASSE[classe]
    g = ImageOps.grayscale(Image.open(path).convert("RGB"))
    g = ImageOps.autocontrast(g, cutoff=1)
    if tipo == "light":
        g = ImageOps.invert(g)
        im = ImageOps.colorize(g, black=_mix(col, "#ffffff", 0.45), white=_mix(col, "#ffffff", 0.93))
    else:
        im = ImageOps.colorize(g, black=_mix(col, "#000000", 0.82), white=_mix(col, "#000000", 0.35))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    buf.seek(0)
    return ImageReader(buf)


_EMBLEMI = {}

def emblema_classe(classe, colore):
    """Icona della classe ricolorata in tinta unita (bianca o nel colore dato)."""
    key = (classe, colore)
    if key not in _EMBLEMI:
        im = Image.open(os.path.join(ASSETS, f"classe_{classe}.png")).convert("RGBA")
        a = im.split()[3].point(lambda v: 0 if v < 60 else min(255, int((v - 60) * 1.6)))
        fill = Image.new("RGBA", im.size, colore)
        fill.putalpha(a)
        _EMBLEMI[key] = (ImageReader(fill), im.size)
    return _EMBLEMI[key]


def disegna_retro_classe(c, ox, oy, classe, tipo):
    col = COLORI_CLASSE[classe]
    cx, cy = ox + CARD_W / 2, oy + CARD_H / 2 + 8
    c.saveState()
    # cornice
    c.setStrokeColor(HexColor(_mix(col, "#ffffff", 0.35) if tipo == "dark" else col))
    c.setLineWidth(1.2)
    c.roundRect(ox + 7, oy + 7, CARD_W - 14, CARD_H - 14, 4, stroke=1, fill=0)
    c.setLineWidth(0.4)
    c.roundRect(ox + 10, oy + 10, CARD_W - 20, CARD_H - 20, 3, stroke=1, fill=0)
    # medaglione
    if tipo == "dark":
        c.setFillColor(HexColor(_mix(col, "#000000", 0.6)), alpha=0.92)
        c.setStrokeColor(HexColor(_mix(col, "#ffffff", 0.3)))
        icol, tcol = "#ffffff", "#ffffff"
    else:
        c.setFillColor(HexColor("#fbf8f2"), alpha=0.95)
        c.setStrokeColor(HexColor(col))
        icol, tcol = col, _mix(col, "#000000", 0.35)
    c.setLineWidth(1.6)
    c.circle(cx, cy, 40, stroke=1, fill=1)
    c.setLineWidth(0.5)
    c.circle(cx, cy, 35, stroke=1, fill=0)
    rd, (w0, h0) = emblema_classe(classe, icol)
    h = 44
    w = h * w0 / h0
    c.drawImage(rd, cx - w / 2, cy - h / 2, w, h, mask="auto")
    # nome
    c.setFillColor(HexColor(tcol))
    c.setFont("F-M", 13)
    nome = classe.upper()
    spaced = " ".join(nome)
    c.drawCentredString(cx, cy - 62, spaced)
    c.restoreState()


_LOGO = {}
LOGO_URL = "https://blackislesociety.com/assets/logo.png"


def scarica_logo(dest):
    """Scarica il logo della Black Isle Society la prima volta che serve."""
    import urllib.request
    print(f"Logo non presente, lo scarico da {LOGO_URL} ...")
    try:
        req = urllib.request.Request(LOGO_URL, headers={"User-Agent": "genera-carte/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r, open(dest, "wb") as f:
            f.write(r.read())
        Image.open(dest).verify()
        print(f"  salvato in {dest}")
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        print(f"  download non riuscito ({e})")

def carica_logo(path):
    """Carica il logo; se e' scuro lo rende bianco, cosi' si vede sul nero."""
    if path in _LOGO:
        return _LOGO[path]
    if path and not os.path.exists(path) and os.path.abspath(path) == os.path.abspath(os.path.join(ASSETS, "logo_bis.png")):
        scarica_logo(path)
    if not path or not os.path.exists(path):
        sys.exit(f"Logo non trovato: {path}\n"
                 "Scaricalo da https://blackislesociety.com/assets/logo.png e "
                 "salvalo in assets/logo_bis.png (oppure indica il percorso con --logo).")
    im = Image.open(path).convert("RGBA")
    from PIL import ImageStat
    maschera = im.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    lum = ImageStat.Stat(ImageOps.grayscale(im), mask=maschera).mean[0]
    if lum < 110:   # logo scuro: lo invertiamo in bianco mantenendo la trasparenza
        r, g, b, a = im.split()
        rgb = ImageOps.invert(Image.merge("RGB", (r, g, b)))
        im = Image.merge("RGBA", (*rgb.split(), a))
    if im.getchannel("A").getextrema()[0] == 255:
        # nessuna trasparenza: rendiamo trasparente lo sfondo nero
        g = ImageOps.grayscale(im)
        im.putalpha(g.point(lambda v: 0 if v < 25 else 255))
    _LOGO[path] = (ImageReader(im), im.size)
    return _LOGO[path]


def pagina_retro_bis(c, logo_path, n):
    c.setFillColor(HexColor("#000000"))
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    rd, (w0, h0) = carica_logo(logo_path)
    max_w, max_h = CARD_W * 0.72, CARD_H * 0.55
    sc = min(max_w / w0, max_h / h0)
    w, h = w0 * sc, h0 * sc
    for k in range(n):
        col, row = k % COLS, k // COLS
        col = COLS - 1 - col            # specchiato per il fronte/retro sul lato lungo
        ox = MARGIN_X + col * PITCH_X
        oy = PAGE_H - (MARGIN_Y + row * PITCH_Y) - CARD_H
        c.drawImage(rd, ox + (CARD_W - w) / 2, oy + (CARD_H - h) / 2, w, h, mask="auto")


def pagina_fronte(c, carte, th, opts, report):
    c.setFillColor(HexColor(th["page_bg"]))
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # linee di taglio a metà degli spazi tra le carte
    c.setStrokeColor(HexColor(th["cut"]))
    c.setLineWidth(0.35)
    for i in range(COLS + 1):
        x = MARGIN_X - (PITCH_X - CARD_W) / 2 + i * PITCH_X
        c.line(x, 0, x, PAGE_H)
    for j in range(ROWS + 1):
        y = PAGE_H - (MARGIN_Y - (PITCH_Y - CARD_H) / 2 + j * PITCH_Y)
        c.line(0, y, PAGE_W, y)
    for k, r in enumerate(carte):
        col, row = k % COLS, k // COLS
        ox = MARGIN_X + col * PITCH_X
        oy = PAGE_H - (MARGIN_Y + row * PITCH_Y) - CARD_H
        disegna_carta(c, r, ox, oy, th, opts, report)


def pagina_retro(c, img, classe=None, tipo="dark", n=0):
    if img is not None:
        c.drawImage(img, 0, 0, PAGE_W, PAGE_H)
    if classe:
        # stampa fronte/retro sul lato lungo: le colonne sono speculari
        for k in range(n):
            col, row = k % COLS, k // COLS
            col = COLS - 1 - col
            ox = MARGIN_X + col * PITCH_X
            oy = PAGE_H - (MARGIN_Y + row * PITCH_Y) - CARD_H
            disegna_retro_classe(c, ox, oy, classe, tipo)


def genera(righe, tema, out_path, opts, classe=None):
    th = THEMES[tema]
    if classe and not opts.fronte_standard and not opts.bis:
        th = tema_classe(th, classe)
    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Carte incantesimi ({tema})")
    report = {"breve": [], "troppo_lunghe": []}
    if opts.senza_retro:
        back = None
    elif classe and not opts.retro_standard:
        back = retro_classe_image(classe, th["back"])
    else:
        back = retro_image(th["back"])
    per_pagina = COLS * ROWS
    for i in range(0, len(righe), per_pagina):
        pagina_fronte(c, righe[i:i + per_pagina], th, opts, report)
        c.showPage()
        if not opts.senza_retro and opts.bis:
            pagina_retro_bis(c, opts.logo, len(righe[i:i + per_pagina]))
            c.showPage()
        elif not opts.senza_retro:
            pagina_retro(c, back, None if opts.retro_standard else classe,
                         th["back"], len(righe[i:i + per_pagina]))
            c.showPage()
    c.save()
    return report


# ==========================================================================
# Formato POKER (63 x 88 mm) con cornice grafica di sfondo
# ==========================================================================
MM = 72 / 25.4
PK_W, PK_H = 63 * MM, 88 * MM          # carta
PK_BLEED = 3 * MM                      # abbondanza dell'immagine cornice
PK_GAP = 6 * MM                        # spazio tra le carte sul foglio
PK_PX = PK_W / 744                     # punti per pixel della cornice (300 dpi)
FOGLI = {"A3": (841.89, 1190.55, 4, 4), "A4": (595.28, 841.89, 3, 3)}

# Zone della cornice, in pixel della carta (senza abbondanza), misurate sull'immagine
Z = dict(
    scuola=(95, 56, 193, 157),          # x0, y0, x1, y1
    titolo=(203, 60, 532, 153),
    livello=(597, 108, 52),             # cx, cy, r
    stat=[(98, 204, 274, 245), (291, 204, 453, 245), (470, 204, 647, 245)],
    testo=(101, 281, 644, 851),
    piede_sx=(85, 888, 271, 983),
    piede_dx=(482, 888, 660, 983),
    ovale=(376, 936, 95, 41),           # cx, cy, semiassi
)
# zone della cornice scura e bianco/nero (stessa impaginazione, diversa da quella chiara)
Z_ORNATA = dict(
    scuola=(83, 46, 194, 161),
    titolo=(222, 65, 525, 140),
    livello=(607, 105, 54),
    stat=[(79, 188, 274, 232), (276, 188, 470, 232), (473, 188, 666, 232)],
    testo=(90, 262, 654, 838),
    piede_sx=(65, 871, 253, 994),
    piede_dx=(497, 871, 680, 994),
    ovale=(375, 930, 102, 52),
)
Z_CHIARA = dict(Z)
PK_ZONE = {"scuro": Z_ORNATA, "bn": Z_ORNATA, "chiaro": Z_CHIARA}
PK_TEMI = {"scuro": "cornice_scura.png", "bn": "cornice_bn.png", "chiaro": "cornice_chiara.png"}
# colore con cui si ripulisce l'interno dell'ovale prima di mettere il logo vero
PK_OVALE = {"scuro": "#3b3b3c", "bn": "#ffffff", "chiaro": "#d1cfc5"}
# colore del retro: nero, tranne la versione chiara che usa il fondo del pannello del testo
PK_RETRO = {"scuro": "#000000", "bn": "#000000", "chiaro": "#e7e4db"}


def _pz(c_ox, c_top, x, y):
    """pixel della cornice -> coordinate PDF (y verso il basso nei pixel)."""
    return c_ox + x * PK_PX, c_top - y * PK_PX


_CORNICI = {}

def cornice(tema):
    if tema not in _CORNICI:
        path = os.path.join(ASSETS, PK_TEMI[tema])
        if not os.path.exists(path):
            path = os.path.join(ASSETS, PK_TEMI["scuro"])
        _CORNICI[tema] = ImageReader(path)
    return _CORNICI[tema]


_LOGO_TINTA = {}

def logo_tinto(path, colore):
    key = (path, colore)
    if key not in _LOGO_TINTA:
        im = Image.open(path).convert("RGBA")
        fill = Image.new("RGBA", im.size, colore)
        fill.putalpha(im.getchannel("A"))
        _LOGO_TINTA[key] = (ImageReader(fill), im.size)
    return _LOGO_TINTA[key]


def riempi_zone(c, ox, top, colore):
    """Nelle versioni chiare copre l'interno dei riquadri con un colore piatto."""
    c.saveState()
    c.setFillColor(HexColor(colore))
    ins = 6  # pixel di rientro per non coprire i bordi metallici
    def rr(z, rad=4):
        x0, y0, x1, y1 = z
        X0, Y0 = _pz(ox, top, x0 + ins, y1 - ins)
        X1, Y1 = _pz(ox, top, x1 - ins, y0 + ins)
        c.roundRect(X0, Y0, X1 - X0, Y1 - Y0, rad, stroke=0, fill=1)
    rr(Z["scuola"], 3)
    rr(Z["titolo"], 1)
    for z in Z["stat"]:
        rr(z, 1)
    rr(Z["testo"], 9)
    rr(Z["piede_sx"], 1)
    rr(Z["piede_dx"], 1)
    cx, cy, r = Z["livello"]
    X, Y = _pz(ox, top, cx, cy)
    c.circle(X, Y, (r - 5) * PK_PX, stroke=0, fill=1)
    cx, cy, a, b = Z["ovale"]
    X, Y = _pz(ox, top, cx, cy)
    c.ellipse(X - (a - 5) * PK_PX, Y - (b - 5) * PK_PX, X + (a - 5) * PK_PX, Y + (b - 5) * PK_PX, stroke=0, fill=1)
    c.restoreState()


def testo_in_box(c, txt, font, size, x0, x1, yc, colore, min_size=5):
    w = x1 - x0
    while pdfmetrics.stringWidth(txt, font, size) > w and size > min_size:
        size -= 0.2
    c.setFont(font, size)
    c.setFillColor(HexColor(colore))
    c.drawCentredString((x0 + x1) / 2, yc - size * 0.35, txt)


def disegna_carta_poker(c, r, ox, oy, tema, th, opts, report):
    global Z
    Z = PK_ZONE[tema]
    mode = th["icon_mode"]
    top = oy + PK_H
    # sfondo: cornice con abbondanza
    c.drawImage(cornice(tema), ox - PK_BLEED, oy - PK_BLEED, PK_W + 2 * PK_BLEED, PK_H + 2 * PK_BLEED)
    if opts.logo and os.path.exists(opts.logo):
        # copre il logo disegnato nella cornice: al suo posto va il file originale
        cx, cy, a, b = Z["ovale"]
        X, Y = _pz(ox, top, cx, cy)
        c.saveState()
        c.setFillColor(HexColor(PK_OVALE[tema]))
        c.ellipse(X - (a - 4) * PK_PX, Y - (b + 1) * PK_PX, X + (a - 4) * PK_PX, Y + (b + 0.5) * PK_PX, stroke=0, fill=1)
        c.restoreState()

    # scuola
    x0, y0, x1, y1 = Z["scuola"]
    X, Y = _pz(ox, top, (x0 + x1) / 2, (y0 + y1) / 2)
    disegna_icona(c, f"scuola_{(r.get('scuola') or '').strip().lower()}", X, Y, 19, mode, align="center")
    # titolo
    x0, y0, x1, y1 = Z["titolo"]
    X0, Yc = _pz(ox, top, x0 + 10, (y0 + y1) / 2)
    X1, _ = _pz(ox, top, x1 - 8, 0)
    disegna_titolo_box(c, r["nome"], X0, X1, Yc, th)
    # livello
    cx, cy, rad = Z["livello"]
    X, Y = _pz(ox, top, cx, cy)
    txt = ROMANI[int(r["livello"])]
    size = 10.5 if len(txt) <= 2 else (8.5 if len(txt) == 3 else 7.5)
    c.setFillColor(HexColor(th["ring_text"]))
    c.setFont("F-M", size)
    c.drawCentredString(X, Y - size * 0.36, txt)

    # statistiche: una per scomparto
    gi, gt = breve_gittata(r.get("gittata"))
    di, dt = breve_durata(r.get("durata"))
    ti, tt = breve_tempo(r.get("tempo_di_lancio_breve"), r.get("tempo_di_lancio"))
    for (icn, txt), z in zip(((gi, gt), (di, dt), (ti, tt)), Z["stat"]):
        x0, y0, x1, y1 = z
        X0, Yc = _pz(ox, top, x0 + 8, (y0 + y1) / 2)
        X1, _ = _pz(ox, top, x1 - 8, 0)
        ih, size = 8, 7
        avail = X1 - X0 - ih - 2
        while pdfmetrics.stringWidth(txt, "F", size) > avail and size > 4.8:
            size -= 0.2
        tw = pdfmetrics.stringWidth(txt, "F", size)
        ic = icona(icn, mode)
        iw = ih * ic[1][0] / ic[1][1] if ic else 0
        start = (X0 + X1) / 2 - (iw + 1.6 + tw) / 2
        disegna_icona(c, icn, start, Yc, ih, mode)
        c.setFillColor(HexColor(th["stat_text"]))
        c.setFont("F", size)
        c.drawString(start + iw + 1.6, Yc - size * 0.35, txt)

    # testo
    x0, y0, x1, y1 = Z["testo"]
    TX0, TY0 = _pz(ox, top, x0 + 24, y0 + 16)
    TX1, TY1 = _pz(ox, top, x1 - 24, y1 - 14)
    rif_y = TY1
    if not opts.senza_pagina and riferimento(r):
        TY1 += 4.0                      # spazio riservato al numero di pagina
    tw_, avail = TX1 - TX0, TY0 - TY1
    vuole_diag = not opts.senza_diagrammi and (analizza_area(r) or breve_gittata(r.get("gittata"))[0] == "gittata_distanza")
    DH = 28
    scelta = None
    tentativi = (["completo"] if opts.testo in ("auto", "completo") else []) + (["breve"] if opts.testo in ("auto", "breve") else [])
    for mt in tentativi:
        min_fs = 4.2 if mt == "completo" and opts.testo == "auto" else 3.4
        fs = 6.0
        while fs >= min_fs - 1e-6:
            bl, ub = blocchi_testo(r, th, fs, mt)
            h = misura(bl, tw_, fs)
            if vuole_diag and h + DH + 2 <= avail:
                scelta = (bl, fs, True, ub); break
            if h <= avail and (not vuole_diag or fs < 5.2):
                scelta = (bl, fs, False, ub); break
            fs -= 0.1
        if scelta:
            break
    if not scelta:
        bl, ub = blocchi_testo(r, th, 3.4, tentativi[-1])
        scelta = (bl, 3.4, False, ub)
        report["troppo_lunghe"].append(r["nome"])
    bl, fs, con_diag, ub = scelta
    if ub and (r.get("descrizione_completa") or "").strip():
        report["breve"].append(r["nome"])
    yend = disegna_blocchi(c, bl, TX0, TY0, tw_, fs, th, mode)
    if con_diag:
        disegna_diagramma(c, r, TX0, max(TY1, yend - DH - 1), tw_, DH, th)
    if not opts.senza_pagina:
        disegna_riferimento(c, r, TX1 - 11, rif_y - 1.0, th)

    # piede sinistro: componenti + rituale
    x0, y0, x1, y1 = Z["piede_sx"]
    X0, Yc = _pz(ox, top, x0 + 12, (y0 + y1) / 2)
    comps = (r.get("componenti") or "").upper()
    x = X0
    for k, nome in (("V", "comp_v"), ("S", "comp_s"), ("M", "comp_m")):
        if k in comps:
            x += disegna_icona(c, nome, x, Yc, 9, mode) + 1.6
    if (r.get("rituale") or "").strip().lower().startswith("s"):
        disegna_icona(c, "rituale", x, Yc, 9, mode)
    # piede destro: classi (rimpicciolite se sono tante)
    x0, y0, x1, y1 = Z["piede_dx"]
    X0, Yc = _pz(ox, top, x0 + 10, (y0 + y1) / 2)
    X1, _ = _pz(ox, top, x1 - 12, 0)
    classi = [k.strip().lower() for k in (r.get("classi") or "").split(",") if k.strip()]
    classi = [k for k in ORDINE_CLASSI if k in classi]
    if classi:
        h = min(9.0, (X1 - X0) / (len(classi) * 1.12))
        x = X1
        for k in reversed(classi):
            x -= disegna_icona(c, f"classe_{k}", x, Yc, h, mode, align="right") + h * 0.12
    # logo nel cartiglio ovale
    if opts.logo and os.path.exists(opts.logo):
        cx, cy, a, b = Z["ovale"]
        X, Y = _pz(ox, top, cx, cy)
        col = {"scuro": "#ffffff", "bn": "#000000", "chiaro": "#2f2f2f"}[tema]
        rd, (w0, h0) = logo_tinto(opts.logo, col)
        bw, bh = 2 * a * 0.80 * PK_PX, 2 * b * 0.80 * PK_PX   # quasi tutto l'ovale
        sc = min(bw / w0, bh / h0)
        c.drawImage(rd, X - w0 * sc / 2, Y - h0 * sc / 2, w0 * sc, h0 * sc, mask="auto")


def riferimento(r):
    """Testo del rimando alla fonte, stampato in fondo al riquadro della descrizione."""
    p = (r.get("pagina_srd") or "").strip()
    if p:
        return f"SRD 5.2.1 · p. {p}"
    pm = (r.get("pagina_manuale") or "").strip()
    if pm:
        return f"Manuale del Giocatore · p. {pm}"
    if "manuale" in (r.get("fonte") or "").lower():
        return "Manuale del Giocatore"
    return ""


def disegna_riferimento(c, r, x_right, y, th, size=4.6):
    txt = riferimento(r)
    if not txt:
        return
    c.saveState()
    c.setFont("F-I", size)
    c.setFillColor(HexColor(th["diag_label"]))
    c.drawRightString(x_right, y, txt)
    c.restoreState()


def disegna_titolo_box(c, nome, x0, x1, yc, th):
    w = x1 - x0
    c.setFillColor(HexColor(th["title"]))
    for size in (11, 10.5, 10, 9.5):
        if pdfmetrics.stringWidth(nome, "F-M", size) <= w:
            c.setFont("F-M", size)
            c.drawCentredString((x0 + x1) / 2, yc - size * 0.35, nome)
            return
    parole = nome.split()
    for size in (8.6, 8.2, 7.8, 7.4, 7, 6.6, 6.2):
        righe, cur = [], ""
        for p in parole:
            t = (cur + " " + p).strip()
            if pdfmetrics.stringWidth(t, "F-M", size) <= w or not cur:
                cur = t
            else:
                righe.append(cur); cur = p
        righe.append(cur)
        if len(righe) <= 2 and all(pdfmetrics.stringWidth(x, "F-M", size) <= w for x in righe):
            c.setFont("F-M", size)
            lead = size * 1.0
            t0 = yc + (len(righe) - 1) * lead / 2 - size * 0.35
            for i, x in enumerate(righe):
                c.drawCentredString((x0 + x1) / 2, t0 - i * lead, x)
            return
    c.setFont("F-M", 6)
    c.drawCentredString((x0 + x1) / 2, yc - 2, nome[:30])


# formato "a libro": fronte + retro affiancati sullo stesso lato del foglio, da piegare
FOGLI_PIEGA = {"A3": (1190.55, 841.89, 3, 3), "A4": (841.89, 595.28, 2, 2)}   # orizzontali
PIEGA_RETRO = {"scuro": ("#000000", "#ffffff"), "chiaro": ("#e7e4db", "#2f2f2f"),
               "bn": ("#000000", "#ffffff")}   # (fondo, logo)


def disegna_retro_piega(c, ox, oy, tema, opts):
    """Pannello retro a destra della carta (ox = linea di piega)."""
    fondo, col_logo = PIEGA_RETRO[tema]
    if opts.nero_k and fondo == "#000000":
        c.setFillColorCMYK(0, 0, 0, 1)
    else:
        c.setFillColor(HexColor(fondo))
    c.rect(ox, oy - PK_BLEED, PK_W + PK_BLEED, PK_H + 2 * PK_BLEED, stroke=0, fill=1)
    if opts.logo and os.path.exists(opts.logo):
        rd, (w0, h0) = logo_tinto(opts.logo, col_logo)
        sc = min(PK_W * 0.72 / w0, PK_H * 0.5 / h0)
        w, h = w0 * sc, h0 * sc
        c.drawImage(rd, ox + (PK_W - w) / 2, oy + (PK_H - h) / 2, w, h, mask="auto")


def genera_poker_piega(righe, tema, out_path, opts, th):
    pw, ph, cols, rows = FOGLI_PIEGA[opts.foglio]
    cw = 2 * PK_W                                   # coppia fronte + retro
    gw = cols * cw + (cols - 1) * PK_GAP
    gh = rows * PK_H + (rows - 1) * PK_GAP
    mx, my = (pw - gw) / 2, (ph - gh) / 2
    c = canvas.Canvas(out_path, pagesize=(pw, ph))
    c.setTitle(f"Carte incantesimi poker da piegare ({tema})")
    report = {"breve": [], "troppo_lunghe": []}
    per = cols * rows
    for i in range(0, len(righe), per):
        for k, r in enumerate(righe[i:i + per]):
            col, row = k % cols, k // cols
            ox = mx + col * (cw + PK_GAP)
            oy = ph - my - (row + 1) * PK_H - row * PK_GAP
            # fronte, tagliato sulla linea di piega (l'abbondanza resta solo sui lati esterni)
            c.saveState()
            p = c.beginPath()
            p.rect(ox - PK_BLEED, oy - PK_BLEED, PK_W + PK_BLEED, PK_H + 2 * PK_BLEED)
            c.clipPath(p, stroke=0, fill=0)
            disegna_carta_poker(c, r, ox, oy, tema, th, opts, report)
            c.restoreState()
            disegna_retro_piega(c, ox + PK_W, oy, tema, opts)
        # segni di taglio (bordi esterni) e di piega (tratteggiati) sui margini
        c.setLineWidth(0.3)
        for col in range(cols):
            x0 = mx + col * (cw + PK_GAP)
            for xx, piega in ((x0, False), (x0 + PK_W, True), (x0 + cw, False)):
                c.setStrokeColor(HexColor("#888888" if piega else "#000000"))
                if piega:
                    c.setDash(2, 1.5)
                c.line(xx, ph - my + 3, xx, ph - 2)
                c.line(xx, my - 3, xx, 2)
                c.setDash()
        c.setStrokeColor(HexColor("#000000"))
        for row in range(rows):
            for yy in (ph - my - row * (PK_H + PK_GAP), ph - my - row * (PK_H + PK_GAP) - PK_H):
                c.line(2, yy, mx - 3, yy)
                c.line(pw - mx + 3, yy, pw - 2, yy)
        c.showPage()
    c.save()
    return report


def genera_poker(righe, tema, out_path, opts):
    th = dict(THEMES["scuro" if tema == "scuro" else tema])
    if tema == "scuro":
        th.update(ring_text="#e8e8e8", text="#f0f0f0")
    if tema == "chiaro":
        th.update(text="#262626", title="#262626", stat_text="#262626", ring_text="#262626")
    if opts.piega:
        return genera_poker_piega(righe, tema, out_path, opts, th)
    pw, ph, cols, rows = FOGLI[opts.foglio]
    gw = cols * PK_W + (cols - 1) * PK_GAP
    gh = rows * PK_H + (rows - 1) * PK_GAP
    mx, my = (pw - gw) / 2, (ph - gh) / 2
    c = canvas.Canvas(out_path, pagesize=(pw, ph))
    c.setTitle(f"Carte incantesimi poker ({tema})")
    report = {"breve": [], "troppo_lunghe": []}
    per = cols * rows

    def pos(k, mirror=False):
        col, row = k % cols, k // cols
        if mirror:
            col = cols - 1 - col
        return mx + col * (PK_W + PK_GAP), ph - my - (row + 1) * PK_H - row * PK_GAP

    for i in range(0, len(righe), per):
        blocco = righe[i:i + per]
        for k, r in enumerate(blocco):
            ox, oy = pos(k)
            disegna_carta_poker(c, r, ox, oy, tema, th, opts, report)
        # segni di taglio sui margini del foglio
        c.setStrokeColor(HexColor("#000000" if tema != "scuro" else "#888888"))
        c.setLineWidth(0.3)
        for col in range(cols):
            for xx in (mx + col * (PK_W + PK_GAP), mx + col * (PK_W + PK_GAP) + PK_W):
                c.line(xx, ph - my + 3, xx, ph - 2)
                c.line(xx, my - 3, xx, 2)
        for row in range(rows):
            for yy in (ph - my - row * (PK_H + PK_GAP), ph - my - row * (PK_H + PK_GAP) - PK_H):
                c.line(2, yy, mx - 3, yy)
                c.line(pw - mx + 3, yy, pw - 2, yy)
        c.showPage()
        if not opts.senza_retro:
            if opts.nero_k and PK_RETRO[tema] == "#000000":
                c.setFillColorCMYK(0, 0, 0, 1)     # nero solo inchiostro K (100% K)
            else:
                c.setFillColor(HexColor(PK_RETRO[tema]))
            c.rect(0, 0, pw, ph, stroke=0, fill=1)
            c.showPage()
    c.save()
    return report


def leggi_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        righe = [r for r in rd]
    obblig = {"nome", "livello", "scuola", "classi", "gittata", "durata",
              "componenti", "descrizione_breve"}
    manca = obblig - set(righe[0].keys()) if righe else obblig
    if manca:
        sys.exit(f"Nel CSV mancano le colonne: {', '.join(sorted(manca))}")
    return righe


def main():
    ap = argparse.ArgumentParser(description="Genera le carte incantesimo A3 dal CSV.")
    ap.add_argument("csv")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--testo", choices=["auto", "completo", "breve"], default="auto")
    ap.add_argument("--solo", choices=["scuro", "chiaro"])
    ap.add_argument("--senza-retro", action="store_true")
    ap.add_argument("--senza-diagrammi", action="store_true")
    ap.add_argument("--senza-pagina", action="store_true",
                    help="non stampa il rimando alla pagina dell'SRD")
    ap.add_argument("--classe", help="es. mago, chierico, warlock...")
    ap.add_argument("--per-classe", action="store_true",
                    help="crea anche una cartella per classe con i PDF di quella classe")
    ap.add_argument("--retro-standard", action="store_true",
                    help="con --per-classe usa il retro normale invece di quello della classe")
    ap.add_argument("--fronte-standard", action="store_true",
                    help="con --per-classe lascia il fronte nei colori standard")
    ap.add_argument("--bis", action="store_true",
                    help="edizione Black Isle Society: fronte bianco e nero + chiaro, retro nero con logo")
    ap.add_argument("--logo", default=os.path.join(ASSETS, "logo_bis.png"),
                    help="percorso del logo per il retro dell'edizione --bis")
    ap.add_argument("--solo-bn", action="store_true", help="con --poker genera solo la versione bianco e nero")
    ap.add_argument("--poker", action="store_true",
                    help="carte formato poker 63x88 mm con la cornice grafica e retro nero")
    ap.add_argument("--nero-k", action="store_true",
                    help="retro nero in CMYK 0/0/0/100 (solo inchiostro nero) invece di RGB 0/0/0")
    ap.add_argument("--piega", action="store_true",
                    help="con --poker: fronte e retro affiancati sullo stesso lato, da piegare (A3/A4 orizzontale)")
    ap.add_argument("--foglio", choices=["A3", "A4"], default="A3",
                    help="foglio per il formato poker: A3 = 16 carte, A4 = 9 carte")
    ap.add_argument("--solo-classi", action="store_true",
                    help="come --per-classe, ma senza i PDF con tutte le carte")
    opts = ap.parse_args()

    registra_font()
    righe = leggi_csv(opts.csv)
    if opts.classe:
        k = opts.classe.strip().lower()
        righe = [r for r in righe if k in (r.get("classi") or "").lower()]
    righe.sort(key=lambda r: (int(r["livello"]), r["nome"].lower()))
    if opts.poker:
        temi = [opts.solo] if opts.solo in ("scuro", "chiaro") else ["scuro", "bn", "chiaro"]
        if opts.solo_bn:
            temi = ["bn"]
        poker_set(righe, opts.out_dir, temi, opts, verbose=True, solo_classi=opts.solo_classi)
        if opts.per_classe or opts.solo_classi:
            print("\nPDF per classe:")
            for k in ORDINE_CLASSI:
                sub = [r for r in righe
                       if k in [c.strip().lower() for c in (r.get("classi") or "").split(",")]]
                if sub:
                    cart = os.path.join(opts.out_dir, k.capitalize())
                    poker_set(sub, cart, temi, opts, verbose=False, classe=k)
                    print(f"  {k.capitalize():<9} {len(sub):>3} carte  ->  {cart}")
        return
    if opts.bis:
        temi = ["bn", "chiaro"] if not opts.solo else [{"scuro": "bn", "chiaro": "chiaro"}[opts.solo]]
    else:
        temi = [opts.solo] if opts.solo else ["scuro", "chiaro"]
    if not opts.solo_classi:
        genera_set(righe, opts.out_dir, temi, opts, verbose=True)

    if opts.per_classe or opts.solo_classi:
        print("\nPDF per classe:")
        for k in ORDINE_CLASSI:
            sub = [r for r in righe
                   if k in [c.strip().lower() for c in (r.get("classi") or "").split(",")]]
            if not sub:
                continue
            cartella = os.path.join(opts.out_dir, k.capitalize())
            genera_set(sub, cartella, temi, opts, verbose=False,
                       classe=k)
            print(f"  {k.capitalize():<9} {len(sub):>3} carte  ->  {cartella}")


def poker_set(righe, cartella, temi, opts, verbose, solo_classi=False, classe=None):
    if solo_classi:
        return
    os.makedirs(cartella, exist_ok=True)
    classe = (classe or opts.classe or "tutte").strip().lower()
    data = datetime.date.today().strftime("%d_%m_%Y")
    for t in temi:
        nome = {"scuro": "scura", "chiaro": "chiara", "bn": "bianco_e_nero"}[t]
        out = os.path.join(cartella, f"BIS_{classe}_{nome}_{opts.foglio}_{data}.pdf")
        rep = genera_poker(righe, t, out, opts)
        if verbose:
            print(f"Creato {out}  ({len(righe)} carte)")
            if rep["breve"] and t == temi[0]:
                print(f"  {len(rep['breve'])} carte usano la descrizione breve.")


def genera_set(righe, cartella, temi, opts, verbose, classe=None):
    os.makedirs(cartella, exist_ok=True)
    for t in temi:
        nome = {"scuro": "scure", "chiaro": "chiare", "bn": "bianco_nero"}[t]
        pref = "carte_bis_" if opts.bis else "carte_"
        out = os.path.join(cartella, f"{pref}{nome}_A3.pdf")
        rep = genera(righe, t, out, opts, classe=classe)
        if not verbose:
            continue
        print(f"Creato {out}  ({len(righe)} carte)")
        if rep["breve"] and t == temi[0]:
            print(f"  {len(rep['breve'])} carte usano la descrizione breve perché il testo completo "
                  f"non entrava:\n   - " + "\n   - ".join(rep["breve"]))
        if rep["troppo_lunghe"] and t == temi[0]:
            print("  Attenzione, testo molto piccolo su: " + ", ".join(rep["troppo_lunghe"]))

if __name__ == "__main__":
    main()
