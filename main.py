import flet as ft
import sqlite3
import json
import re
import html
import ssl
import os
import time
import threading
from datetime import datetime, date, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlencode
import xml.etree.ElementTree as ET


# ----------------------------------------------------------------------------
# Fonti (uffici scolastici provinciali/regionali e Argo Interpelli)
# ----------------------------------------------------------------------------
PAGES_TO_FETCH = 5

ATA_KEYWORDS = [
    "ata", "dsga", "direttore dei servizi generali", "collaboratore scolastico", 
    "collaboratori scolastici", "assistente amministrativo", "assistenti amministrativi",
    "assistente tecnico", "assistenti tecnici", "operatore scolastico", "operatori scolastici",
    "operatore dei servizi agrari", "addetto aziende agrarie", "cuoco", "cuochi",
    "infermiere", "infermieri", "guardarobiere", "guardarobieri"
]

SOURCES = {
    "Nazionale / Piattaforme": [
        ("Argo Interpelli", "https://interpelloweb.it/", PAGES_TO_FETCH)
    ],
    "Abruzzo": [
        ("USP Chieti e Pescara", "https://www.istruzionechietipescara.it/category/interpelli-provinciali/feed/", 1),
        ("USP Teramo", "https://www.csateramo.it/wpusp/interpelli", 1),
        ("USP L'Aquila", "https://www.uspuquila.it/category/interpelli/feed/", 1)
    ],
    "Basilicata": [
        ("USP Matera", "https://www.istruzionematera.it/category/interpelli/feed/", 1),
        ("USP Potenza", "https://www.usppotenza.it/category/interpelli/feed/", 1)
    ],
    "Calabria": [
        ("USP Reggio Calabria", "https://www.usprc.it/category/interpelli/feed/", 1),
        ("USP Catanzaro", "https://www.uspcatanzaro.it/category/interpelli/feed/", 1),
        ("USP Cosenza", "https://www.uspcosenza.it/category/interpelli/feed/", 1)
    ],
    "Campania": [
        ("USP Caserta", "https://www.atpcaserta.it/category/interpelli/feed/", 1),
        ("USP Salerno", "https://www.atpsalerno.it/category/interpelli/feed/", 1),
        ("USP Napoli", "https://www.ustnapoli.it/category/interpelli/feed/", 1)
    ],
    "Emilia-Romagna": [
        ("USP Bologna", "https://interpelloweb.it/interpelli-supplenze/istituto/boss000vd8/", 1),
        ("USP Ferrara", "https://fe.istruzioneer.gov.it/category/interpelli_docenti/", 1),
        ("USP Modena", "https://mo.istruzioneer.gov.it/category/interpelli-personale-docente-2026-27/", 1),
        ("USP Parma", "https://pr.istruzioneer.gov.it/interpelli-docenti/", 1),
        ("USP Reggio Emilia", "https://re.istruzioneer.gov.it/tutte-le-notizie/", 1),
        ("USP Forlì Cesena", "https://fc.istruzioneer.gov.it/category/interpelli-a-s-2026-27/", 1),
        ("USP Piacenza", "https://pc.istruzioneer.gov.it/interpelli/", 1),
        ("USP Ravenna", "https://ra.istruzioneer.gov.it/conferimento-supplenze-per-esaurimento-graduatorie-di-istituto/", 1),
        ("USP Rimini", "https://rn.istruzioneer.gov.it/category/personale-docente/interpelli-docenti-2026-2027/", 1)
    ],
    "Friuli-Venezia Giulia": [
        ("USP Trieste", "https://usrfvg.gov.it/it/home/menu/uffici/ufficio-territoriale-di-trieste/Interpelli/index.html", 1),
        ("USP Udine", "https://usrfvg.gov.it/it/home/menu/uffici/ufficio-territoriale-di-udine/Interpelli/index.html", 1),
        ("USP Gorizia", "https://usrfvg.gov.it/it/home/menu/uffici/ufficio-territoriale-di-gorizia/Interpelli/", 1),
        ("USP Pordenone", "https://usrfvg.gov.it/it/home/menu/uffici/ufficio-territoriale-di-pordenone/Interpelli/index.html", 1)
    ],
    "Lazio": [
        ("USP Frosinone", "https://www.atpfrosinone.it/category/interpelli/feed/", 1),
        ("USP Latina", "https://www.csalatina.it/category/interpelli/feed/", 1),
        ("USP Roma", "https://www.atpromaistruzione.it/atp/category/interpelli/feed/", 1),
        ("USP Viterbo", "https://www.uspviterbo.it/category/interpelli/feed/", 1)
    ],
    "Liguria": [
        ("USP Genova", "https://servizi.istruzioneliguria.gov.it/provincia.php?provincia=GE", 1),
        ("USP La Spezia", "https://servizi.istruzioneliguria.gov.it/provincia.php?p=SP", 1),
        ("USP Imperia", "https://www.istruzioneimperia.gov.it/pagine/interpelli-e-comunicati", 1),
        ("USP Savona", "https://www.istruzionesavona.gov.it/pagine/interpelli-e-comunicati", 1)
    ],
    "Lombardia": [
        ("USP Milano", "https://www.mim.gov.it/web/milano/interpelli-ricerca-supplenti", 1),
        ("USP Brescia", "https://www.mim.gov.it/web/brescia/interpelli-ricerca-supplenti", 1),
        ("USP Bergamo", "https://www.mim.gov.it/web/bergamo/interpelli-ricerca-supplenti", 1),
        ("USP Como", "https://www.mim.gov.it/web/como/interpelli-ricerca-supplenti", 1),
        ("USP Cremona", "https://www.mim.gov.it/web/cremona/interpelli-ricerca-supplenti", 1),
        ("USP Lecco", "https://www.mim.gov.it/web/lecco/interpelli-ricerca-supplenti", 1),
        ("USP Lodi", "https://www.mim.gov.it/web/lodi/interpelli-ricerca-supplenti", 1),
        ("USP Mantova", "https://www.mim.gov.it/web/mantova/interpelli-ricerca-supplenti", 1),
        ("USP Monza brianza", "https://www.mim.gov.it/web/monza-brianza/interpelli-ricerca-supplenti", 1),
        ("USP Pavia", "https://www.mim.gov.it/web/pavia/interpelli-ricerca-supplenti", 1),
        ("USP Sondrio", "https://www.mim.gov.it/web/sondrio/interpelli-ricerca-supplenti", 1),
        ("USP Varese", "https://www.mim.gov.it/web/varese/interpelli-ricerca-supplenti", 1)
    ],
    "Marche": [
        ("USP Ancona", "https://www.uspancona.it/category/interpelli/feed/", 1),
        ("USP Macerata", "https://www.uspmacerata.it/category/interpelli/feed/", 1)
    ],
    "Molise": [
        ("USP Campobasso", "https://www.uspcampobasso.it/category/interpelli/feed/", 1)
    ],
    "Piemonte": [
        ("USP Torino", "https://www.istruzionepiemonte.it/torino/interpelli-supplenze/", PAGES_TO_FETCH),
        ("USP Cuneo", "https://www.istruzionepiemonte.it/cuneo/category/interpelli/feed/", 1),
        ("USP Novara", "https://www.istruzionepiemonte.it/novara/category/interpelli/feed/", 1)
    ],
    "Puglia": [
        ("USP Bari", "https://www.uspbari.it/category/interpelli/feed/", 1),
        ("USP Foggia", "https://www.fg.usrpuglia.gov.it/category/interpelli/feed/", 1),
        ("USP Lecce", "https://www.usplecce.it/category/interpelli/feed/", 1),
        ("USP Taranto", "https://www.usptaranto.it/category/interpelli/feed/", 1)
    ],
    "Sardegna": [
        ("USP Cagliari", "https://www.uspcagliari.it/category/interpelli/feed/", 1),
        ("USP Sassari", "https://www.uspsassari.it/category/interpelli/feed/", 1)
    ],
    "Sicilia": [
        ("USP Agrigento", "https://ag.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Caltanissetta-Enna", "https://cl-en.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Catania", "https://ct.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Palermo", "https://pa.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Siracusa", "https://sr.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Trapani", "https://tp.usr.sicilia.it/category/interpelli/feed/", 1)
    ],
    "Toscana": [
        ("USP Firenze", "https://www.toscana.istruzione.it/category/usp-firenze/interpelli/feed/", 1),
        ("USP Lucca", "https://www.toscana.istruzione.it/category/usp-lucca/interpelli/feed/", 1),
        ("USP Pisa", "https://www.toscana.istruzione.it/category/usp-pisa/interpelli/feed/", 1)
    ],
    "Trentino-Alto Adige": [
        ("USP Trento", "https://www.vivoscuola.it/feed/", 1)
    ],
    "Umbria": [
        ("USP Perugia", "https://www.usp.perugia.it/category/interpelli/feed/", 1)
    ],
    "Valle d'Aosta": [
        ("USP Aosta", "https://www.scuole.vda.it/category/interpelli/feed/", 1)
    ],
    "Veneto": [
        ("USP Padova", "https://padova.istruzioneveneto.gov.it/category/interpelli-personale-docente/", 1),
        ("USP Treviso", "https://treviso.istruzioneveneto.gov.it/tag/interpelli-istituti-scolastici/", 1),
        ("USP Venezia", "https://venezia.istruzioneveneto.gov.it/interpelli-supplenze/", 1),
        ("USP Verona", "https://verona.istruzioneveneto.gov.it/index.php/interpelli-as-2025-2026/", 1)
    ]
}


# ----------------------------------------------------------------------------
# Configurazione
# ----------------------------------------------------------------------------
DB_VERSION = 10


def get_db_path():
    db_dir = os.getenv("FLET_APP_STORAGE_DATA")
    if not db_dir:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = "."
        db_dir = os.path.join(base_dir, "data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "interpelli_nazionali.db")


DB = get_db_path()


# ----------------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------------
def db_connect():
    conn = sqlite3.connect(DB, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    return conn


def init_db():
    conn = db_connect()
    c = conn.cursor()
    version = c.execute("PRAGMA user_version").fetchone()[0]
    if version < DB_VERSION:
        c.execute("DROP TABLE IF EXISTS interpelli")
        c.execute(f"PRAGMA user_version = {DB_VERSION}")
    c.execute("""CREATE TABLE IF NOT EXISTS interpelli (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT UNIQUE,
        region TEXT,
        source TEXT,
        target TEXT,
        published TEXT,
        deadline TEXT,
        cdc TEXT,
        post_type TEXT,
        doc_url TEXT,
        email TEXT,
        verified INTEGER DEFAULT 0
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_interpelli_published ON interpelli(published DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_interpelli_region ON interpelli(region)")
    conn.commit()
    conn.close()


def known_urls():
    try:
        conn = db_connect()
        rows = conn.execute("SELECT url FROM interpelli").fetchall()
        conn.close()
        return {r[0] for r in rows}
    except sqlite3.Error:
        return set()


# ----------------------------------------------------------------------------
# Scraping
# ----------------------------------------------------------------------------
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<(script|style|noscript)\b.*?</\1>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()


def fetch_url(url, data=None, headers=None):
    default_headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"}
    if headers:
        default_headers.update(headers)
    req = Request(url, data=data, headers=default_headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urlopen(req, timeout=10, context=ctx) as resp:
        raw = resp.read(3_000_000)
        return raw.decode(resp.headers.get_content_charset() or 'utf-8', errors='replace')


def fetch_argo_filtrato(provincia="", classe_concorso="", known_urls_set=None):
    if known_urls_set is None:
        known_urls_set = set()
        
    url_ricerca = "https://interpelloweb.it/"
    items = []
    
    payload = {
        "provincia": provincia,
        "classe_concorso": classe_concorso,
        "cerca": "1"
    }
    
    data = urlencode(payload).encode('utf-8')
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": url_ricerca
    }
    
    try:
        html_content = fetch_url(url_ricerca, data=data, headers=headers)
        link_pattern = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
        for match in link_pattern.finditer(html_content):
            href, anchor_text = match.groups()
            cleaned_title = clean_text(anchor_text)
            
            if cleaned_title and len(cleaned_title) > 10:
                full_url = urljoin(url_ricerca, href)
                if full_url not in known_urls_set:
                    items.append((cleaned_title, full_url, None))
    except Exception as e:
        print(f"Errore nella ricerca filtrata su Argo: {e}")
        
    return items


def detect_cdc(title, body=""):
    _CDC_SPECIAL_RE = re.compile(r"\b(ADMM|ADSS|ADEE|ADAA|AAAA|EEEE|EEEM|PPPP)\b", re.I)
    _CDC_CODE_RE = re.compile(r"\b(?<![A-Za-z0-9])([A-Z]\d{2,3}|[A-Z]{2}\d{2})(?![A-Za-z0-9])")
    codes = [m.group(1).upper() for m in _CDC_SPECIAL_RE.finditer(title or "")]
    if not codes and body:
        codes = [m.group(1).upper() for m in _CDC_CODE_RE.finditer(body[:2500]) if not m.group(1).startswith(("L", "D", "N"))]
    return ", ".join(codes[:2])


# ----------------------------------------------------------------------------
# Interfaccia Grafica Flet (Android Ready)
# ----------------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "Interpelli Argo & USP"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    # Componenti della schermata
    provincia_dropdown = ft.Dropdown(
        label="Provincia / Regione",
        hint_text="Seleziona",
        options=[ft.dropdown.Option("Tutte")] + [ft.dropdown.Option(p) for p in SOURCES.keys() if p != "Nazionale / Piattaforme"],
        value="Tutte",
        expand=True
    )

    cdc_input = ft.TextField(
        label="Classe Concorso (es. A028)",
        hint_text="Tutte",
        expand=True
    )

    status_text = ft.Text("Seleziona i filtri e avvia la ricerca.", italic=True, size=12)
    results_list = ft.ListView(expand=True, spacing=10, padding=5)

    def carica_dati(prov, cdc):
        # Operazione eseguita in background per evitare schermata nera su Android
        try:
            init_db()
            known = known_urls()
            
            # Recupero da Argo
            nuovi = fetch_argo_filtrato(provincia=prov if prov != "Tutte" else "", classe_concorso=cdc, known_urls_set=known)
            
            conn = db_connect()
            c = conn.cursor()
            for title, url, pub in nuovi:
                cdc_found = detect_cdc(title)
                c.execute("""INSERT OR IGNORE INTO interpelli 
                    (title, url, region, source, target, published, cdc, verified)
                    VALUES (?, ?, ?, 'Argo Interpelli', 'DOCENTI', ?, ?, 1)""",
                    (title, url, prov if prov != "Tutte" else "Nazionale", date.today().strftime("%Y-%m-%d"), cdc_found))
            conn.commit()

            # Query di lettura locale
            query = "SELECT title, url, region, published, cdc FROM interpelli WHERE 1=1"
            params = []
            if prov != "Tutte":
                query += " AND region = ?"
                params.append(prov)
            if cdc:
                query += " AND cdc LIKE ?"
                params.append(f"%{cdc}%")
            
            query += " ORDER BY id DESC LIMIT 50"
            rows = conn.execute(query, params).fetchall()
            conn.close()

            results_list.controls.clear()
            if not rows:
                results_list.controls.append(ft.Text("Nessun interpello trovato con i criteri inseriti."))
            else:
                for r in rows:
                    title, url, region, pub, found_cdc = r
                    results_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(title, weight=ft.FontWeight.BOLD, size=14),
                                    ft.Row([
                                        ft.Chip(label=ft.Text(f"Zona: {region}", size=11)),
                                        ft.Chip(label=ft.Text(f"CDC: {found_cdc if found_cdc else 'N/D'}", size=11)),
                                    ], wrap=True),
                                    ft.TextButton("Apri Avviso sul Sito", url=url)
                                ], spacing=5),
                                padding=12
                            )
                        )
                    )
            status_text.value = f"Trovati {len(rows)} interpelli."
        except Exception as ex:
            status_text.value = f"Errore caricamento: {ex}"

        page.update()

    def esegui_ricerca(e):
        status_text.value = "Ricerca in corso su Argo Interpelli..."
        page.update()
        
        prov = provincia_dropdown.value
        cdc = cdc_input.value.strip().upper()

        # Avvio in thread separato
        threading.Thread(target=carica_dati, args=(prov, cdc), daemon=True).start()

    btn_cerca = ft.ElevatedButton("Avvia Ricerca", on_click=esegui_ricerca, icon=ft.Icons.SEARCH)

    # Costruzione layout dell'interfaccia Flet
    page.add(
        ft.Text("Ricerca Interpelli Scuola", size=18, weight=ft.FontWeight.BOLD),
        ft.Row([provincia_dropdown, cdc_input], spacing=10),
        ft.Row([btn_cerca], alignment=ft.MainAxisAlignment.END),
        status_text,
        ft.Divider(),
        results_list
    )
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
