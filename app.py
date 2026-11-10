"""
Web app Streamlit: carica l'Excel delle risposte e genera i grafici a ellisse
  - complessivo
  - per anno (1-5)
  - per singola classe (anno + sezione)

Avvio:  streamlit run app.py
"""
import io
import zipfile

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import ellisse_excel as ee

TITOLO = "Percezione dell'impatto della crisi climatica"

st.set_page_config(page_title="Ellisse percezione", page_icon="🟢", layout="wide")
st.title("Ellisse della percezione")
st.caption("Carica l'Excel delle risposte al modulo: ogni riga è uno studente, un punto nell'ellisse.")

# ---------------------------------------------------------------- impostazioni
with st.sidebar:
    st.header("Impostazioni")
    file = st.file_uploader("File Excel (.xlsx)", type=["xlsx", "xls"])
    seed = st.number_input("Seme casuale (jitter)", min_value=0, value=1, step=1,
                           help="Stesso seme = stessa disposizione dei punti")
    etichette = st.checkbox("Mostra classe+sezione accanto ai punti", value=False)
    colonne_griglia = st.select_slider("Grafici per riga", options=[1, 2, 3], value=2)

if file is None:
    st.info("Carica un file Excel dalla barra laterale per iniziare.")
    st.markdown(
        "**Colonne attese, in quest'ordine:** data/ora · valore asse X (0-10) · "
        "valore asse Y (0-10) · classe (1-5) · sezione · genere."
    )
    st.stop()


# ---------------------------------------------------------------- dati
@st.cache_data(show_spinner=False)
def prepara(contenuto: bytes, seed: int):
    df, _ = ee.leggi(io.BytesIO(contenuto))
    df["classe"] = pd.to_numeric(df["classe"], errors="coerce").astype("Int64")
    df = ee.calcola(df, seed)          # jitter calcolato una sola volta: stessi punti in tutte le viste
    df["classe_sez"] = df["classe"].astype(str) + df["sezione"]
    return df


@st.cache_data(show_spinner=False)
def png(df: pd.DataFrame, titolo: str, etichette: bool, dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    ee.disegna(df, buf, titolo, etichette=etichette, dpi=dpi)
    return buf.getvalue()


try:
    df = prepara(file.getvalue(), int(seed))
except Exception as e:
    st.error(f"Non riesco a leggere il file: {e}")
    st.stop()

if df.empty:
    st.warning("Nessuna riga valida nel file.")
    st.stop()

anni = sorted(df["classe"].dropna().unique().tolist())
classi = (df.dropna(subset=["classe"])
            .groupby(["classe", "sezione"]).size()
            .reset_index(name="n").sort_values(["classe", "sezione"]))

c1, c2, c3 = st.columns(3)
c1.metric("Risposte", len(df))
c2.metric("Anni", len(anni))
c3.metric("Classi", len(classi))


def griglia(elementi):
    """elementi: lista di (nome_file, titolo, sotto-df). Mostra i grafici in griglia."""
    for i in range(0, len(elementi), colonne_griglia):
        cols = st.columns(colonne_griglia)
        for col, (nome, titolo, sub) in zip(cols, elementi[i:i + colonne_griglia]):
            dati = png(sub, titolo, etichette)
            col.image(dati, use_container_width=True)
            col.download_button("Scarica PNG", dati, file_name=nome, mime="image/png",
                                key=f"dl_{nome}")


def elementi_anno():
    return [(f"anno_{a}.png", f"{TITOLO} — Anno {a} · {int((df['classe'] == a).sum())} risposte",
             df[df["classe"] == a]) for a in anni]


def elementi_classi(anno=None):
    righe = classi if anno is None else classi[classi["classe"] == anno]
    out = []
    for _, r in righe.iterrows():
        sub = df[(df["classe"] == r["classe"]) & (df["sezione"] == r["sezione"])]
        out.append((f"classe_{r['classe']}{r['sezione']}.png",
                    f"Classe {r['classe']}{r['sezione']} · {len(sub)} risposte", sub))
    return out


# ---------------------------------------------------------------- viste
tab_tot, tab_anno, tab_classe, tab_dati = st.tabs(["Complessivo", "Per anno", "Per classe", "Dati"])

with tab_tot:
    dati = png(df, f"{TITOLO} — {len(df)} risposte", etichette, dpi=200)
    st.image(dati, use_container_width=True)
    st.download_button("Scarica PNG", dati, file_name="complessivo.png", mime="image/png")

with tab_anno:
    griglia(elementi_anno())

with tab_classe:
    scelta = st.radio("Anno", ["Tutti"] + [str(a) for a in anni], horizontal=True)
    griglia(elementi_classi(None if scelta == "Tutti" else int(scelta)))

with tab_dati:
    st.dataframe(df.drop(columns=["classe_sez"]), use_container_width=True, hide_index=True)
    st.download_button("Scarica CSV coordinate", df.to_csv(index=False).encode("utf-8"),
                       file_name="ellisse_punti.csv", mime="text/csv")

# ---------------------------------------------------------------- zip con tutto
st.divider()
if st.button("Prepara ZIP con tutti i grafici"):
    with st.spinner("Genero i grafici…"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("complessivo.png", png(df, f"{TITOLO} — {len(df)} risposte", etichette, dpi=200))
            for nome, titolo, sub in elementi_anno():
                z.writestr(f"anni/{nome}", png(sub, titolo, etichette))
            for nome, titolo, sub in elementi_classi():
                z.writestr(f"classi/{nome}", png(sub, titolo, etichette))
            z.writestr("ellisse_punti.csv", df.to_csv(index=False))
        plt.close("all")
    st.download_button("Scarica ZIP", buf.getvalue(), file_name="grafici_ellisse.zip",
                       mime="application/zip")
