# Ellisse della percezione — web app Streamlit

Carica l'Excel delle risposte e ottieni i grafici a ellisse:
- **Complessivo**: tutti gli studenti
- **Per anno**: un grafico per ciascun anno (1-5)
- **Per classe**: un grafico per ogni classe (anno + sezione), filtrabile per anno
- **Dati**: tabella con le coordinate calcolate (scaricabile in CSV)

Ogni grafico ha il suo bottone "Scarica PNG"; in fondo alla pagina c'è uno ZIP con tutto.
Il jitter casuale è calcolato una volta sola sull'intero file: ogni studente è nella stessa
posizione in tutti i grafici. Cambiando il "seme" cambia la disposizione.

## Avvio in locale
    pip install -r requirements.txt
    streamlit run app.py

## Pubblicarla (Streamlit Community Cloud, gratuito)
1. Metti questa cartella in un repository GitHub (app.py, ellisse_excel.py, requirements.txt).
2. Vai su https://share.streamlit.io → "New app" → scegli repository e `app.py`.

## Colonne attese nell'Excel (in quest'ordine)
data/ora · valore asse X (0-10) · valore asse Y (0-10) · classe (1-5) · sezione · genere

Colori, etichette e gruppi si modificano in cima a `ellisse_excel.py`.
