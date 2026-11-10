#!/usr/bin/env python3
"""
Ellisse da Excel: ogni riga del foglio (risposte al modulo) diventa un punto nell'ellisse.

Colonne attese (in quest'ordine, la prima è il timestamp):
  1) valore asse X (0-10)   "...impatto sull'ambiente a te più ..."
  2) valore asse Y (0-10)   "...impatto sull'ambiente a te vicino"
  3) classe (1-5)
  4) sezione (lettera)
  5) genere ("Come ti identifichi?")

Passi per ogni riga:
  1. normalizzazione 0..10 -> intervallo centrato: X in [-5, 5], Y in [-3, 3]
  2. jitter casuale uniforme in [valore-0.5, valore+0.5] (poi limitato al rettangolo)
  3. mappatura rettangolo -> ellisse (stessa funzione `trasforma` di Index.html)
  4. punto disegnato con colore in base al genere

Uso:
  python ellisse_excel.py "Percezione Livi.xlsx"
  python ellisse_excel.py dati.xlsx -o grafico.png --seed 42 --etichette
"""
import argparse
import math

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.colors import LinearSegmentedColormap

A, B = 5.0, 3.0      # semiassi dell'ellisse (come in Index.html)
VMIN, VMAX = 0, 10   # scala delle risposte
JITTER = 0.5

# etichette agli estremi degli assi (X: valore basso a sinistra; Y: valore basso in basso)
LABEL_SINISTRA, LABEL_DESTRA = "Prossima", "Lontana"
LABEL_SOTTO, LABEL_SOPRA = "Negativo", "Positivo"

# colori per genere (le etichette non previste ricevono un colore dalla tavolozza di riserva)
# colori chiari e accesi, con bordo scuro: si leggono sia sul rosso/verde scuro sia sul centro chiaro
# (l'ordine qui è anche l'ordine in legenda)
COLORI_GENERE = {
    "Ragazza": "#ffd60a",   # giallo
    "Ragazzo": "#00d4ff",   # azzurro
    "Altro": "#ffffff",     # bianco
}
BORDO_PUNTI = "#111111"
RISERVA = ["#ff9f1c", "#c77dff", "#80ffdb", "#ff70a6", "#bcbd22"]

# raggruppamento delle risposte per il grafico (il valore nell'Excel resta quello originale)
GRUPPI = {
    "Non binario": "Altro",
    "Preferisco non rispondere": "Altro",
}

# colori delle etichette agli estremi
COLORE_SINISTRA, COLORE_DESTRA = "#c2008a", "#1d4ed8"   # Prossima magenta, Lontana blu
COLORE_SOTTO, COLORE_SOPRA = "#c1121f", "#15803d"       # Negativo rosso, Positivo verde
FONT_ETICHETTE = 15

# sfondo dell'ellisse: dal basso (rosso scuro) al centro (chiaro) all'alto (verde intenso)
GRADIENTE = ["#4a0000", "#b2182b", "#f4a582", "#f7f7f7", "#a6dba0", "#1b9e3a", "#00441b"]
ALPHA_SFONDO = 0.7


def normalizza(v, semiasse):
    """0..10 -> [-semiasse, +semiasse]"""
    return (v - (VMIN + VMAX) / 2) / ((VMAX - VMIN) / 2) * semiasse


def trasforma(x, y):
    """Mappatura rettangolo [-A,A]x[-B,B] -> ellisse (identica a Index.html)."""
    u, v = x / A, y / B
    return A * u * np.sqrt(1 - v * v / 2), B * v * np.sqrt(1 - u * u / 2)


def leggi(path, foglio=0):
    df = pd.read_excel(path, sheet_name=foglio)
    cols = list(df.columns)
    out = pd.DataFrame({
        "x_raw": pd.to_numeric(df[cols[1]], errors="coerce"),
        "y_raw": pd.to_numeric(df[cols[2]], errors="coerce"),
        "classe": df[cols[3]],
        "sezione": df[cols[4]].astype(str).str.strip().str.upper(),
        "genere": df[cols[5]].astype(str).str.strip(),
    })
    return out.dropna(subset=["x_raw", "y_raw"]).reset_index(drop=True), cols


def calcola(df, seed=None):
    rng = np.random.default_rng(seed)
    n = len(df)
    xn = normalizza(df["x_raw"].clip(VMIN, VMAX).to_numpy(float), A)
    yn = normalizza(df["y_raw"].clip(VMIN, VMAX).to_numpy(float), B)
    xj = np.clip(xn + rng.uniform(-JITTER, JITTER, n), -A, A)
    yj = np.clip(yn + rng.uniform(-JITTER, JITTER, n), -B, B)
    xe, ye = trasforma(xj, yj)
    df = df.copy()
    df["x_norm"], df["y_norm"] = xn, yn
    df["x_jitter"], df["y_jitter"] = xj, yj
    df["x_ellisse"], df["y_ellisse"] = xe, ye
    return df


def colori_per(generi):
    mappa, k = {}, 0
    for g in generi:
        if g in COLORI_GENERE:
            mappa[g] = COLORI_GENERE[g]
        else:
            mappa[g] = RISERVA[k % len(RISERVA)]
            k += 1
    return mappa


def disegna(df, out_png, titolo, etichette=False, dpi=200):
    """Disegna e salva su file (out_png può essere un percorso o un buffer BytesIO)."""
    fig = figura(df, titolo, etichette)
    fig.savefig(out_png, dpi=dpi, format="png")
    plt.close(fig)


def figura(df, titolo, etichette=False):
    """Restituisce la figura matplotlib dell'ellisse con i punti di df."""
    fig, ax = plt.subplots(figsize=(10, 8))
    XR, YR = 5.5, 3.5

    for i in range(-5, 6):
        ax.axvline(i, color="#dde2e8", lw=0.8, ls=(0, (2, 3)), zorder=0)
    for i in range(-3, 4):
        ax.axhline(i, color="#dde2e8", lw=0.8, ls=(0, (2, 3)), zorder=0)
    # gradiente verticale ritagliato sulla forma dell'ellisse
    cmap = LinearSegmentedColormap.from_list("neg_pos", GRADIENTE)
    grad = np.linspace(-1, 1, 512).reshape(-1, 1)
    img = ax.imshow(grad, extent=(-A, A, -B, B), origin="lower", cmap=cmap,
                    vmin=-1, vmax=1, aspect="auto", alpha=ALPHA_SFONDO, zorder=1)
    bordo = Ellipse((0, 0), 2 * A, 2 * B, facecolor="none", edgecolor="#1f2933", lw=2, zorder=2)
    ax.add_patch(bordo)
    img.set_clip_path(bordo)
    ax.axhline(0, color="#1f2933", lw=1, zorder=2)
    ax.axvline(0, color="#1f2933", lw=1, zorder=2)

    # con molti punti: marker più piccoli e trasparenti
    n = len(df)
    size, alpha, lw = (110, 1.0, 1.4) if n <= 50 else (34, 0.95, 0.7)
    gruppo = df["genere"].map(lambda g: GRUPPI.get(g, g))
    presenti = list(gruppo.unique())
    ordine = [g for g in COLORI_GENERE if g in presenti] + sorted(g for g in presenti if g not in COLORI_GENERE)
    mappa = colori_per(ordine)
    for g in ordine:
        sub = df[gruppo == g]
        ax.scatter(sub["x_ellisse"], sub["y_ellisse"], s=size, c=mappa[g],
                   edgecolors=BORDO_PUNTI, linewidths=lw, alpha=alpha, zorder=3,
                   label=f"{g} ({len(sub)})")

    # etichette agli estremi opposti degli assi
    stile = dict(fontsize=FONT_ETICHETTE, fontweight="bold", zorder=5,
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#d9dee5", alpha=0.92))
    ax.text(-A - 0.1, 0.15, LABEL_SINISTRA, ha="right", va="bottom", color=COLORE_SINISTRA, **stile)
    ax.text(A + 0.1, 0.15, LABEL_DESTRA, ha="left", va="bottom", color=COLORE_DESTRA, **stile)
    ax.text(0.12, B + 0.1, LABEL_SOPRA, ha="left", va="bottom", color=COLORE_SOPRA, **stile)
    ax.text(0.12, -B - 0.1, LABEL_SOTTO, ha="left", va="top", color=COLORE_SOTTO, **stile)
    if etichette:
        for _, r in df.iterrows():
            ax.annotate(f"{r['classe']}{r['sezione']}", (r["x_ellisse"], r["y_ellisse"]),
                        xytext=(6, 6), textcoords="offset points", fontsize=8,
                        color="#5f6b78", zorder=4)

    ax.set_xlim(-XR - 1.4, XR + 1.4); ax.set_ylim(-YR - 0.4, YR + 0.4); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])   # niente tacche né numeri sui bordi
    for s in ax.spines.values():
        s.set_color("#d9dee5")
    ax.set_title(titolo, loc="left", fontsize=13, fontweight="bold")
    leg = ax.legend(title="Genere", loc="upper center", bbox_to_anchor=(0.5, -0.03),
                    ncol=4, frameon=False, markerscale=1.6 if n > 50 else 1,
                    columnspacing=2.0, handletextpad=0.4)
    leg.get_title().set_fontweight("bold")
    fig.tight_layout()
    return fig


def main():
    p = argparse.ArgumentParser(description="Punti dell'Excel nell'ellisse, colorati per genere")
    p.add_argument("excel")
    p.add_argument("-o", "--output", default="ellisse_punti.png")
    p.add_argument("--csv", default="ellisse_punti.csv", help="coordinate calcolate")
    p.add_argument("--seed", type=int, default=None, help="seme per jitter riproducibile")
    p.add_argument("--foglio", default=0)
    p.add_argument("--etichette", action="store_true", help="scrive classe+sezione accanto ai punti")
    a = p.parse_args()

    df, cols = leggi(a.excel, a.foglio)
    df = calcola(df, a.seed)
    df.to_csv(a.csv, index=False)
    disegna(df, a.output, f"Percezione dell'impatto della crisi climatica — {len(df)} risposte",
            etichette=a.etichette)

    q = (df["x_ellisse"] / A) ** 2 + (df["y_ellisse"] / B) ** 2
    print(f"{len(df)} punti -> {a.output}  (coordinate in {a.csv})")
    print(f"tutti dentro l'ellisse: {bool((q <= 1 + 1e-9).all())}")


if __name__ == "__main__":
    main()
