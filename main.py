import flet as ft
import sqlite3
import json
import re
import html
import ssl
import socket
import os
import time
import threading
from datetime import datetime, date, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urljoin, quote
import xml.etree.ElementTree as ET


# ----------------------------------------------------------------------------
# Fonti (uffici scolastici provinciali/regionali)
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
    "Abruzzo": [
        ("USP Chieti e Pescara", "https://www.istruzionechietipescara.it/category/interpelli-provinciali/feed/", 1),
        ("USP Teramo", "https://www.csateramo.it/wpusp/interpelli", 1),
        ("USP L'Aquila", "https://lnx.csalaquila.it/wp/category/interpelli/feed/", 1)
    ],
    "Basilicata": [
        ("USP Matera", "https://www.istruzionematera.it/category/interpelli/feed/", 1)
    ],
    "Calabria": [
        ("USP Reggio Calabria", "https://www.istruzioneatprc.it/category/recl/int/feed/", 1),
        ("USP Catanzaro", "https://www.istruzione.calabria.it/catanzaro/category/nca/feed/", 1),
        ("USP Cosenza", "https://www.istruzione.calabria.it/cosenza/category/interdoc/feed/", 1)
    ],
    "Campania": [
        ("USP Caserta", "https://www.uat-caserta.it/category/segnalazioni-dalle-scuole/feed/", 1),
        ("USP Salerno", "https://uat-salerno.it/Documenti/CIRCOLARI/Interpelli-per-reclutamento-personale-docente", 1),
        ("USP Napoli", "https://www.uat-napoli.it/tag/interpelli-personale-docente/feed/", 1)
    ],
    "Emilia-Romagna": [
        ("USP Bologna", "https://bo.istruzioneer.gov.it/category/docenti/feed/", 1),
        ("USP Ferrara", "https://fe.istruzioneer.gov.it/category/interpelli_docenti/", 1),
        ("USP Modena", "https://mo.istruzioneer.gov.it/category/interpelli-personale-docente-2026-27/", 1),
        ("USP Parma", "https://pr.istruzioneer.gov.it/interpelli-docenti/", 1),
        ("USP Reggio Emilia", "https://re.istruzioneer.gov.it/category/docenti/feed/", 1),
        ("USP Forlì Cesena", "https://fc.istruzioneer.gov.it/category/interpelli-a-s-2026-27/", 1),
        ("USP Piacenza", "https://pc.istruzioneer.gov.it/interpelli/", 1),
        ("USP Ravenna", "https://ra.istruzioneer.gov.it/conferimento-supplenze-per-esaurimento-graduatorie-di-istituto/", 1),
        ("USP Rimini", "https://rn.istruzioneer.gov.it/category/personale-docente/interpelli-docenti-2026-2027/", 1)
    ],
    "Lazio": [
        ("USP Frosinone", "https://lnx.uspistruzione.fr.it/wp2/category/interpello-nazionale/feed/", 1),
        ("USP Latina", "https://www.csalatina.it/category/interpelli/feed/", 1),
        ("USP Roma", "https://www.atpromaistruzione.it/atp/category/reclutamento/interpelli-personale-docente/feed/", 1),
        ("USP Viterbo", "http://www.provveditoratostudiviterbo.it/DOCENTI/interpelli/INTERPELLIDOC.htm", 1)
    ],
    "Liguria": [
        ("USP Genova", "https://servizi.istruzioneliguria.gov.it/provincia.php?p=GE", 1),
        ("USP La Spezia", "https://servizi.istruzioneliguria.gov.it/provincia.php?p=SP", 1),
        ("USP Imperia", "https://servizi.istruzioneliguria.gov.it/provincia.php?p=IM", 1),
        ("USP Savona", "https://servizi.istruzioneliguria.gov.it/provincia.php?p=SV", 1)
    ],
    "Lombardia": [
        ("USP Milano", "https://milano.istruzionelombardia.gov.it/argomento/interpelli-ricerca-supplenti/", 1),
        ("USP Brescia", "https://brescia.istruzionelombardia.gov.it/argomento/interpelli-ricerca-supplenti/", 1),
        ("USP Bergamo", "https://bergamo.istruzionelombardia.gov.it/argomento/interpelli-ricerca-supplenti/", 1),
        ("USP Como", "https://como.istruzionelombardia.gov.it/argomento/interpelli-ricerca-supplenti/", 1),
        ("USP Cremona", "https://www.mim.gov.it/web/cremona/interpelli-ricerca-supplenti", 1),
        ("USP Lecco", "https://www.mim.gov.it/web/lecco/interpelli-ricerca-supplenti", 1),
        ("USP Lodi", "https://www.mim.gov.it/web/lodi/interpelli-ricerca-supplenti", 1),
        ("USP Mantova", "https://www.mim.gov.it/web/mantova/interpelli-ricerca-supplenti", 1),
        ("USP Monza brianza", "https://www.mim.gov.it/web/monza-brianza/interpelli-ricerca-supplenti", 1),
        ("USP Pavia", "https://pavia.istruzionelombardia.gov.it/argomento/interpelli-ricerca-supplenti/", 1),
        ("USP Sondrio", "https://www.mim.gov.it/web/sondrio/interpelli-ricerca-supplenti", 1),
        ("USP Varese", "https://varese.istruzionelombardia.gov.it/argomento/interpelli-ricerca-supplenti/", 1)
    ],
    "Marche": [
        ("USP Ancona", "https://www.istruzione-ancona.it/category/docenti/feed/", 1),
        ("USP Pesaro Urbino", "http://www.usppesarourbino.it/category/interpelli/feed/", 1)
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
        ("USP Bari", "https://www.uspbari.it/usp/category/interpelli-della-provincia-di-bari", 1),
        ("USP Foggia", "https://www.ustfoggia.it/feed/", 1),
        ("USP Lecce", "https://www.usplecce.it/category/interpelli/feed/", 1),
        ("USP Taranto", "https://www.usptaranto.it/category/in-evidenza/", 1)
    ],
    "Sardegna": [
        ("USP Sassari", "https://www.uspss.it/wordpress/nomine-a-t-d-usp-nazionali", 1)
    ],
    "Sicilia": [
        ("USP Agrigento", "https://ag.usr.sicilia.it/category/personale-scuola/personale-docente/interpelli/", 1),
        ("USP Caltanissetta-Enna", "https://cl-en.usr.sicilia.it/category/personale-scuola/personale-docente/", 1),
        ("USP Catania", "https://ct.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Palermo", "https://pa.usr.sicilia.it/category/interpelli/feed/", 1),
        ("USP Siracusa", "https://sr.usr.sicilia.it/tag/interpelli/", 1),
        ("USP Trapani", "https://tp.usr.sicilia.it/personale-scuola/interpelli/", 1),
        ("USP Messina", "https://me.usr.sicilia.it/personale-scuola/interpelli/", 1)
    ],
    "Toscana": [
        ("USP Firenze", "https://www.ust.fi.it/", 1),
        ("USP Lucca", "https://www.ustlucca.it/feed/", 1),
        ("USP Pisa", "https://www.toscana-istruzione.it/atpisa/category/news/", 1)
    ],
    "Trentino-Alto Adige": [
        ("USP Trento", "https://www.vivoscuola.it/feed/", 1)
    ],
    "Umbria": [
        ("USP Perugia", "https://istruzione.umbria.it/interpelli/interpelli-aperti/", 1)
    ],
    "Valle d'Aosta": [
        ("USP Aosta", "https://www.scuole.vda.it/category/interpelli/feed/", 1)
    ],
    "Veneto": [
        ("USP Padova", "https://padova.istruzioneveneto.gov.it/category/interpelli-personale-docente/", 1),
        ("USP Treviso", "https://treviso.istruzioneveneto.gov.it/tag/interpelli-istituti-scolastici/", 1),
        ("USP Venezia", "https://venezia.istruzioneveneto.gov.it/interpelli-supplenze/", 1),
        ("USP Verona", "https://verona.istruzioneveneto.gov.it/index.php/interpelli-2026-2027/", 1),
        ("USP Rovigo", "https://rovigo.istruzioneveneto.gov.it/category/5-interpelli/docenti-rovigo/", 1)
    ]
}


# ----------------------------------------------------------------------------
# Configurazione
# ----------------------------------------------------------------------------
MAX_WORKERS = 15
PAGE_SIZE = 25          # interpelli mostrati per "blocco"
DB_VERSION = 6          # alzare per forzare il rifacimento della cache
GPS_LISTS_URL = "https://www.orizzontescuola.it/gps-docenti-2026-27-ecco-le-prime-graduatorie-in-aggiornamento/"
SOON_DAYS = 3           # "in scadenza" = scade entro questi giorni

MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

# Palette (il resto dei colori segue il tema chiaro/scuro del sistema)
BRAND_DARK = "#1C248C"
BRAND_LIGHT = "#347CF6"
GOLD = "#FFC83D"
GREEN = "#16A363"


def get_db_path():
    # Su Android la cartella dell'app è di sola lettura: Flet fornisce una
    # cartella dati scrivibile tramite FLET_APP_STORAGE_DATA.
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
    # La tabella è solo una cache degli avvisi online: se cambia lo schema o la
    # logica di classificazione basta ricrearla e riscaricare.
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
# Download e analisi delle pagine
# ----------------------------------------------------------------------------
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<(script|style|noscript)\b.*?</\1>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()


def _open(url, context=None):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"})
    with urlopen(req, timeout=10, context=context) as resp:
        raw = resp.read(2_000_000)
        return raw.decode(resp.headers.get_content_charset() or 'utf-8', errors='replace')


def fetch_url(url):
    # Prima con verifica del certificato; solo se fallisce (molti siti
    # istituzionali hanno catene incomplete, e su Android manca il bundle CA)
    # si ripiega sulla connessione non verificata.
    try:
        return _open(url, ssl.create_default_context())
    except Exception as ex:
        reason = getattr(ex, "reason", ex)
        if isinstance(reason, socket.gaierror) or "name or service" in str(ex).lower():
            # Nome non risolto: prova con/senza "www."
            alt = re.sub(r"^(https?://)www\.", r"\1", url) if "://www." in url else re.sub(r"^(https?://)", r"\1www.", url)
            if alt != url and not getattr(fetch_url, "_alt", False):
                try:
                    return _open(alt, ssl.create_default_context())
                except Exception:
                    pass
        if isinstance(reason, ssl.SSLError) or "CERTIFICATE" in str(ex).upper():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return _open(url, ctx)
        raise


MESI_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7,
    "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6, "lug": 7, "ago": 8,
    "set": 9, "sett": 9, "ott": 10, "nov": 11, "dic": 12,
}
_MESI_RE = "|".join(sorted(MESI_IT, key=len, reverse=True))
DATE_NUM = r"\d{1,2}\s?[\/\-.]\s?\d{1,2}\s?[\/\-.]\s?(?:\d{4}|\d{2})(?!\d)"
DATE_TXT = rf"\d{{1,2}}\s?(?:°|º)?\s+(?:{_MESI_RE})\b\.?(?:\s*,?\s*(?:\d{{4}}|\d{{2}}(?!\d)))?"
DATE_ANY = rf"(?:{DATE_NUM}|{DATE_TXT})"


def _mk(year, month, day):
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_date(value, default_year=None):
    """Converte una data (RSS, ISO, 12/10/2025, 12 ottobre 2025, 12 ott) in 'AAAA-MM-GG'."""
    if not value:
        return None
    value = value.strip()
    if re.match(r"^[A-Za-z]{3},", value):          # formato RSS: "Mon, 05 Oct 2026 ..."
        try:
            return parsedate_to_datetime(value).strftime("%Y-%m-%d")
        except Exception:
            pass

    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if iso:
        return _mk(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))

    m = re.search(r"(\d{1,2})\s?[\/\-.]\s?(\d{1,2})\s?[\/\-.]\s?(\d{4}|\d{2})(?!\d)", value)
    if m:
        day, month, year = m.groups()
        year = int(year) + (2000 if len(year) == 2 else 0)
        return _mk(year, int(month), int(day))

    m = re.search(rf"(\d{{1,2}})\s?(?:°|º)?\s+({_MESI_RE})\b\.?(?:\s*,?\s*(\d{{4}}|\d{{2}}(?!\d)))?", value, re.I)
    if m:
        day, mese, year = m.groups()
        if year:
            year = int(year) + (2000 if len(year) == 2 else 0)
        else:
            year = default_year or date.today().year
        return _mk(year, MESI_IT[mese.lower()], int(day))

    try:
        return parsedate_to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return None


# --- scadenza -----------------------------------------------------------------
_KEY = (r"(?:entro(?:\s+e\s+non\s+oltre)?|non\s+oltre|scadenz[ae]|termine(?:\s+ultimo)?|"
        r"improrogabilmente|presentat[ae]\s+(?:dal\s+\S+\s+)?al)")
_NOSTOP = r"(?:(?!\.\s)(?!\n).)"            # niente fine-frase tra parola chiave e data
DEADLINE_RE = re.compile(rf"({_KEY})({_NOSTOP}{{0,110}}?)({DATE_ANY})", re.I | re.S)
APPLY_WORDS = re.compile(r"domand|candidatur|disponibilit|istanz|present|invia|trasmett|pervenir|"
                         r"comunicar|manifest|aspirant|\bMAD\b|aderir|adesion", re.I)
CONTRACT_WORDS = re.compile(r"supplenz|incaric|contratt|nomina|assunzion|servizio|durata|"
                            r"fino\s+al|sino\s+al|termine\s+delle\s+(?:lezioni|attivit)", re.I)


def find_deadline(text, published=None):
    """Cerca la scadenza per presentare la disponibilità. Restituisce (data ISO, frase trovata)."""
    pub = to_date(published) if published else None
    default_year = pub.year if pub else date.today().year
    best = None
    for m in DEADLINE_RE.finditer(text):
        key, between, raw = m.group(1), m.group(2), m.group(3)
        iso = parse_date(raw, default_year)
        if not iso:
            continue
        d = to_date(iso)
        # data senza anno già molto precedente alla pubblicazione -> anno dopo
        if pub and not re.search(r"\d{4}|/\d{2}\b|\.\d{2}\b", raw) and (pub - d).days > 30:
            iso = _mk(d.year + 1, d.month, d.day) or iso
            d = to_date(iso)

        before = text[max(0, m.start() - 90):m.start()]
        context = before + key + between
        score = 0
        if APPLY_WORDS.search(context):
            score += 3
        if re.search(r"\bore\b|\d{1,2}[:.]\d{2}", between):
            score += 2
        if re.match(r"(?i)entro|non\s+oltre|scadenz", key):
            score += 1
        if CONTRACT_WORDS.search(before[-45:] + key + between[:25]) and not APPLY_WORDS.search(context):
            score -= 3
        if d.month in (6, 8) and d.day in (30, 31) and score < 4:
            score -= 2                                    # tipica fine contratto/anno scolastico
        if pub:
            delta = (d - pub).days
            if delta < -1:
                score -= 3
            elif delta > 150:
                score -= 2
        if score >= 1 and (best is None or score > best[0]):
            a = max(0, m.start() - 25)
            snippet = text[a:m.end() + 25].strip()
            best = (score, iso, snippet)
    if best:
        return best[1], best[2]
    return None, ""


# --- pubblicazione ---------------------------------------------------------------
_META_PUB = [
    r'<meta[^>]+(?:property|name|itemprop)=["\'](?:article:published_time|datePublished|date|dc\.date(?:\.issued)?|'
    r'dcterms\.(?:created|issued|date)|og:article:published_time)["\'][^>]*content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name|itemprop)=["\'](?:article:published_time|datePublished|date)["\']',
    r'"datePublished"\s*:\s*"([^"]+)"',
]
PUB_TEXT_RE = re.compile(
    rf"(?:pubblicat[oa](?:\s+(?:il|in\s+data|data|sul\s+sito))?|data\s+(?:di\s+)?pubblicazione|"
    rf"pubblicazione|inserit[oa]\s+il|data\s+inserimento)\s*:?\s*(?:[A-Za-zàèéìòù]+\s+)?({DATE_ANY})", re.I)


def find_published(page_html, main_html, text):
    """Data di pubblicazione: metadati della pagina, poi tag <time>, poi testo. -> (ISO, origine)"""
    for pat in _META_PUB:
        m = re.search(pat, page_html, re.I | re.S)
        if m:
            iso = parse_date(m.group(1))
            if iso:
                return iso, "metadati della pagina"
    for m in re.finditer(r'<time\b([^>]*)>', main_html, re.I):
        attrs = m.group(1)
        dt = re.search(r'datetime=["\']([^"\']+)["\']', attrs, re.I)
        if dt and not re.search(r'updated|modified', attrs, re.I):
            iso = parse_date(dt.group(1))
            if iso:
                return iso, "data indicata nella pagina"
    m = PUB_TEXT_RE.search(text)
    if m:
        iso = parse_date(m.group(1))
        if iso:
            return iso, "testo dell'avviso"
    return None, ""


# --- contenuto principale della pagina ---------------------------------------------
def main_region(page_html):
    """Isola il corpo dell'avviso, scartando menu, barre laterali e piè di pagina."""
    h = re.sub(r'<(script|style|noscript)\b.*?</\1>', ' ', page_html, flags=re.I | re.S)
    arts = re.findall(r'<article\b.*?</article>', h, flags=re.I | re.S)
    if arts:
        return max(arts, key=len)
    m = re.search(r'<(?:div|section)\b[^>]*class=["\'][^"\']*(?:entry-content|post-content|article-body|'
                  r'node__content|field--name-body|contenuto|content-main)[^"\']*["\'][^>]*>', h, re.I)
    if m:
        return h[m.start():m.start() + 40000]
    mains = re.findall(r'<main\b.*?</main>', h, flags=re.I | re.S)
    if mains:
        return max(mains, key=len)
    return strip_chrome(h)


def strip_chrome(h):
    """Toglie menu, intestazioni, piè di pagina e barre laterali."""
    h = re.sub(r'<(script|style|noscript)\b.*?</\1>', ' ', h, flags=re.I | re.S)
    for tag in ("nav", "header", "footer", "aside"):
        h = re.sub(rf'<{tag}\b.*?</{tag}>', ' ', h, flags=re.I | re.S)
    return h


def analyze_post_content(full_text):
    text = full_text.lower()
    post_type = "Posto Ordinario / Altro"

    if "sostegno" in text:
        post_type = "Posto di Sostegno"
    elif "spezzone" in text:
        post_type = "Spezzone Orario"
    elif "cattedra orario esterna" in text or re.search(r"\bcoe\b", text):
        post_type = "Cattedra Orario Esterna (COE)"
    elif "cattedra orario interna" in text or re.search(r"\bcoi\b", text):
        post_type = "Cattedra Orario Interna (COI)"
    elif "annuale" in text:
        post_type = "Annuale"
    return post_type


# ----------------------------------------------------------------------------
# Classificazione: ATA / docenti, classi di concorso, avvisi che non sono interpelli
# ----------------------------------------------------------------------------
# ATA: nel TITOLO bastano parole anche generiche; nel TESTO servono profili precisi
# (così "procedimento amministrativo" in un avviso per docenti non lo rende ATA).
ATA_TITLE_RE = re.compile(
    r"(?:\bATA\b|\bA\.\s?T\.\s?A\.?|personale\s+ata|collaborator[ei]\s+scolastic[oi]|"
    r"assistent[ei]\s+(?:amministrativ|tecnic)\w*|amministrativ[oiae]|\bDSGA\b|"
    r"direttore\s+dei\s+servizi\s+generali|\bcuoc[oh]i?\b|\binfermier[ei]\b|\bguardarobier[ei]\b|"
    r"operator[ei]\s+scolastic\w*|operator[ei]\s+dei\s+servizi\s+agrari|"
    r"addett[oi]\s+(?:alle?\s+)?aziend\w*\s+agrar\w*|\bpersonale\s+amministrativo\b)", re.I)
ATA_BODY_RE = re.compile(
    r"(?:\bATA\b|\bA\.\s?T\.\s?A\.?|personale\s+ata|collaborator[ei]\s+scolastic[oi]|"
    r"assistent[ei]\s+(?:amministrativ|tecnic)\w*|\bDSGA\b|direttore\s+dei\s+servizi\s+generali|"
    r"\bcuoc[oh]i?\b|\binfermier[ei]\b|\bguardarobier[ei]\b|operator[ei]\s+scolastic\w*|"
    r"operator[ei]\s+dei\s+servizi\s+agrari|addett[oi]\s+(?:alle?\s+)?aziend\w*\s+agrar\w*)", re.I)
# Il termine "ATA" in maiuscolo è valido anche da solo; le altre voci senza distinzione di maiuscole.
ATA_PATTERN = ATA_BODY_RE   # compatibilità

# Classi di concorso: A028, B012, AB24, BA02... più i codici speciali di infanzia/primaria/sostegno.
CDC_SPECIAL = ["ADMM", "ADSS", "ADEE", "ADAA", "AAAA", "EEEE", "EEEM", "PPPP"]
CDC_NAMES = {
    "PPPP": "Personale educativo",
    "EEEM": "Educazione motoria",
    "EEEE": "Primaria (posto comune)",
    "ADEE": "Sostegno primaria",
    "AAAA": "Infanzia (posto comune)",
    "ADAA": "Sostegno infanzia",
    "ADMM": "Sostegno sec. I grado",
    "ADSS": "Sostegno sec. II grado",
}
# Descrizioni in lettere che indicano una classe anche quando il codice non è scritto
CDC_PHRASES = [
    (re.compile(r"personale\s+educativ\w*", re.I), "PPPP"),
    (re.compile(r"educazione\s+motoria|\bed\.?\s*motoria|insegnante\s+di\s+motoria", re.I), "EEEM"),
]
# Parole di ricerca che rimandano a una classe (es. cercando "motoria" trova EEEM)
CDC_SEARCH_ALIASES = {
    "motoria": "EEEM", "motorie": "EEEM",
    "educativo": "PPPP", "educativi": "PPPP", "educativa": "PPPP",
}
_CDC_SPECIAL_RE = re.compile(r"\b(" + "|".join(CDC_SPECIAL) + r")\b", re.I)
_CDC_CODE_RE = re.compile(r"\b(?<![A-Za-z0-9])([A-Z]\d{2,3}|[A-Z]{2}\d{2})(?![A-Za-z0-9])")
_CDC_BAD_PREFIX = ("L", "D", "N")      # L.107, D25, n123: leggi/decreti/numeri, non classi


def _codes_in(text, limit=3):
    """Codici di classe in ordine di apparizione, senza doppioni."""
    spans = [(m.start(), m.group(1).upper()) for m in _CDC_SPECIAL_RE.finditer(text)]
    for m in _CDC_CODE_RE.finditer(text):
        code = m.group(1)
        if code[0] in _CDC_BAD_PREFIX and code[1:].isdigit():
            continue
        if re.fullmatch(r"AR\d{2}", code):      # aree degli assistenti tecnici (ATA), non classi docenti
            continue
        spans.append((m.start(), code))
    for rx, code in CDC_PHRASES:
        m = rx.search(text)
        if m:
            spans.append((m.start(), code))
    explicit = {m.group(1).upper() for m in _CDC_SPECIAL_RE.finditer(text)}
    ordered = []
    for _, code in sorted(spans):
        if code not in ordered:
            ordered.append(code)
    # "personale educativo" e "educazione motoria" nello stesso testo: è PPPP, a meno che
    # EEEM non sia scritto come codice esplicito.
    if "PPPP" in ordered and "EEEM" in ordered and "EEEM" not in explicit:
        ordered.remove("EEEM")
    return ordered[:limit]


def detect_cdc(title, body=""):
    """Classi di concorso: prima quelle scritte nel titolo, poi quelle nell'inizio del testo."""
    codes = _codes_in(title or "")
    if not codes and body and not ATA_TITLE_RE.search(title or ""):
        codes = _codes_in(body[:2500], limit=2)
    return ", ".join(codes)


def cdc_label(cdc):
    """'PPPP' -> 'PPPP · Personale educativo' (solo per un singolo codice con nome noto)."""
    if cdc and cdc in CDC_NAMES:
        return f"{cdc} · {CDC_NAMES[cdc]}"
    return cdc


NOT_INTERPELLO_RE = re.compile(r"bollettin\w*|\bnomine\b", re.I)


def is_not_interpello(title):
    """Bollettini delle nomine e simili: sono esiti, non interpelli."""
    return bool(NOT_INTERPELLO_RE.search(title or ""))


# Diciture che indicano il personale docente/educativo (nel titolo sono decisive).
DOC_WORDS_RE = re.compile(
    r"(?:personale\s+docente|\bdocent[ei]\b|\binsegnant[ei]\b|personale\s+educativ\w*|"
    r"\beducator[ei]\b|\beducatric[ei]\b|\bcl(?:asse|\.)?\s+di\s+concorso|\bcdc\b)", re.I)


def _first_doc_pos(text):
    """Posizione della prima dicitura da docente (parola o classe di concorso) nel testo."""
    pos = []
    m = DOC_WORDS_RE.search(text)
    if m:
        pos.append(m.start())
    m = _CDC_SPECIAL_RE.search(text)
    if m:
        pos.append(m.start())
    for m in _CDC_CODE_RE.finditer(text):
        code = m.group(1)
        if code[0] in _CDC_BAD_PREFIX and code[1:].isdigit():
            continue
        if re.fullmatch(r"AR\d{2}", code):
            continue
        pos.append(m.start())
        break
    return min(pos) if pos else None


_EDUCATIVO_RE = re.compile(r"\bPPPP\b|personale\s+educativ\w*", re.I)


def detect_target(title, body=""):
    """'ATA' solo con una dicitura ATA esplicita (ata, collaboratore scolastico, amministrativo,
    dsga, cuoco...). Se compare "personale docente" o una classe di concorso, è DOCENTI."""
    title = title or ""
    if DOC_WORDS_RE.search(title) or _codes_in(title):
        return "DOCENTI"
    if ATA_TITLE_RE.search(title):
        return "ATA"

    # titolo neutro: guarda l'inizio del testo e decide per ciò che compare per primo
    head = (body or "")[:2500]
    if _EDUCATIVO_RE.search(head):          # PPPP / personale educativo non è mai ATA
        return "DOCENTI"
    body_ata = ATA_BODY_RE.search(head)
    if not body_ata:
        return "DOCENTI"
    doc_pos = _first_doc_pos(head)
    if doc_pos is not None and doc_pos < body_ata.start():
        return "DOCENTI"
    if doc_pos is not None and DOC_WORDS_RE.search(head) and not re.search(r"\bATA\b", head):
        return "DOCENTI"
    return "ATA"


DOC_RE = re.compile(r'href=["\']([^"\']+\.(?:pdf|docx?|odt)(?:\?[^"\']*)?)["\']', re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def extract_doc_url(page_html, base_url):
    """Primo allegato (pdf/doc/odt) della pagina, preferendo quelli che parlano di interpello."""
    found = [urljoin(base_url, h) for h in DOC_RE.findall(page_html)]
    for u in found:
        if any(k in u.lower() for k in ["interpell", "supplenz", "avviso"]):
            return u
    return found[0] if found else ""


def extract_email(text):
    """Indirizzo email più plausibile per la candidatura (preferisce PEC/istituzionali)."""
    emails = []
    for e in EMAIL_RE.findall(text):
        e = e.strip(".").lower()
        if e not in emails:
            emails.append(e)
    for e in emails:
        if e.endswith(".edu.it") or "istruzione.it" in e or "pec" in e:
            return e
    return emails[0] if emails else ""


FILE_EXT_RE = re.compile(r"\.(?:pdf|docx?|odt|xlsx?|zip)(?:\?.*)?$", re.I)


def analyze_page(page_html, link, rss_published=None):
    """Legge una pagina-avviso e ne estrae i dati. Tutte le date partono dal testo dell'avviso."""
    main_html = main_region(page_html)
    text = clean_text(main_html)
    if len(text) < 3:                            # pagina atipica: usa tutta la pagina (senza menu)
        main_html = strip_chrome(page_html)
        text = clean_text(main_html)
    pub, pub_src = find_published(page_html, main_html, text)
    if not pub and rss_published:
        pub, pub_src = rss_published, "elenco dell'ufficio"
    if not pub:
        m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', link)
        if m:
            pub, pub_src = f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "indirizzo della pagina"
    deadline, deadline_src = find_deadline(text, pub)
    return {
        "text": text,
        "post_type": analyze_post_content(text),
        "published": pub or "",
        "published_src": pub_src,
        "deadline": deadline,
        "deadline_src": deadline_src,
        "doc_url": extract_doc_url(main_html, link) or extract_doc_url(page_html, link),
        "email": extract_email(text),
        "html": main_html[:20000],
    }


def fetch_page_details(link, rss_published=None):
    """Come analyze_page ma scaricando la pagina; None se non raggiungibile."""
    if FILE_EXT_RE.search(link):
        return {"text": "", "post_type": "Non specificato", "published": rss_published or "",
                "published_src": "elenco dell'ufficio" if rss_published else "", "deadline": None,
                "deadline_src": "", "doc_url": link, "email": ""}
    try:
        return analyze_page(fetch_url(link), link, rss_published)
    except Exception:
        return None


def verify_interpello(url, rss_published=None, title=""):
    """Riapre l'avviso e rilegge date, profilo (docenti/ATA) e classe. None se la pagina non risponde."""
    info = fetch_page_details(url, rss_published)
    if info is None:
        return None
    heading = ""
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", info.get("html", ""), re.I | re.S)
    if m:
        heading = clean_text(m.group(1))
    info["heading"] = heading
    info["not_interpello"] = is_not_interpello(title) or is_not_interpello(heading)
    info["target"] = detect_target(title or heading, info["text"])
    info["cdc"] = detect_cdc(title or heading, info["text"])
    return info


def get_page_url(base_url, page_num):
    if page_num == 1:
        return base_url
    if base_url.endswith("/feed/"):
        return f"{base_url[:-6]}/page/{page_num}/feed/"
    if "paged=" in base_url or "page=" in base_url:
        return re.sub(r'(paged|page)=\d+', f'\\1={page_num}', base_url)
    elif "?" in base_url:
        return f"{base_url}&paged={page_num}"
    else:
        if base_url.endswith("/"):
            return f"{base_url}page/{page_num}/"
        return f"{base_url}?paged={page_num}"


NOTICE_LINK_RE = re.compile(r"\b(?:interpell\w*|interp\b\.?|supplenz\w*|avvis\w*|graduatori\w*|docent\w*|ata|dsga|"
                            r"collaborator\w*|assistent\w*|disponibilit\w*)\b", re.I)


SOURCE_LOG = {}          # nome fonte -> {"ok", "found", "new", "err"} dell'ultimo aggiornamento


def short_error(ex):
    code = getattr(ex, "code", None)
    if code:
        return f"errore HTTP {code}"
    reason = getattr(ex, "reason", None) or ex
    text = str(reason).strip() or type(ex).__name__
    return text[:70]


def log_source(name, ok=None, found=0, new=0, err=""):
    e = SOURCE_LOG.setdefault(name, {"ok": False, "found": 0, "new": 0, "err": ""})
    if ok:
        e["ok"], e["err"] = True, ""
    elif err and not e["ok"]:
        e["err"] = err
    e["found"] += found
    e["new"] += new


def parse_source_page(region, source_name, url, known):
    """Scarica una pagina-fonte e restituisce (nuovi_interpelli, raggiungibile).

    Gli avvisi già presenti nel database (`known`) non vengono riscaricati:
    questo rende gli aggiornamenti successivi al primo molto più veloci.
    """
    items = []
    try:
        html_content = fetch_url(url)
    except Exception as ex:
        log_source(source_name, err=short_error(ex))
        return [], False

    lower_content = html_content.lower()
    if "<rss" in lower_content or "<feed" in lower_content or "<channel" in lower_content:
        try:
            root = ET.fromstring(html_content)
            for item in root.findall(".//item"):
                title = clean_text(item.findtext("title"))
                link = clean_text(item.findtext("link"))
                pub_date = clean_text(item.findtext("pubDate"))
                if title and link:
                    items.append((title, link, pub_date))

            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title = clean_text(entry.findtext("{http://www.w3.org/2005/Atom}title"))
                link = ""
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.get("href", "")
                pub_date = clean_text(entry.findtext("{http://www.w3.org/2005/Atom}updated") or entry.findtext("{http://www.w3.org/2005/Atom}published"))
                if title and link:
                    items.append((title, link, pub_date))
        except Exception:
            pass

    # Portale USR Liguria: tabella con un link "interpello.php?id=N" per riga.
    if not items and "interpello.php" in lower_content:
        for row in re.findall(r'<tr\b.*?</tr>', html_content, re.I | re.S):
            m = re.search(r'href=["\']([^"\']*interpello\.php[^"\']*)["\']', row, re.I)
            if m:
                txt = clean_text(row)
                if len(txt) >= 10:
                    items.append(("Interpello " + txt[:140], urljoin(url, m.group(1)), ""))

    # Pagine che non sono feed: cerca i link agli avvisi nel corpo della pagina (senza menu né piè di pagina).
    # Se il feed ha già fornito gli avvisi, i link dentro le descrizioni non si contano.
    if not items:
        body_html = strip_chrome(html_content)
        for href, txt in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body_html, re.I | re.S):
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            title = clean_text(txt)
            if len(title) >= 15 and NOTICE_LINK_RE.search(title):
                full_url = urljoin(url, href)
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', full_url)
                pub_date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else ""
                items.append((title, full_url, pub_date_str))

    results = []
    seen_links = set()
    for title, link, pub_date in items:
        if link in seen_links or link in known:
            continue
        seen_links.add(link)

        if is_not_interpello(title):          # es. "Bollettino nomine": non è un interpello
            continue
        rss_pub = parse_date(pub_date)
        info = fetch_page_details(link, rss_pub)
        if info is None:
            info = {"text": "", "post_type": "Non specificato", "published": rss_pub or "",
                    "deadline": None, "doc_url": "", "email": ""}
        target = detect_target(title, info["text"])
        cdc = detect_cdc(title, info["text"])
        post_type = info["post_type"]
        published = info["published"] or ""   # niente più "oggi" quando la data non si trova

        title_lower = title.lower()
        if post_type == "Non specificato" or post_type == "Posto Ordinario / Altro":
            if "sostegno" in title_lower:
                post_type = "Posto di Sostegno"
            elif "spezzone" in title_lower:
                post_type = "Spezzone Orario"

        results.append((title, link, region, source_name, target, published, info["deadline"], cdc, post_type,
                        info["doc_url"], info["email"]))
    log_source(source_name, ok=True, found=len(items), new=len(results))
    return results, True


# ----------------------------------------------------------------------------
# Formattazione
# ----------------------------------------------------------------------------
def to_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").date()
    except Exception:
        return None


def fmt_date(iso):
    d = to_date(iso)
    return f"{d.day} {MESI[d.month - 1]} {d.year}" if d else (iso or "—")


def fmt_short(d):
    return f"{d.day} {MESI[d.month - 1]}"


def deadline_info(deadline):
    """(testo, colore sfondo, colore testo, icona) del badge di scadenza."""
    d = to_date(deadline)
    if not d:
        return ("Scadenza non indicata", ft.Colors.SURFACE_CONTAINER_HIGHEST, ft.Colors.ON_SURFACE_VARIANT,
                ft.Icons.SCHEDULE_ROUNDED)
    days = (d - date.today()).days
    if days < 0:
        return (f"Scaduto il {fmt_short(d)}", ft.Colors.SURFACE_CONTAINER_HIGHEST, ft.Colors.OUTLINE,
                ft.Icons.EVENT_BUSY_ROUNDED)
    if days == 0:
        return ("Scade oggi", ft.Colors.ERROR_CONTAINER, ft.Colors.ON_ERROR_CONTAINER,
                ft.Icons.TIMER_ROUNDED)
    if days == 1:
        return ("Scade domani", ft.Colors.ERROR_CONTAINER, ft.Colors.ON_ERROR_CONTAINER,
                ft.Icons.TIMER_ROUNDED)
    if days <= 3:
        return (f"Scade tra {days} giorni", ft.Colors.ERROR_CONTAINER, ft.Colors.ON_ERROR_CONTAINER,
                ft.Icons.TIMER_ROUNDED)
    return (f"Scade il {fmt_short(d)}", ft.Colors.TERTIARY_CONTAINER, ft.Colors.ON_TERTIARY_CONTAINER,
            ft.Icons.EVENT_AVAILABLE_ROUNDED)


def is_new(published):
    d = to_date(published)
    return bool(d) and 0 <= (date.today() - d).days <= 2


STATUS_COLORS = {"active": "#16A363", "soon": "#E8590C", "expired": "#9CA3AF", "unknown": "#6B7280"}


def status_of(deadline):
    """'active' | 'soon' | 'expired' | 'unknown' in base alla scadenza."""
    d = to_date(deadline)
    if not d:
        return "unknown"
    days = (d - date.today()).days
    if days < 0:
        return "expired"
    return "soon" if days <= SOON_DAYS else "active"


def parse_classes(raw):
    """'a028, A022 adss' -> ['A028', 'A022', 'ADSS'] (senza duplicati)."""
    out = []
    for token in re.split(r"[\s,;]+", (raw or "").upper()):
        token = token.strip()
        if token and token not in out:
            out.append(token)
    return out


def matches_classes(title, cdc, classes):
    if not classes:
        return False
    t = (title or "").upper()
    codes = [x.strip() for x in (cdc or "").upper().split(",")]
    return any(c in codes or re.search(rf"\b{re.escape(c)}\b", t) for c in classes)


# ----------------------------------------------------------------------------
# «Dove mi conviene fare le GPS?»: confronto con i bollettini di nomina
# ----------------------------------------------------------------------------
# I dati stanno in assets/gps_data.json (creato con tools/gps/build_gps_data.py dai bollettini di nomina
# GPS pubblicati dagli Uffici scolastici) e contengono SOLO dati aggregati, mai nomi. Formato:
#   {"anno": "2026/27", "aggiornato": "2026-08-29", "bollettino": "1", "fonte": "...",
#    "province": {"Pescara": {"regione": "Abruzzo",
#        "classi": {"A011:I": {"n": 12, "min": 107.5, "max": 197.5, "pos": 24}}}}}
# n = nomine, min/max = punteggio più basso/più alto nominato, pos = posizione più bassa raggiunta.
GPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "gps_data.json")
GPS_FASCE = {"I": "I fascia", "II": "II fascia"}
# Riserva per chi ha fatto il servizio civile: al massimo il 15% dei posti di quel turno, per classe.
# L'algoritmo scorre la graduatoria e «salta» ai riservisti solo finché la quota non è raggiunta, quindi i
# nominati con la riserva sono al massimo il 15% e hanno i punteggi più bassi. Nei bollettini non si capisce
# chi sono (colonne oscurate): la soglia vera sta tra il punteggio dell'ultimo nominato (minima) e quello
# che resta togliendo il 15% dei punteggi più bassi (sicura).
GPS_RISERVA = 0.15


def load_gps_data(path=GPS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("province"), dict) and data["province"]:
            return data
    except (OSError, ValueError):
        pass
    return None


def parse_score(text):
    """'85,5' o '85.5' -> 85.5; None se non è un punteggio plausibile."""
    try:
        value = float(str(text).strip().replace(",", "."))
    except ValueError:
        return None
    return value if 0 <= value <= 1000 else None


def fmt_score(value):
    """107.5 -> '107,5'; 98.0 -> '98'."""
    return f"{value:g}".replace(".", ",")


def gps_reserved_tail(ordered, quota):
    """Riservisti riconoscibili da un salto di posizione: i chiamati si seguono in ordine di posizione, quindi uno che
    arriva dopo un salto grande (es. dalla 20ª alla 80ª) è quasi certamente entrato dalla riserva.
    Restituisce da quale indice (in ordine di posizione) i chiamati sono riservisti, o None se non c'è un salto
    credibile. La coda tagliata non può superare la quota del 15%."""
    by_pos = sorted(ordered, key=lambda x: x[1])
    if quota < 1 or len(by_pos) < 3:
        return None, by_pos
    gaps = sorted(by_pos[i][1] - by_pos[i - 1][1] for i in range(1, len(by_pos)))
    median = gaps[len(gaps) // 2]
    jump = max(20, 5 * max(1, median))
    for j in range(1, len(by_pos)):
        if by_pos[j][1] - by_pos[j - 1][1] > jump and len(by_pos) - j <= quota:
            return j, by_pos
    return None, by_pos


def gps_threshold(entry, riserva=0.0, totals=None):
    """(soglia, posizione, nomine, escluse, minima, rilevata).
    La riserva del 15% si calcola sul totale dei chiamati della classe in quel bollettino (tutte le fasce insieme,
    `totals` = {turno: chiamati}), arrotondato per difetto: 20 chiamati -> 3 posti riservati.
    Se tra i chiamati c'è un salto di posizione (es. dalla 20ª alla 80ª) chi sta dopo il salto è un riservista
    (`rilevata` = True) e si toglie quello; altrimenti non si sa chi sono e per prudenza si tolgono, in quel turno,
    i punteggi più bassi della fascia (mai tutti).
    soglia = punteggio dell'ultimo nominato rimasto; con più turni vale il più basso raggiunto.
    minima = punteggio dell'ultimo nominato in assoluto. Senza elenco dei punteggi soglia = minima."""
    n = int(entry["n"])
    minima = float(entry["min"])
    turns = entry.get("t") or ([{"b": "1", "s": entry["s"]}] if entry.get("s") else [])
    if not turns or riserva <= 0:
        return minima, int(entry.get("pos", 0)), n, 0, minima, False
    pct = int(round(riserva * 100))
    best, escluse, rilevata = None, 0, False
    for t in turns:
        ordered = sorted(t["s"], key=lambda x: (-x[0], x[1]))
        total = (totals or {}).get(t.get("b"), len(ordered))
        quota = min(total * pct // 100, len(ordered) - 1)   # interi: nessun errore di arrotondamento
        cut, by_pos = gps_reserved_tail(ordered, quota)
        if cut is not None:
            kept = sorted(by_pos[:cut], key=lambda x: (-x[0], x[1]))
            rilevata = True
        else:
            kept = ordered[:len(ordered) - quota]
        escluse += len(ordered) - len(kept)
        last = kept[-1]
        if best is None or last[0] < best[0]:
            best = last
    return float(best[0]), int(best[1]), n, escluse, minima, rilevata


def gps_rank(data, cdc, fascia, score, region="", riserva=0.0, tipo="GPS"):
    """Confronta il punteggio con quello dell'ultimo nominato di ogni provincia.
    esito: "si" (ci saresti anche con la riserva piena), "forse" (dipende da quanti riservisti sono entrati),
    "no". Prima i "si" (margine maggiore per primi), poi i "forse", poi i "no" (i più vicini per primi)."""
    cdc = (cdc or "").strip().upper()
    if tipo == "GUI" and cdc.startswith("AD"):
        cdc += "#GUI"              # sostegno: la graduatoria GUI (incrocio) è separata dalla GPS
    key = f"{cdc}:{fascia}"
    rows = []
    for prov, info in data.get("province", {}).items():
        reg = info.get("regione", "")
        if region and reg != region:
            continue
        classi = info.get("classi", {})
        entry = classi.get(key)
        if not entry or not entry.get("n"):
            continue
        # chiamati della classe per bollettino, con tutte le fasce: su questo totale si calcola il 15%
        totals = {}
        for f in GPS_FASCE:
            for t in (classi.get(f"{cdc}:{f}") or {}).get("t", []):
                totals[t.get("b")] = totals.get(t.get("b"), 0) + len(t["s"])
        soglia, ultima, n, escluse, minima, rilevata = gps_threshold(entry, riserva, totals)
        chiamati = sum(totals.values())
        margin = round(score - soglia, 3)
        esito = "si" if margin >= 0 else ("forse" if score >= minima else "no")
        turni = [(t.get("b"), min(sc for sc, _ in t["s"])) for t in entry.get("t", []) if t.get("s")]
        rows.append({"provincia": prov, "regione": reg, "soglia": soglia, "minima": minima, "turni": turni, "chiamati": chiamati,
                     "massimo": float(entry["max"]), "nomine": n, "escluse": escluse, "ultima": ultima, "rilevata": rilevata,
                     "margine": margin, "mancano": round(max(0.0, minima - score), 3),
                     "esito": esito, "ok": esito == "si"})
    order = {"si": 0, "forse": 1, "no": 2}
    rows.sort(key=lambda r: (order[r["esito"]], -r["margine"], -r["nomine"], r["provincia"]))
    return rows


# Punteggio GPS: regole dell'OM 27/2026 come indicate dall'utente (titolo d'accesso, titoli aggiuntivi, servizio).
GPS_TITOLI_EXTRA = [("dott", "Dottorato di ricerca", 14), ("asn", "Abilitazione Scientifica Nazionale", 15),
                    ("assegni", "Assegni di ricerca", 13), ("sost", "Specializzazione sul sostegno", 9)]
GPS_LINGUE = {"": 0, "B2": 3, "C1": 4, "C2": 6}
GPS_MASTER_MAX = 3
GPS_INFORMATICHE_MAX = 4
GPS_SERVIZIO = [(16, 45, 2), (46, 75, 4), (76, 105, 6), (106, 135, 8), (136, 165, 10), (166, 10 ** 6, 12)]


def gps_points_access(voto, lode=False):
    """Titolo di accesso: fino a 76/110 sono 12 punti, poi +0,50 per ogni punto sopra 76 (110 = 29); la lode dà +4."""
    if voto is None or voto < 1:
        return 0.0
    pts = 12.0 if voto <= 76 else 12.0 + (min(voto, 110) - 76) * 0.5
    if lode and voto >= 110:
        pts += 4
    return pts


# Abilitazione dei percorsi da 30/60 CFU (DPCM 4 agosto 2023), prima fascia: 24 punti di base (non per gli ITP della
# tabella B) più i punti del voto della prova finale (in decimi).
GPS_ABIL_VOTI = [(10.0, 12), (9.5, 11), (9.0, 9), (8.5, 8), (8.0, 7), (7.5, 6), (7.0, 5)]
GPS_ABIL_BASE = 24


def gps_points_abil(voto, itp=False):
    """Punti dell'abilitazione 60 CFU: voto in decimi (7-10, a mezzi punti) -> base 24 + punti del voto."""
    if voto is None:
        return 0.0
    pts = dict(GPS_ABIL_VOTI).get(round(float(voto) * 2) / 2)
    if pts is None:
        return 0.0
    return float(pts + (0 if itp else GPS_ABIL_BASE))


def gps_points_service(days, specific=True):
    """Un anno scolastico: servizio specifico 2-12 punti in base ai giorni, aspecifico la metà (massimo 6)."""
    for lo, hi, pts in GPS_SERVIZIO:
        if lo <= days <= hi:
            return float(pts) if specific else pts / 2
    return 0.0


def _place_slug(text):
    import unicodedata
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\b(e|di|del|della|d)\b", " ", t)
    return re.sub(r"[^a-z]", "", t)


def source_provinces(source, province_names):
    """Province GPS a cui corrisponde una fonte («USP Chieti e Pescara» -> Chieti, Pescara)."""
    name = re.sub(r"^(USP|AT|UST|Ambito territoriale)\s+", "", source or "", flags=re.I)
    slug = _place_slug(name)
    return [p for p in province_names if len(_place_slug(p)) >= 4 and _place_slug(p) in slug]


def gps_stats(data, cdc):
    """Nomine di una classe di concorso in tutta Italia: totali, per fascia e le province con più chiamati."""
    cdc = (cdc or "").strip().upper()
    per_fascia = {f: 0 for f in GPS_FASCE}
    per_prov = {}
    for prov, info in data.get("province", {}).items():
        for f in GPS_FASCE:
            e = info.get("classi", {}).get(f"{cdc}:{f}")
            if e and e.get("n"):
                per_fascia[f] += int(e["n"])
                per_prov[prov] = per_prov.get(prov, 0) + int(e["n"])
    top = sorted(per_prov.items(), key=lambda x: (-x[1], x[0]))[:5]
    return {"totale": sum(per_fascia.values()), "fasce": per_fascia, "province": len(per_prov), "top": top}


def build_mailto(email, title, cdc, name, phone):
    from urllib.parse import quote
    subject = f"Disponibilità supplenza {('classe ' + cdc) if cdc else ''} - {name}".replace("  ", " ").strip(" -")
    body = (
        "Gentile Dirigente Scolastico,\n\n"
        f"con riferimento all'interpello \"{title}\", comunico la mia disponibilità "
        "ad accettare la supplenza.\n\n"
        f"{name}\n{('Tel. ' + phone) if phone else ''}\n"
    )
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


# ----------------------------------------------------------------------------
# Interfaccia
# ----------------------------------------------------------------------------
def build(page: ft.Page, raw_prefs=None):
    try:
        page.title = "Interpelli Scuola"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.theme = ft.Theme(color_scheme_seed=BRAND_LIGHT, use_material3=True)
        page.dark_theme = ft.Theme(color_scheme_seed=BRAND_LIGHT, use_material3=True)
        page.padding = 0
        page.spacing = 0
        try:
            page.window.width = 420
            page.window.height = 820
        except Exception:
            pass

        init_db()

        state = {"profile": "", "region": "", "status": "", "sort": "new", "shown": 0, "refreshing": False}
        timers = {"search": None}

        # ---- Preferenze dell'utente (classi di concorso, dati per le candidature)
        prefs = {"classes": [], "name": "", "phone": "", "gps_class": "", "gps_score": "",
                 "fav": [], "applied": [], "profiles": [], "theme": "", "calc": {},
                 "sources": [], "src_status": {}}

        store = ft.SharedPreferences()

        def show_dialog(d):
            try:
                page.show_dialog(d)
            except RuntimeError:             # era già nella pila: la riapro
                d.open = True
                d.update()

        def close_dialog(d):
            d.open = False
            try:
                d.update()
            except Exception:
                page.update()

        def load_prefs():
            try:
                raw = raw_prefs
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    classes = data.get("classes", [])
                    if isinstance(classes, list):
                        prefs["classes"] = [c for c in classes if isinstance(c, str)]
                    for key in ("fav", "applied"):
                        if isinstance(data.get(key), list):
                            prefs[key] = [u for u in data[key] if isinstance(u, str)][-300:]
                    if isinstance(data.get("profiles"), list):
                        prefs["profiles"] = [p for p in data["profiles"] if isinstance(p, dict)
                                             and isinstance(p.get("c"), str) and isinstance(p.get("s"), str)][:8]
                    if isinstance(data.get("calc"), dict):
                        prefs["calc"] = data["calc"]
                    if isinstance(data.get("sources"), list):
                        prefs["sources"] = [{"n": str(x["n"])[:40], "u": str(x["u"])[:300]} for x in data["sources"]
                                            if isinstance(x, dict) and x.get("n") and x.get("u")][:30]
                    if isinstance(data.get("src_status"), dict):
                        prefs["src_status"] = {k: v for k, v in data["src_status"].items()
                                               if isinstance(k, str) and isinstance(v, dict)}
                    if data.get("theme") in ("light", "dark"):
                        prefs["theme"] = data["theme"]
                    for key in ("name", "phone", "gps_class", "gps_score"):
                        if isinstance(data.get(key), str):
                            prefs[key] = data[key]
            except Exception:
                pass

        def save_prefs():
            try:
                page.run_task(store.set, "prefs", json.dumps(prefs))
            except Exception:
                pass

        load_prefs()

        def apply_theme():
            page.theme_mode = {"light": ft.ThemeMode.LIGHT, "dark": ft.ThemeMode.DARK}.get(
                prefs["theme"], ft.ThemeMode.SYSTEM)

        apply_theme()

        # ---- Intestazione con logo e ricerca -------------------------------
        # I tre pulsanti stanno nella riga dei filtri, accanto a «Per me» (più comodi da raggiungere).
        def tool_button(icon, tooltip, visible=True):
            return ft.IconButton(
                icon=icon,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                icon_size=22,
                tooltip=tooltip,
                visible=visible,
                style=ft.ButtonStyle(bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
            )

        settings_button = tool_button(ft.Icons.TUNE_ROUNDED, "Le mie classi e i miei dati")
        refresh_button = tool_button(ft.Icons.SYNC_ROUNDED, "Cerca nuovi interpelli")
        reset_button = tool_button(ft.Icons.FILTER_ALT_OFF_ROUNDED, "Azzera i filtri", visible=False)
        sources_button = tool_button(ft.Icons.RSS_FEED_ROUNDED, "Stato delle fonti")

        clear_button = ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, icon_size=18, visible=False,
                                     icon_color="#6B7280")

        search_input = ft.TextField(
            hint_text="Cerca classe di concorso, ruolo, ufficio…",
            hint_style=ft.TextStyle(color="#6B7280", size=14),
            text_style=ft.TextStyle(color="#111827", size=14),
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            suffix=clear_button,
            filled=True,
            fill_color=ft.Colors.with_opacity(0.96, ft.Colors.WHITE),
            border=ft.NoInputBorder(),
            border_radius=16,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=14),
            cursor_color=BRAND_LIGHT,
        )

        menu_button = ft.IconButton(icon=ft.Icons.MENU_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=26,
                                    tooltip="Menù", on_click=lambda e: open_menu(e),
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE)))
        refresh_button.icon_color = ft.Colors.WHITE
        refresh_button.style = ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE))

        header = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[BRAND_DARK, BRAND_LIGHT],
            ),
            padding=ft.Padding.only(left=18, right=14, top=22, bottom=18),
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            menu_button,
                            ft.Image(src="logo.png", width=42, height=42, border_radius=12),
                            ft.Column(
                                expand=True, spacing=0,
                                controls=[
                                    ft.Text("Interpelli Scuola", size=21, weight=ft.FontWeight.W_800,
                                            color=ft.Colors.WHITE),
                                    ft.Text("Supplenze in tutta Italia, in un tocco",
                                            size=12, color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)),
                                ],
                            ),
                            refresh_button,
                        ],
                    ),
                    search_input,
                ],
            ),
        )

        # ---- Filtri ---------------------------------------------------------
        pills = {}

        # Pulsanti-filtro: stesso tipo di controllo (ElevatedButton) già usato
        # dalla versione originale, quindi sicuro su tutti i dispositivi.
        def make_pill(key, label, icon):
            btn = ft.Button(
                content=label,
                icon=icon,
                on_click=lambda e, k=key: set_profile(k),
            )
            pills[key] = btn
            return btn

        def paint_pills():
            for key, btn in pills.items():
                active = state["profile"] == key
                btn.style = ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=20),
                    bgcolor=ft.Colors.PRIMARY if active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    color=ft.Colors.ON_PRIMARY if active else ft.Colors.ON_SURFACE_VARIANT,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    elevation=0,
                )
            saved_tools.visible = state["profile"] == "SAVED"

        pills_row = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                make_pill("", "Tutti", None),
                make_pill("DOCENTI", "Docenti", None),
                make_pill("ATA", "ATA", None),
                make_pill("ME", "Per me", ft.Icons.STAR_ROUNDED),
                make_pill("SAVED", "Salvati", ft.Icons.BOOKMARK_ROUNDED),
                reset_button,
            ],
        )

        region_options = [ft.DropdownOption(key="", text="Tutta Italia")]
        for reg in sorted(SOURCES.keys()):
            region_options.append(ft.DropdownOption(key=reg, text=reg))

        # Stessa configurazione del Dropdown originale (che funzionava),
        # direttamente in colonna e a larghezza piena.
        region_dropdown = ft.Dropdown(
            label="Regione",
            options=region_options,
            value="",
            expand=True,
            dense=True,
            border_radius=14,
            filled=True,
            border_color=ft.Colors.TRANSPARENT,
        )

        status_dropdown = ft.Dropdown(
            label="Stato",
            expand=True,
            dense=True,
            options=[
                ft.DropdownOption(key="", text="Tutti"),
                ft.DropdownOption(key="active", text="Attivi"),
                ft.DropdownOption(key="soon", text="In scadenza"),
                ft.DropdownOption(key="expired", text="Scaduti"),
            ],
            value="",
            border_radius=14,
            filled=True,
            border_color=ft.Colors.TRANSPARENT,
        )

        sort_dropdown = ft.Dropdown(
            label="Ordina per", value="new", dense=True, border_radius=14, filled=True,
            border_color=ft.Colors.TRANSPARENT,
            options=[ft.DropdownOption(key="new", text="Più recenti"),
                     ft.DropdownOption(key="deadline", text="Scadenza più vicina")])

        def on_sort(e):
            state["sort"] = sort_dropdown.value or "new"
            load_results(reset=True)

        sort_dropdown.on_select = on_sort

        classes_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        gps_button = ft.Container(
            ink=True,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT, end=ft.Alignment.CENTER_RIGHT,
                colors=[BRAND_DARK, BRAND_LIGHT]),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                controls=[
                    ft.Container(
                        width=44, height=44, border_radius=14, alignment=ft.Alignment.CENTER,
                        bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
                        content=ft.Icon(ft.Icons.TRAVEL_EXPLORE_ROUNDED, color=ft.Colors.WHITE, size=26)),
                    ft.Column(expand=True, spacing=1, controls=[
                        ft.Text("Dove mi conviene fare le GPS?", size=15, weight=ft.FontWeight.W_800,
                                color=ft.Colors.WHITE),
                        ft.Text("Confronta il tuo punteggio con i bollettini di nomina di ogni provincia",
                                size=11.5, color=ft.Colors.with_opacity(0.88, ft.Colors.WHITE)),
                    ]),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=ft.Colors.WHITE, size=26),
                ],
            ),
        )

        saved_tools = ft.Row(wrap=True, spacing=0, visible=False)

        radar_button = ft.FilledTonalButton(
            content="Radar: interpelli aperti per te, provincia per provincia",
            icon=ft.Icons.RADAR_ROUNDED, expand=True, height=46)

        def saved_text():
            """Elenco degli interpelli salvati o a cui hai già risposto, da copiare o mandare a qualcuno."""
            urls = list(dict.fromkeys(prefs["fav"] + prefs["applied"]))
            if not urls:
                return ""
            conn = db_connect()
            found = {}
            for u in urls:
                row = conn.execute("SELECT title, deadline FROM interpelli WHERE url = ?", (u,)).fetchone()
                if row:
                    found[u] = row
            conn.close()
            lines = []
            for u in urls:
                if u not in found:
                    continue
                title, deadline = found[u]
                tag = " [candidatura inviata]" if u in prefs["applied"] else ""
                lines.append(f"• {title}{tag}\n  Scadenza: {fmt_date(deadline) if deadline else 'non indicata'}\n  {u}")
            return "I miei interpelli\n\n" + "\n\n".join(lines)

        def saved_copy(e=None):
            text = saved_text()
            if not text:
                notify("Non hai ancora salvato nessun interpello.")
                return
            try:
                page.run_task(clipboard.set, text)
                notify("Elenco copiato.")
            except Exception:
                notify("Copia non riuscita.")

        def saved_whatsapp(e=None):
            text = saved_text()
            if not text:
                notify("Non hai ancora salvato nessun interpello.")
                return
            open_url("https://wa.me/?text=" + quote(text))

        saved_tools.controls = [
            ft.TextButton(content="Copia elenco", icon=ft.Icons.CONTENT_COPY_ROUNDED, on_click=saved_copy),
            ft.TextButton(content="Invia su WhatsApp", icon=ft.Icons.SHARE_ROUNDED, on_click=saved_whatsapp)]

        def shortcut(icon, label, handler):
            return ft.Container(
                expand=True, ink=True, border_radius=18, height=78, on_click=handler,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                content=ft.Column(spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(icon, size=26, color=BRAND_LIGHT),
                    ft.Text(label, size=11.5, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER)]))

        shortcuts_row = ft.Row(spacing=10, controls=[
            shortcut(ft.Icons.TRAVEL_EXPLORE_ROUNDED, "Dove fare\nle GPS", lambda e: open_menu_item(open_gps)),
            shortcut(ft.Icons.RADAR_ROUNDED, "Radar\nopportunità", lambda e: open_menu_item(open_radar)),
            shortcut(ft.Icons.CALCULATE_ROUNDED, "Calcola\npunteggio", lambda e: open_menu_item(lambda: open_calc(from_home=True))),
            shortcut(ft.Icons.GRID_VIEW_ROUNDED, "Tutte le\nfunzioni", lambda e: open_menu(e)),
        ])

        stat_texts = {k: ft.Text("–", size=24, weight=ft.FontWeight.W_800, color=c)
                      for k, c in (("open", BRAND_LIGHT), ("soon", "#E8590C"), ("mine", GREEN))}

        def stat_tile(key, label, handler):
            return ft.Container(
                expand=True, ink=True, border_radius=18, padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                on_click=handler, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                content=ft.Column(spacing=0, controls=[
                    stat_texts[key], ft.Text(label, size=11.5, color=ft.Colors.ON_SURFACE_VARIANT)]))

        def stat_filter(status):
            state["profile"] = ""
            state["status"] = status
            status_dropdown.value = status
            paint_pills()
            load_results(reset=True)

        stats_row = ft.Row(spacing=10, controls=[
            stat_tile("soon", "In scadenza", lambda e: stat_filter("soon")),
            stat_tile("mine", "Per te", lambda e: set_profile("ME")),
        ])

        def paint_stats():
            try:
                today_s = date.today().strftime("%Y-%m-%d")
                soon_s = (date.today() + timedelta(days=SOON_DAYS)).strftime("%Y-%m-%d")
                conn = db_connect()
                rows = conn.execute("SELECT title, cdc, deadline FROM interpelli "
                                    "WHERE deadline IS NOT NULL AND deadline >= ?", (today_s,)).fetchall()
                conn.close()
                stat_texts["open"].value = str(len(rows))
                stat_texts["soon"].value = str(sum(1 for r in rows if r[2] <= soon_s))
                stat_texts["mine"].value = (str(sum(1 for r in rows if matches_classes(r[0], r[1], prefs["classes"])))
                                            if prefs["classes"] else "–")
            except Exception:
                pass

        filters_panel = ft.Column(spacing=10, visible=False, controls=[
            ft.Row(spacing=10, controls=[region_dropdown, status_dropdown]), sort_dropdown])
        filters_toggle = ft.TextButton(content="Filtri", icon=ft.Icons.TUNE_ROUNDED)

        def toggle_filters(e=None):
            filters_panel.visible = not filters_panel.visible
            filters_toggle.icon = (ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if filters_panel.visible
                                   else ft.Icons.TUNE_ROUNDED)
            page.update()

        filters_toggle.on_click = toggle_filters

        filters = ft.Container(
            padding=ft.Padding.only(left=16, right=16, top=14, bottom=4),
            content=ft.Column(
                spacing=10,
                controls=[
                    shortcuts_row,
                    stats_row,
                    ft.Row(spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=[ft.Container(expand=True, content=pills_row), filters_toggle]),
                    classes_text,
                    saved_tools,
                    filters_panel,
                ],
            ),
        )

        # ---- Stato / progresso ---------------------------------------------
        status_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.W_500,
                              expand=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, bar_height=3, border_radius=3)
        status_row = ft.Container(
            padding=ft.Padding.symmetric(horizontal=18, vertical=6),
            content=ft.Column(spacing=6, controls=[progress_bar, ft.Row([status_text])]),
        )

        # ---- Lista risultati -----------------------------------------------
        results = ft.ListView(expand=True, spacing=10,
                              padding=ft.Padding.only(left=16, right=16, top=4, bottom=28))

        more_button = ft.Container(
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(top=6, bottom=6),
            content=ft.FilledTonalButton(
                content="Mostra altri", icon=ft.Icons.EXPAND_MORE_ROUNDED,
                on_click=lambda e: load_results(reset=False),
            ),
        )

        def empty_state(db_empty):
            if state["refreshing"]:
                return ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.only(top=48, left=24, right=24),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                        controls=[
                            ft.ProgressRing(width=34, height=34, stroke_width=4),
                            ft.Text("Sto cercando gli interpelli…", size=16, weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text("I risultati compaiono qui man mano che li trovo.", size=13,
                                    color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                        ],
                    ),
                )
            if db_empty:
                title, sub = "Nessun interpello scaricato", "Tocca il pulsante per scaricare gli avvisi di tutta Italia."
                action = ft.FilledButton("Scarica interpelli", icon=ft.Icons.CLOUD_DOWNLOAD_ROUNDED,
                                         on_click=lambda e: refresh())
            else:
                title, sub = "Nessun risultato", "Prova a cambiare ricerca o filtri."
                action = ft.TextButton("Azzera filtri", on_click=lambda e: reset_filters())
            return ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=48, left=24, right=24),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=56, color=ft.Colors.OUTLINE),
                        ft.Text(title, size=16, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
                        ft.Text(sub, size=13, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                        action,
                    ],
                ),
            )

        def badge(text, bgcolor, color, icon=None):
            row = []
            if icon:
                row.append(ft.Icon(icon, size=13, color=color))
            row.append(ft.Text(text, size=11, weight=ft.FontWeight.W_700, color=color))
            return ft.Container(
                content=ft.Row(row, spacing=4, tight=True),
                bgcolor=bgcolor,
                padding=ft.Padding.symmetric(horizontal=9, vertical=4),
                border_radius=8,
            )

        def meta_row(icon, text):
            return ft.Row(
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(icon, size=14, color=ft.Colors.OUTLINE),
                    ft.Text(text, size=12, color=ft.Colors.ON_SURFACE_VARIANT, expand=True,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ],
            )

        launcher = ft.UrlLauncher()

        def open_url(url):
            try:
                page.run_task(launcher.launch_url, url)
            except Exception:
                pass

        def build_card(row):
            title, url, region, source, target, published, deadline, cdc, post_type, doc_url, email, verified = row
            is_ata = target == "ATA"
            d_text, d_bg, d_fg, d_icon = deadline_info(deadline)
            status = status_of(deadline)
            mine = matches_classes(title, cdc, prefs["classes"])

            chips = [
                badge("ATA" if is_ata else "Docenti",
                      ft.Colors.SECONDARY_CONTAINER if is_ata else ft.Colors.PRIMARY_CONTAINER,
                      ft.Colors.ON_SECONDARY_CONTAINER if is_ata else ft.Colors.ON_PRIMARY_CONTAINER,
                      ft.Icons.WORK_ROUNDED if is_ata else ft.Icons.SCHOOL_ROUNDED),
            ]
            for code in [c.strip() for c in (cdc or "").split(",") if c.strip()]:
                chips.append(badge(cdc_label(code), ft.Colors.SURFACE_CONTAINER_HIGHEST, ft.Colors.ON_SURFACE_VARIANT))
            if mine:
                chips.append(badge("PER TE", GOLD, "#3B2A00", ft.Icons.STAR_ROUNDED))
            if url in prefs["applied"]:
                chips.append(badge("CANDIDATO", GREEN, ft.Colors.WHITE, ft.Icons.CHECK_ROUNDED))
            if is_new(published):
                chips.append(badge("NUOVO", GREEN, ft.Colors.WHITE))
            if verified:
                chips.append(badge("Date verificate", ft.Colors.SURFACE_CONTAINER_HIGHEST, GREEN, ft.Icons.VERIFIED_ROUNDED))

            body = [
                ft.Row(chips, spacing=6, wrap=True, run_spacing=6),
                ft.Text(title, size=14, weight=ft.FontWeight.W_600, max_lines=4,
                        overflow=ft.TextOverflow.ELLIPSIS),
                meta_row(ft.Icons.PLACE_ROUNDED, f"{source} · {region}"),
                meta_row(ft.Icons.CALENDAR_TODAY_ROUNDED,
                         f"Pubblicato il {fmt_date(published)}" if published else "Data di pubblicazione non indicata"),
            ]
            if post_type and post_type != "Non specificato":
                body.append(meta_row(ft.Icons.WORK_OUTLINE_ROUNDED, post_type))
            body.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        badge(d_text, d_bg, d_fg, d_icon),
                        ft.Row(
                            spacing=2, tight=True,
                            controls=[
                                ft.Text("Controlla e apri", size=12, weight=ft.FontWeight.W_700,
                                        color=ft.Colors.PRIMARY),
                                ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED, size=15, color=ft.Colors.PRIMARY),
                            ],
                        ),
                    ],
                )
            )

            # Azioni come sul sito: documento originale e candidatura via email
            actions = []
            if doc_url:
                actions.append(ft.TextButton(content="Documento", icon=ft.Icons.DOWNLOAD_ROUNDED, url=doc_url))
            if email and status != "expired":
                mailto = build_mailto(email, title, cdc, prefs["name"] or "Candidato", prefs["phone"])
                actions.append(ft.TextButton(content="Candidati", icon=ft.Icons.MAIL_OUTLINE_ROUNDED, url=mailto))
            def toggle(key, btn, on_icon, off_icon, color):
                lst = prefs[key]
                if url in lst:
                    lst.remove(url)
                else:
                    lst.append(url)
                    del lst[:-300]
                on = url in lst
                btn.icon = on_icon if on else off_icon
                btn.icon_color = color if on else ft.Colors.OUTLINE
                save_prefs()
                btn.update()

            def mark_button(key, on_icon, off_icon, color, tip):
                on = url in prefs[key]
                btn = ft.IconButton(icon=on_icon if on else off_icon, icon_size=22, tooltip=tip,
                                    icon_color=color if on else ft.Colors.OUTLINE)
                btn.on_click = lambda e, b=btn: toggle(key, b, on_icon, off_icon, color)
                return btn

            def share(e):
                open_url("https://wa.me/?text=" + quote(f"{title}\n{url}"))

            actions += [
                mark_button("fav", ft.Icons.BOOKMARK_ROUNDED, ft.Icons.BOOKMARK_BORDER_ROUNDED, GOLD, "Salva"),
                mark_button("applied", ft.Icons.CHECK_CIRCLE_ROUNDED, ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, GREEN,
                            "Candidatura inviata"),
                ft.IconButton(icon=ft.Icons.SHARE_ROUNDED, icon_size=20, icon_color=ft.Colors.OUTLINE,
                              tooltip="Condividi su WhatsApp", on_click=share),
            ]
            body.append(ft.Row(actions, spacing=2, wrap=True, run_spacing=0))

            return ft.Container(
                content=ft.Column(body, spacing=8),
                padding=ft.Padding.only(left=16, right=14, top=14, bottom=12),
                border_radius=20,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1.5, STATUS_COLORS[status]) if status in ("active", "soon")
                else ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                shadow=ft.BoxShadow(blur_radius=10, offset=ft.Offset(0, 2),
                                    color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
                opacity=0.7 if status == "expired" else 1,
                ink=True,
                data=url,
                on_click=lambda e, u=url: open_interpello(u),
            )

        # ---- Apertura di un interpello: rilegge le date sulla pagina ----------
        detail_title = ft.Text("", size=15, weight=ft.FontWeight.W_700, max_lines=4,
                               overflow=ft.TextOverflow.ELLIPSIS)
        detail_body = ft.Column(tight=True, spacing=10)
        detail_open_btn = ft.FilledButton("Apri avviso", icon=ft.Icons.OPEN_IN_NEW_ROUNDED)
        detail_close_btn = ft.TextButton("Chiudi")
        detail_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Controllo dell'avviso"),
            content=ft.Column(tight=True, spacing=12, controls=[detail_title, detail_body]),
            actions=[detail_close_btn, detail_open_btn],
        )

        def close_detail(e=None):
            close_dialog(detail_dlg)

        def go_to_notice(url):
            close_detail()
            open_url(url)

        detail_close_btn.on_click = close_detail

        def date_line(icon, label, value_text, note, color=None):
            col = [ft.Text(value_text, size=14, weight=ft.FontWeight.W_700, color=color)]
            if note:
                col.append(ft.Text(note, size=11, color=ft.Colors.ON_SURFACE_VARIANT, italic=True))
            return ft.Row(
                spacing=10, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(icon, size=20, color=ft.Colors.PRIMARY),
                    ft.Column(spacing=1, tight=True, expand=True,
                              controls=[ft.Text(label, size=11, color=ft.Colors.ON_SURFACE_VARIANT)] + col),
                ],
            )

        def replace_card(url):
            """Ricostruisce solo la scheda toccata, senza perdere la posizione nella lista."""
            try:
                conn = db_connect()
                row = conn.execute(
                    "SELECT title, url, region, source, target, published, deadline, cdc, post_type, doc_url, email, verified "
                    "FROM interpelli WHERE url = ?", (url,)).fetchone()
                conn.close()
                if not row:
                    return
                for i, ctl in enumerate(results.controls):
                    if getattr(ctl, "data", None) == url:
                        results.controls[i] = build_card(row)
                        break
            except Exception:
                pass

        def show_verification(url, row_title, stored_pub, stored_deadline, info, stored_target=None, stored_cdc=None):
            if info is None:
                detail_body.controls = [
                    date_line(ft.Icons.CALENDAR_TODAY_ROUNDED, "Pubblicazione",
                              fmt_date(stored_pub) if stored_pub else "Non indicata",
                              "Non verificata: la pagina non risponde"),
                    date_line(ft.Icons.EVENT_BUSY_ROUNDED, "Scadenza",
                              fmt_date(stored_deadline) if stored_deadline else "Non indicata",
                              "Non verificata: la pagina non risponde"),
                    ft.Text("Controlla la connessione e riprova, oppure apri l'avviso e verifica le date.",
                            size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ]
                return

            pub, deadline = info["published"], info["deadline"]
            d_text, _, _, _ = deadline_info(deadline)
            lines = [
                date_line(ft.Icons.CALENDAR_TODAY_ROUNDED, "Data di pubblicazione",
                          fmt_date(pub) if pub else "Non trovata nella pagina",
                          f"Letta da: {info['published_src']}" if pub else "Controllala nell'avviso"),
                date_line(ft.Icons.EVENT_BUSY_ROUNDED, "Scadenza per la candidatura",
                          fmt_date(deadline) if deadline else "Non trovata nella pagina",
                          f"«…{info['deadline_src']}…»" if deadline else
                          "Potrebbe essere scritta solo nell'allegato: aprilo per controllare",
                          color=STATUS_COLORS[status_of(deadline)] if deadline else None),
            ]
            if deadline:
                lines.append(ft.Text(d_text, size=12, weight=ft.FontWeight.W_600))

            # profilo e classe riletti dall'avviso (correggono l'elenco se serve)
            profile = "Personale ATA" if info.get("target") == "ATA" else "Docenti"
            cdc_txt = ", ".join(cdc_label(c.strip()) for c in (info.get("cdc") or "").split(",") if c.strip())
            note = None
            if stored_target and stored_target != info.get("target"):
                was = "Personale ATA" if stored_target == "ATA" else "Docenti"
                note = f"Corretto: nell'elenco risultava «{was}»"
            lines.append(date_line(ft.Icons.BADGE_ROUNDED, "Profilo e classe di concorso",
                                   profile + (f" · {cdc_txt}" if cdc_txt else ""), note))
            if info.get("doc_url"):
                lines.append(ft.Text("Nell'avviso è presente un allegato: se la scadenza è indicata solo lì, "
                                     "controllala nel documento.", size=11, color=ft.Colors.ON_SURFACE_VARIANT))
            detail_body.controls = lines

        def open_interpello(url):
            try:
                conn = db_connect()
                row = conn.execute("SELECT title, published, deadline, target, cdc FROM interpelli WHERE url = ?",
                                   (url,)).fetchone()
                conn.close()
            except sqlite3.Error:
                row = None
            row_title, stored_pub, stored_deadline, stored_target, stored_cdc = row if row else ("", "", None, None, None)

            detail_title.value = row_title
            detail_body.controls = [
                ft.Row(spacing=12, controls=[
                    ft.ProgressRing(width=20, height=20, stroke_width=3),
                    ft.Text("Controllo le date sulla pagina dell'avviso…", size=13),
                ])
            ]
            detail_open_btn.on_click = lambda e, u=url: go_to_notice(u)
            show_dialog(detail_dlg)

            def worker():
                info = verify_interpello(url, stored_pub or None, row_title)
                if info is not None and info.get("not_interpello"):
                    # bollettino delle nomine o simili: non è un interpello, via dall'elenco
                    try:
                        conn = db_connect()
                        conn.execute("DELETE FROM interpelli WHERE url = ?", (url,))
                        conn.commit()
                        conn.close()
                    except sqlite3.Error:
                        pass
                    results.controls[:] = [c for c in results.controls if getattr(c, "data", None) != url]
                    detail_body.controls = [ft.Text(
                        "Questo avviso non è un interpello (bollettino delle nomine): l'ho tolto dall'elenco.",
                        size=13)]
                    page.update()
                    return
                if info is not None:
                    try:
                        conn = db_connect()
                        conn.execute(
                            "UPDATE interpelli SET published = ?, deadline = ?, doc_url = ?, email = ?, "
                            "target = ?, cdc = ?, verified = 1 WHERE url = ?",
                            (info["published"], info["deadline"], info["doc_url"] or "", info["email"] or "",
                             info["target"], info["cdc"], url))
                        conn.commit()
                        conn.close()
                    except sqlite3.Error:
                        pass
                    replace_card(url)
                show_verification(url, row_title, stored_pub, stored_deadline, info, stored_target, stored_cdc)
                page.update()

            threading.Thread(target=worker, daemon=True).start()

        # ---- Query ----------------------------------------------------------
        def build_query():
            where = ["1=1"]
            params = []

            for token in state_search_tokens():
                clause = "title LIKE ? OR cdc LIKE ? OR source LIKE ? OR region LIKE ?"
                params.extend([f"%{token}%"] * 4)
                alias = CDC_SEARCH_ALIASES.get(token.lower())
                if alias:                      # cercando "motoria" trova anche la classe EEEM
                    clause += " OR cdc LIKE ?"
                    params.append(f"%{alias}%")
                where.append("(" + clause + ")")

            if state["profile"] == "ME":
                if prefs["classes"]:
                    parts = []
                    for c in prefs["classes"]:
                        parts.append("(cdc LIKE ? OR title LIKE ?)")
                        params.extend([f"%{c}%", f"%{c}%"])
                    where.append("(" + " OR ".join(parts) + ")")
                else:
                    where.append("1=0")
            elif state["profile"] == "SAVED":
                saved = list(dict.fromkeys(prefs["fav"] + prefs["applied"]))
                if saved:
                    where.append("url IN (" + ",".join("?" * len(saved)) + ")")
                    params.extend(saved)
                else:
                    where.append("1=0")
            elif state["profile"]:
                where.append("target = ?")
                params.append(state["profile"])
            if state["region"]:
                where.append("region = ?")
                params.append(state["region"])

            today = date.today()
            today_s = today.strftime("%Y-%m-%d")
            if state["status"] == "active":
                where.append("(deadline IS NULL OR deadline = '' OR deadline >= ?)")
                params.append(today_s)
            elif state["status"] == "soon":
                where.append("(deadline >= ? AND deadline <= ?)")
                params.extend([today_s, (today + timedelta(days=SOON_DAYS)).strftime("%Y-%m-%d")])
            elif state["status"] == "expired":
                where.append("(deadline IS NOT NULL AND deadline != '' AND deadline < ?)")
                params.append(today_s)
            return " AND ".join(where), params

        def order_clause():
            if state["sort"] == "deadline":
                today_s = date.today().strftime("%Y-%m-%d")      # prima i aperti per scadenza più vicina, poi senza data, poi scaduti
                return (f"CASE WHEN deadline >= '{today_s}' THEN 0 WHEN deadline IS NULL OR deadline = '' THEN 1 "
                        "ELSE 2 END, deadline ASC, published DESC, id DESC")
            return "published DESC, id DESC"

        def state_search_tokens():
            return [t for t in (search_input.value or "").strip().split() if t]

        load_lock = threading.RLock()

        def load_results(reset=True, live=False):
            """reset: riparte dall'inizio · live: ricarica quanto già mostrato (durante la ricerca) · altrimenti 'mostra altri'."""
            with load_lock:
                try:
                    if reset:
                        state["shown"] = 0
                        offset, limit = 0, PAGE_SIZE
                    elif live:
                        offset, limit = 0, max(state["shown"], PAGE_SIZE)
                    else:
                        offset, limit = state["shown"], PAGE_SIZE

                    where, params = build_query()
                    conn = db_connect()
                    total_filtered = conn.execute(f"SELECT COUNT(*) FROM interpelli WHERE {where}", params).fetchone()[0]
                    total_in_db = conn.execute("SELECT COUNT(*) FROM interpelli").fetchone()[0]
                    rows = conn.execute(
                        "SELECT title, url, region, source, target, published, deadline, cdc, post_type, doc_url, email, verified "
                        f"FROM interpelli WHERE {where} ORDER BY {order_clause()} LIMIT ? OFFSET ?",
                        params + [limit, offset],
                    ).fetchall()
                    conn.close()

                    if reset or live:
                        results.controls.clear()
                        state["shown"] = 0
                    elif results.controls and results.controls[-1] is more_button:
                        results.controls.pop()

                    for row in rows:
                        results.controls.append(build_card(row))
                    state["shown"] += len(rows)

                    if not results.controls:
                        results.controls.append(empty_state(total_in_db == 0))
                    elif state["shown"] < total_filtered:
                        results.controls.append(more_button)

                    if not state["refreshing"]:
                        if total_filtered:
                            status_text.value = f"{total_filtered} interpelli · mostrati {state['shown']}"
                        else:
                            status_text.value = ""
                    if reset and not live:
                        try:
                            page.run_task(results.scroll_to, offset=0, duration=0)
                        except Exception:
                            pass
                    update_reset_visibility()
                    paint_stats()
                    page.update()
                except Exception as ex:
                    status_text.value = f"Errore nel caricamento: {ex}"
                    page.update()

        # ---- Eventi filtri --------------------------------------------------
        def update_reset_visibility():
            reset_button.visible = bool(state["profile"] or state["region"] or state["status"]
                                        or (search_input.value or "").strip())

        reset_button.on_click = lambda e: reset_filters()

        def refresh_classes_text():
            if prefs["classes"]:
                classes_text.value = "Le mie classi: " + ", ".join(prefs["classes"])
            else:
                classes_text.value = "Apri il menù ☰ → «Le mie classi» per scegliere le tue classi"

        def set_profile(key):
            if key == "ME" and not prefs["classes"]:
                open_settings()
                return
            state["profile"] = key
            paint_pills()
            load_results(reset=True)

        def reset_filters():
            state["profile"] = ""
            state["region"] = ""
            state["status"] = ""
            search_input.value = ""
            clear_button.visible = False
            region_dropdown.value = ""
            status_dropdown.value = ""
            paint_pills()
            load_results(reset=True)

        # ---- Impostazioni: classi di concorso e dati per le candidature ----
        classes_field = ft.TextField(
            label="Classi di concorso",
            hint_text="es. A028, A022, ADSS",
            helper="Separale con virgole o spazi",
        )
        name_field = ft.TextField(label="Nome e cognome (per le candidature)")
        phone_field = ft.TextField(label="Telefono (facoltativo)")
        theme_dropdown = ft.Dropdown(
            label="Aspetto", value="",
            options=[ft.DropdownOption(key="", text="Come il telefono"),
                     ft.DropdownOption(key="light", text="Chiaro"),
                     ft.DropdownOption(key="dark", text="Scuro")])

        def close_settings(e=None):
            close_dialog(dlg)

        clipboard = ft.Clipboard()

        def copy_classes():
            text = ", ".join(parse_classes(classes_field.value))
            if not text:
                notify("Scrivi prima almeno una classe di concorso.")
                return
            try:
                page.run_task(clipboard.set, text)
                notify(f"Copiato: {text}")
            except Exception:
                notify("Copia non riuscita: seleziona e copia il testo a mano.")

        def save_settings(e=None):
            prefs["classes"] = parse_classes(classes_field.value)
            prefs["name"] = (name_field.value or "").strip()
            prefs["phone"] = (phone_field.value or "").strip()
            prefs["theme"] = theme_dropdown.value or ""
            apply_theme()
            save_prefs()
            refresh_classes_text()
            if state["profile"] == "ME" and not prefs["classes"]:
                state["profile"] = ""
                paint_pills()
            close_dialog(dlg)
            load_results(reset=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Le mie classi"),
            content=ft.Column(
                tight=True, spacing=12,
                controls=[
                    ft.Text("Servono al filtro «Per me» e alle notifiche: ricevi un avviso solo per i nuovi "
                            "interpelli di queste classi.", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    classes_field, name_field, phone_field, theme_dropdown,
                    ft.TextButton("Copia le classi per le notifiche", icon=ft.Icons.CONTENT_COPY_ROUNDED,
                                  on_click=lambda e: copy_classes()),
                    ft.Text("Per le notifiche a app chiusa incolla l'elenco nella variabile NOTIFY_CLASSES "
                            "del repository GitHub (vedi NOTIFICHE.md).", size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
            actions=[ft.TextButton("Annulla", on_click=close_settings),
                     ft.FilledButton("Salva", on_click=save_settings)],
        )

        def open_settings(e=None):
            classes_field.value = ", ".join(prefs["classes"])
            name_field.value = prefs["name"]
            phone_field.value = prefs["phone"]
            theme_dropdown.value = prefs["theme"]
            show_dialog(dlg)

        settings_button.on_click = open_settings

        # ---- «Dove mi conviene fare le GPS?» ---------------------------------
        gps_class_field = ft.TextField(label="Classe di concorso", hint_text="es. A028", max_length=6, expand=True,
                                       capitalization=ft.TextCapitalization.CHARACTERS,
                                       prefix_icon=ft.Icons.SCHOOL_ROUNDED, border_radius=14)
        gps_score_field = ft.TextField(label="Il tuo punteggio GPS", hint_text="es. 42,5",
                                       keyboard_type=ft.KeyboardType.NUMBER,
                                       prefix_icon=ft.Icons.STAR_ROUNDED, border_radius=14)
        gps_hint = ft.Text("", size=12.5, color=ft.Colors.ERROR)

        def gps_values():
            cls = (gps_class_field.value or "").strip().upper()
            score = (gps_score_field.value or "").strip().replace(",", ".")
            try:
                num = float(score)
            except ValueError:
                num = None
            return cls, score, num

        def gps_open(url):
            open_url(url)

        gps_data = load_gps_data()

        def gps_data_info():
            prov = (gps_data or {}).get("province", {})
            gui = sum(1 for v in prov.values() for k in v.get("classi", {}) if "#GUI" in k)
            return {"province": len(prov), "gui": gui, "agg": (gps_data or {}).get("aggiornato", "?")}

        def gps_data_text():
            i = gps_data_info()
            return f"dati del {i['agg']} · {i['province']} province · {i['gui']} graduatorie GUI"
        gps_fascia = ft.Dropdown(
            label="Fascia", value="II", expand=True, border_radius=14,
            options=[ft.DropdownOption(key=k, text=v) for k, v in GPS_FASCE.items()],
        )
        gps_region = ft.Dropdown(
            label="Regione", value="", border_radius=14,
            options=[ft.DropdownOption(key="", text="Tutta Italia")]
                    + [ft.DropdownOption(key=r, text=r) for r in sorted(SOURCES.keys())],
        )
        gps_province = ft.Dropdown(
            label="Provincia", value="", border_radius=14,
            options=[ft.DropdownOption(key="", text="Tutte le province")]
                    + [ft.DropdownOption(key=p, text=p) for p in sorted(gps_data.get("province", {}))])
        gps_riserva = ft.Switch(label="Considera la riserva del 15%", value=True)
        gps_tipo = ft.Dropdown(
            label="Graduatoria del sostegno", value="GPS", border_radius=14,
            options=[ft.DropdownOption(key="GPS", text="GPS (con specializzazione sul sostegno)"),
                     ft.DropdownOption(key="GUI", text="GUI (senza specializzazione: incrocio)")])
        gps_tipo_box = ft.Column(visible=False, spacing=6, controls=[
            gps_tipo,
            ft.Text("Per il sostegno i bollettini hanno due graduatorie: la GPS, di chi ha la specializzazione, e la "
                    "GUI (incrocio), dove entra chi non ce l'ha usando il punteggio della graduatoria di origine. "
                    "Hanno soglie diverse, quindi scegli quella in cui sei.", size=11.5,
                    color=ft.Colors.ON_SURFACE_VARIANT)])

        def sync_tipo(e=None):
            is_ad = (gps_class_field.value or "").strip().upper().startswith("AD")
            gps_tipo_box.visible = is_ad
            if not is_ad:
                gps_tipo.value = "GPS"
            try:
                page.update()
            except Exception:
                pass

        gps_class_field.on_change = sync_tipo

        def _keep(e=None):
            """Registra la scelta fatta nei menù a tendina (alcune versioni non la inviano senza un gestore)."""
            try:
                page.update()
            except Exception:
                pass

        for _dd in (gps_tipo, gps_fascia, gps_region, gps_province):
            _dd.on_select = _keep
        gps_riserva.on_change = _keep
        gps_profiles_row = ft.Row(wrap=True, spacing=6, run_spacing=6)
        gps_state = {"rows": {}}

        def profile_label(p):
            return (f"{p['c']}{' ' + p['t'] if p.get('t') else ''} · {GPS_FASCE.get(p['f'], p['f'])} · "
                    f"{p['s'].replace('.', ',')}")

        def use_profile(p):
            gps_class_field.value = p["c"]
            gps_fascia.value = p["f"]
            gps_score_field.value = p["s"]
            sync_tipo()
            if p["c"].startswith("AD"):
                gps_tipo.value = p.get("t", "GPS")
            run_gps()

        def drop_profile(p):
            prefs["profiles"] = [q for q in prefs["profiles"] if q != p]
            save_prefs()
            paint_profiles()
            page.update()

        def paint_profiles():
            chips = []
            for p in prefs["profiles"]:
                chips.append(ft.Container(
                    border_radius=18, bgcolor=ft.Colors.SECONDARY_CONTAINER, ink=True,
                    padding=ft.Padding.only(left=12, right=2, top=2, bottom=2),
                    on_click=lambda e, p=p: use_profile(p),
                    content=ft.Row(tight=True, spacing=0, controls=[
                        ft.Text(profile_label(p), size=12, weight=ft.FontWeight.W_600,
                                color=ft.Colors.ON_SECONDARY_CONTAINER),
                        ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, icon_size=15, tooltip="Elimina",
                                      on_click=lambda e, p=p: drop_profile(p))])))
            gps_profiles_row.controls = chips
            gps_profiles_row.visible = bool(chips)

        def save_profile(e=None):
            cls, score, num = gps_values()
            num = parse_score(score)
            if not re.fullmatch(r"[A-Z0-9]{3,5}", cls) or num is None:
                gps_hint.value = "Scrivi classe e punteggio prima di salvare il profilo."
                page.update()
                return
            p = {"c": cls, "f": gps_fascia.value or "II", "s": score}
            if cls.startswith("AD"):
                p["t"] = gps_tipo.value or "GPS"
            if p not in prefs["profiles"]:
                prefs["profiles"] = (prefs["profiles"] + [p])[-8:]
            gps_hint.value = ""
            save_prefs()
            paint_profiles()
            page.update()

        gps_compare_pick = [ft.Dropdown(label=f"Provincia {i}", value="", expand=True, dense=True, border_radius=14,
                                        options=[ft.DropdownOption(key="", text="—")]) for i in (1, 2, 3)]
        gps_compare_out = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.START)
        gps_compare_card = ft.Container(visible=False)
        gps_stats_card = ft.Container(visible=False)

        def paint_compare(e=None):
            cols = []
            for dd in gps_compare_pick:
                r = gps_state["rows"].get(dd.value or "")
                if not r:
                    continue
                color = GREEN if r["esito"] == "si" else ("#E08A00" if r["esito"] == "forse" else ft.Colors.ERROR)
                label = {"si": "Ci saresti", "forse": "Forse", "no": "Troppo alto"}[r["esito"]]
                cols.append(ft.Container(
                    expand=True, padding=10, border_radius=14, bgcolor=ft.Colors.with_opacity(0.10, color),
                    content=ft.Column(spacing=3, controls=[
                        ft.Text(r["provincia"], size=13, weight=ft.FontWeight.W_800),
                        ft.Text(label, size=12, weight=ft.FontWeight.W_700, color=color),
                        ft.Text(f"Ultimo: {fmt_score(r['soglia'])}", size=11.5),
                        ft.Text(f"Nomine: {r['nomine']}", size=11.5),
                        ft.Text((f"Margine: +{fmt_score(r['margine'])}" if r["margine"] >= 0
                                 else f"Mancano: {fmt_score(r['mancano'] or abs(r['margine']))}"), size=11.5)])))
            gps_compare_out.controls = cols
            try:
                page.update()
            except Exception:
                pass

        for dd in gps_compare_pick:
            dd.on_select = paint_compare
        gps_results = ft.Column(spacing=10)
        gps_summary = ft.Container(visible=False)
        gps_info = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

        def stat_tile(value, label, color):
            return ft.Container(
                expand=True, padding=ft.Padding.symmetric(horizontal=8, vertical=12), border_radius=16,
                bgcolor=ft.Colors.with_opacity(0.12, color),
                content=ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Text(str(value), size=26, weight=ft.FontWeight.W_800, color=color),
                    ft.Text(label, size=11.5, weight=ft.FontWeight.W_600, color=color,
                            text_align=ft.TextAlign.CENTER),
                ]),
            )

        def gps_row(i, r, score):
            if r["esito"] == "si":
                color, verdict, icon = GREEN, f"Ci saresti · +{fmt_score(r['margine'])} punti", ft.Icons.CHECK_CIRCLE_ROUNDED
            elif r["esito"] == "forse":
                color, verdict, icon = "#E08A00", "Forse · dipende dalla riserva", ft.Icons.HELP_ROUNDED
            else:
                color, verdict, icon = ft.Colors.ERROR, f"Ti mancano {fmt_score(r['mancano'])} punti", ft.Icons.CANCEL_ROUNDED
            soglia = r["soglia"] or 1
            fill = max(0.04, min(1.0, score / soglia)) if soglia else 1.0
            last = (f"Ultimo nominato: {fmt_score(r['soglia'])} punti (posiz. {r['ultima']})"
                    + (f" · con riserva piena {fmt_score(r['minima'])}" if r["escluse"] else ""))
            return ft.Container(
                border_radius=18, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                shadow=ft.BoxShadow(blur_radius=8, offset=ft.Offset(0, 2),
                                    color=ft.Colors.with_opacity(0.07, ft.Colors.BLACK)),
                content=ft.Row(spacing=0, controls=[
                    ft.Container(width=6, bgcolor=color),
                    ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                                 content=ft.Column(spacing=6, controls=[
                        ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                            ft.Text(str(i), size=12, weight=ft.FontWeight.W_700, color=ft.Colors.OUTLINE),
                            ft.Column(expand=True, spacing=0, controls=[
                                ft.Text(r["provincia"], size=16, weight=ft.FontWeight.W_800),
                                ft.Text(f"{r['regione']} · {r['nomine']} nomine", size=11.5,
                                        color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            ft.Icon(icon, color=color, size=24),
                        ]),
                        ft.Text(verdict, size=13, weight=ft.FontWeight.W_700, color=color),
                        ft.ProgressBar(value=fill, color=color, bgcolor=ft.Colors.with_opacity(0.15, color),
                                       bar_height=6, border_radius=3),
                        ft.Text(last, size=11.5, color=ft.Colors.ON_SURFACE_VARIANT),
                        *([ft.Text(f"Riserva 15%: tolti {r['escluse']} posti su {r['chiamati']} chiamati della classe "
                                   + ("(riservisti riconosciuti dal salto di posizione)" if r.get("rilevata")
                                      else "(dai punteggi più bassi)"), size=11.5,
                                   color=ft.Colors.ON_SURFACE_VARIANT)] if r.get("escluse") else []),
                        *([ft.Text("Per turno, ultimo nominato: " + " → ".join(
                            f"{b}° {fmt_score(v)}" for b, v in r["turni"]), size=11.5,
                            color=ft.Colors.ON_SURFACE_VARIANT)] if len(r.get("turni", [])) > 1 else []),
                    ])),
                ]),
            )

        def run_gps(e=None):
            gps_results.controls = []
            gps_summary.visible = False
            gps_info.visible = False
            gps_compare_card.visible = False
            gps_stats_card.visible = False
            gps_share_row.visible = False
            cls, score, num = gps_values()
            num = parse_score(score)
            if not re.fullmatch(r"[A-Z0-9]{3,5}", cls) or num is None:
                gps_hint.value = "Scrivi la classe di concorso (es. A028) e il punteggio (es. 42,5)."
            else:
                gps_hint.value = ""
                prefs["gps_class"], prefs["gps_score"] = cls, score
                save_prefs()
                fascia = gps_fascia.value or "II"
                tipo = gps_tipo.value if cls.startswith("AD") else "GPS"
                rows = gps_rank(gps_data, cls, fascia, num, gps_region.value or "",
                                riserva=GPS_RISERVA if gps_riserva.value else 0.0, tipo=tipo)
                if gps_province.value:
                    rows = [r for r in rows if r["provincia"] == gps_province.value]
                gps_info.visible = True
                if not rows and tipo == "GUI" and cls.startswith("AD") and not gps_data_info()["gui"]:
                    gps_info.value = ("I dati caricati nell'app non contengono le graduatorie GUI (" + gps_data_text()
                                      + "). Sostituisci il file assets/gps_data.json con quello nuovo e rifai la build.")
                elif not rows:
                    gps_info.value = (f"Nessuna nomina trovata per {cls}{' · ' + tipo if cls.startswith('AD') else ''} "
                                      f"({GPS_FASCE.get(fascia, '')}) nelle province con dati. "
                                      "Controlla la sigla della classe o cambia fascia.")
                else:
                    yes = sum(1 for r in rows if r["esito"] == "si")
                    maybe = sum(1 for r in rows if r["esito"] == "forse")
                    no = len(rows) - yes - maybe
                    gps_summary.content = ft.Column(spacing=8, controls=[
                        ft.Text(f"{cls}{' · ' + tipo if cls.startswith('AD') else ''} · {GPS_FASCE.get(fascia, '')} · {fmt_score(num)} punti",
                                size=13, weight=ft.FontWeight.W_700),
                        ft.Row(spacing=8, controls=[stat_tile(yes, "Ci saresti", GREEN),
                                                    stat_tile(maybe, "Forse", "#E08A00"),
                                                    stat_tile(no, "Troppo alto", ft.Colors.ERROR)]),
                    ])
                    gps_summary.visible = True
                    gps_results.controls = [gps_row(i, r, num) for i, r in enumerate(rows[:80], 1)]
                    gps_state["rows"] = {r["provincia"]: r for r in rows}
                    gps_state["text"] = (f"GPS {cls}, {GPS_FASCE.get(fascia, '')}, {fmt_score(num)} punti:\n" + "\n".join(
                        f"• {r['provincia']}: " + {"si": "ci saresti", "forse": "forse",
                                                   "no": "troppo alto"}[r["esito"]]
                        + f" (ultimo nominato {fmt_score(r['soglia'])})" for r in rows[:30]))
                    gps_share_row.visible = True
                    opts = [ft.DropdownOption(key="", text="—")] + [
                        ft.DropdownOption(key=r["provincia"], text=r["provincia"]) for r in rows]
                    for dd, r in zip(gps_compare_pick, rows):
                        dd.options, dd.value = opts, r["provincia"]
                    for dd in gps_compare_pick[len(rows):]:
                        dd.options, dd.value = opts, ""
                    paint_compare()
                    gps_compare_card.visible = len(rows) > 1
                    st = gps_stats(gps_data, cls)
                    if st["totale"]:
                        gps_stats_card.content = ft.Column(spacing=6, controls=[
                            ft.Text(f"Classe {cls} in tutta Italia", size=14, weight=ft.FontWeight.W_700),
                            ft.Text(f"{st['totale']} nomine in {st['province']} province "
                                    f"(I fascia {st['fasce'].get('I', 0)}, II fascia {st['fasce'].get('II', 0)}).",
                                    size=12.5),
                            ft.Text("Dove ne hanno chiamate di più: " + ", ".join(
                                f"{p} ({n})" for p, n in st["top"]), size=12.5,
                                color=ft.Colors.ON_SURFACE_VARIANT)])
                        gps_stats_card.visible = True
                    gps_info.value = (f"{len(rows)} province con dati" + (" (mostro le prime 80)" if len(rows) > 80 else "")
                                      + f" · Bollettino n. {gps_data.get('bollettino', '?')} {gps_data.get('anno', '')}, "
                                        f"aggiornato al {gps_data.get('aggiornato', '?')}.")
            page.update()

        gps_all_out = ft.Column(spacing=6)
        gps_share_row = ft.Row(visible=False, wrap=True, spacing=0)

        def run_all(e=None):
            _cls, score, _n = gps_values()
            num = parse_score(score)
            if num is None:
                gps_hint.value = "Scrivi il tuo punteggio per vedere l'esito su tutte le tue classi."
                gps_all_out.controls = []
            elif not prefs["classes"]:
                gps_all_out.controls = [ft.Text("Aggiungi le tue classi con il tasto in alto nella schermata "
                                                "principale (Le mie classi).", size=12.5)]
            else:
                gps_hint.value = ""
                fascia = gps_fascia.value or "II"
                lines = []
                for c in prefs["classes"]:
                    rows = gps_rank(gps_data, c, fascia, num, gps_region.value or "",
                                    riserva=GPS_RISERVA if gps_riserva.value else 0.0)
                    yes = sum(1 for r in rows if r["esito"] == "si")
                    maybe = sum(1 for r in rows if r["esito"] == "forse")
                    color = GREEN if yes else ("#E08A00" if maybe else ft.Colors.OUTLINE)
                    text = (f"ci saresti in {yes}, forse in {maybe}, su {len(rows)} province con dati"
                            if rows else "nessuna nomina trovata nei bollettini")
                    lines.append(ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=4), border_radius=10,
                                     bgcolor=ft.Colors.with_opacity(0.14, color),
                                     content=ft.Text(c, size=13, weight=ft.FontWeight.W_800, color=color)),
                        ft.Text(text, size=12.5, expand=True)]))
                gps_all_out.controls = lines
            page.update()

        def gps_share_text():
            return gps_state.get("text", "")

        def gps_copy(e=None):
            try:
                page.run_task(clipboard.set, gps_share_text())
                notify("Elenco copiato.")
            except Exception:
                notify("Copia non riuscita.")

        def gps_whatsapp(e=None):
            open_url("https://wa.me/?text=" + quote(gps_share_text()))

        gps_share_row.controls = [
            ft.TextButton(content="Copia elenco", icon=ft.Icons.CONTENT_COPY_ROUNDED, on_click=gps_copy),
            ft.TextButton(content="Invia su WhatsApp", icon=ft.Icons.SHARE_ROUNDED, on_click=gps_whatsapp)]

        def section_card(controls):
            return ft.Container(
                padding=16, border_radius=22, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                content=ft.Column(spacing=12, controls=controls))

        gps_compare_card.content = section_card([
            ft.Text("Confronta province", size=14, weight=ft.FontWeight.W_700),
            ft.Row(spacing=8, controls=gps_compare_pick), gps_compare_out])

        gps_calc_button = ft.FilledButton(content="Trova le province migliori", icon=ft.Icons.PLACE_ROUNDED,
                                          on_click=run_gps, visible=bool(gps_data), expand=True, height=50)
        gps_no_data = ft.Text(
            "I dati dei bollettini non sono ancora nell'app: usa i servizi esterni qui sotto.",
            size=12, color=ft.Colors.ON_SURFACE_VARIANT, visible=not gps_data)

        def close_gps(e=None):
            gps_view.visible = False
            home_view.visible = True
            page.update()

        gps_header = ft.Container(
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[BRAND_DARK, BRAND_LIGHT]),
            padding=ft.Padding.only(left=6, right=18, top=18, bottom=18),
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=26,
                              tooltip="Indietro", on_click=close_gps),
                ft.Column(expand=True, spacing=0, controls=[
                    ft.Text("Dove fare le GPS", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
                    ft.Text("Il tuo punteggio contro i bollettini di nomina", size=12,
                            color=ft.Colors.with_opacity(0.88, ft.Colors.WHITE)),
                ]),
            ]),
        )

        gps_body = ft.Column(
            expand=True, scroll=ft.ScrollMode.AUTO, spacing=14,
            controls=[
                ft.Container(padding=ft.Padding.only(left=16, right=16, top=16, bottom=28), content=ft.Column(
                    spacing=14,
                    controls=[
                        section_card([
                            ft.Text("Inserisci classe, fascia e punteggio: l'app lo confronta con l'ultimo nominato "
                                    "dei bollettini di nomina di ogni provincia.", size=12.5,
                                    color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Row(spacing=10, controls=[gps_class_field, gps_fascia]),
                            gps_tipo_box,
                            gps_score_field,
                            ft.TextButton(content="Non so il mio punteggio: calcolalo", icon=ft.Icons.CALCULATE_ROUNDED,
                                          on_click=lambda e: open_calc(e)),
                            ft.Row(spacing=10, controls=[ft.Column(expand=True, controls=[gps_region]),
                                                         ft.Column(expand=True, controls=[gps_province])]),
                            gps_riserva,
                            gps_hint,
                            ft.Row(controls=[gps_calc_button]),
                            ft.TextButton(content="Salva questo profilo", icon=ft.Icons.BOOKMARK_ADD_ROUNDED,
                                          on_click=save_profile),
                            gps_profiles_row,
                            gps_no_data,
                        ]),
                        gps_summary,
                        gps_share_row,
                        gps_results,
                        gps_info,
                        gps_compare_card,
                        gps_stats_card,
                        section_card([
                            ft.Text("Le mie classi", size=14, weight=ft.FontWeight.W_700),
                            ft.Text("Con il punteggio e la fascia qui sopra, l'esito per tutte le classi che hai "
                                    "salvato in «Le mie classi».", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.FilledTonalButton(content="Esito su tutte le mie classi",
                                                 icon=ft.Icons.FACT_CHECK_ROUNDED, on_click=run_all),
                            gps_all_out]),
                        section_card([
                            ft.Text("Altri strumenti", size=14, weight=ft.FontWeight.W_700),
                            ft.TextButton(content="Graduatorie GPS di ogni provincia",
                                          icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                                          on_click=lambda e: gps_open(GPS_LISTS_URL)),
                        ]),
                        ft.Text("Riserva servizio civile: il 15% dei chiamati di ogni classe in ogni bollettino (es. 20 chiamati: 3 posti riservati). I bollettini "
                                "non dicono chi sono, quindi «ci saresti» vale anche con la quota piena (tolgo quei posti "
                                "dai punteggi più bassi); «forse» se il tuo punteggio basta solo se i riservisti sono "
                                "stati meno.", size=11.5, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("Dati nell'app: " + gps_data_text(), size=11.5, weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text("Solo le province con bollettini già caricati. Nei bollettini successivi si scende "
                                "più in basso, quindi è una stima prudente. Fa fede l'Ufficio Scolastico della "
                                "provincia.", size=11.5, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                )),
            ],
        )

        gps_view = ft.Column(expand=True, spacing=0, visible=False, controls=[gps_header, gps_body])

        def open_gps(e=None):
            first_class = prefs["classes"][0] if prefs["classes"] else ""
            gps_class_field.value = prefs["gps_class"] or first_class
            gps_score_field.value = prefs["gps_score"]
            gps_hint.value = ""
            sync_tipo()
            gps_info.visible = False
            gps_summary.visible = False
            gps_compare_card.visible = False
            gps_stats_card.visible = False
            gps_results.controls = []
            paint_profiles()
            home_view.visible = False
            gps_view.visible = True
            page.update()

        gps_button.on_click = open_gps

        def go_back(e=None):
            """Indietro dalle pagine interne; True se ha gestito il gesto."""
            if calc_view.visible:
                close_calc()
                return True
            if gps_view.visible:
                close_gps()
                return True
            return False

        for _name in ("on_back_button", "on_view_pop"):
            try:
                setattr(page, _name, go_back)
            except Exception:
                pass

        # ---- Calcolo del punteggio GPS ------------------------------------------
        calc = {"serv": []}
        c_voto = ft.TextField(label="Voto di laurea / diploma (es. 98)", keyboard_type=ft.KeyboardType.NUMBER,
                              border_radius=14, prefix_icon=ft.Icons.SCHOOL_ROUNDED)
        c_lode = ft.Switch(label="110 e lode (+4)", value=False)
        c_tipo = ft.Dropdown(label="Con quale titolo sei in prima fascia?", value="lau", border_radius=14,
                             options=[ft.DropdownOption(key="lau", text="Laurea / diploma (vecchi percorsi)"),
                                      ft.DropdownOption(key="abil", text="Abilitazione 60 CFU (DPCM 4/8/2023)")])
        c_vabil = ft.Dropdown(label="Voto dell'abilitazione (in decimi)", value="", border_radius=14,
                              options=[ft.DropdownOption(key="", text="Scegli il voto")] + [
                                  ft.DropdownOption(key=f"{v:g}", text=f"{v:g}/10 → {GPS_ABIL_BASE + p} punti")
                                  for v, p in GPS_ABIL_VOTI])
        c_itp = ft.Switch(label="Classe ITP della tabella B (senza i 24 punti di base)", value=False)
        c_abil_note = ft.Text("L'abilitazione è titolo di accesso: vale 24 punti di base più fino a 12 in base al voto "
                              "(10/10 = 36, 9/10 = 33, 8/10 = 31, 7/10 = 29). Il voto di laurea qui non conta.",
                              size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        c_extra = {k: ft.Switch(label=f"{label} ({pts} punti)", value=False) for k, label, pts in GPS_TITOLI_EXTRA}
        c_master = ft.Dropdown(label="Master (1 punto ciascuno, max 3)", value="0", border_radius=14,
                               options=[ft.DropdownOption(key=str(i), text=str(i)) for i in range(0, 4)])
        c_lingua = ft.Dropdown(label="Certificazione linguistica più alta", value="", border_radius=14,
                               options=[ft.DropdownOption(key="", text="Nessuna"),
                                        ft.DropdownOption(key="B2", text="B2 (3 punti)"),
                                        ft.DropdownOption(key="C1", text="C1 (4 punti)"),
                                        ft.DropdownOption(key="C2", text="C2 (6 punti)")])
        c_dig = ft.Switch(label="Certificazione DigComp 2.2 (1 punto)", value=False)
        c_digedu = ft.Switch(label="Certificazione DigCompEdu (2 punti)", value=False)
        c_serv_type = ft.Dropdown(label="Tipo", value="s", expand=True, dense=True, border_radius=14,
                                  options=[ft.DropdownOption(key="s", text="Specifico"),
                                           ft.DropdownOption(key="a", text="Aspecifico")])
        c_serv_days = ft.TextField(label="Giorni", keyboard_type=ft.KeyboardType.NUMBER, expand=True,
                                   dense=True, border_radius=14)
        c_serv_list = ft.Column(spacing=4)
        c_total = ft.Text("0", size=44, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE)
        c_detail = ft.Text("", size=12, color=ft.Colors.with_opacity(0.9, ft.Colors.WHITE))

        def calc_total():
            try:
                voto = int((c_voto.value or "").strip())
            except ValueError:
                voto = None
            if voto is not None and not 1 <= voto <= 110:
                voto = None
            if c_tipo.value == "abil":
                try:
                    acc = gps_points_abil(float((c_vabil.value or "").replace(",", ".")), c_itp.value)
                except ValueError:
                    acc = 0.0
            else:
                acc = gps_points_access(voto, c_lode.value)
            extra = sum(pts for k, _l, pts in GPS_TITOLI_EXTRA if c_extra[k].value)
            master = min(int(c_master.value or 0), GPS_MASTER_MAX)
            lingua = GPS_LINGUE.get(c_lingua.value or "", 0)
            info = min((1 if c_dig.value else 0) + (2 if c_digedu.value else 0), GPS_INFORMATICHE_MAX)
            serv = sum(gps_points_service(d, t == "s") for t, d in calc["serv"])
            parts = [("Titolo di accesso", acc), ("Titoli aggiuntivi", extra + master + lingua + info),
                     ("Servizio", serv)]
            return sum(v for _n, v in parts), parts

        def save_calc():
            prefs["calc"] = {
                "voto": c_voto.value or "", "lode": bool(c_lode.value),
                "tipo": c_tipo.value or "lau", "vabil": c_vabil.value or "", "itp": bool(c_itp.value),
                "extra": [k for k, sw in c_extra.items() if sw.value],
                "master": c_master.value or "0", "lingua": c_lingua.value or "",
                "dig": bool(c_dig.value), "digedu": bool(c_digedu.value),
                "serv": [[t, d] for t, d in calc["serv"]]}
            save_prefs()

        def restore_calc():
            c = prefs.get("calc") or {}
            try:
                c_voto.value = str(c.get("voto", ""))
                c_lode.value = bool(c.get("lode"))
                if c.get("tipo") in ("lau", "abil"):
                    c_tipo.value = c["tipo"]
                if c.get("vabil", "") in [""] + [f"{v:g}" for v, _p in GPS_ABIL_VOTI]:
                    c_vabil.value = c.get("vabil", "")
                c_itp.value = bool(c.get("itp"))
                for k, sw in c_extra.items():
                    sw.value = k in (c.get("extra") or [])
                if str(c.get("master", "0")) in ("0", "1", "2", "3"):
                    c_master.value = str(c.get("master", "0"))
                if c.get("lingua", "") in GPS_LINGUE:
                    c_lingua.value = c.get("lingua", "")
                c_dig.value = bool(c.get("dig"))
                c_digedu.value = bool(c.get("digedu"))
                calc["serv"] = [(t, int(d)) for t, d in (c.get("serv") or []) if t in ("s", "a")][:40]
            except Exception:
                calc["serv"] = []

        def paint_calc(e=None):
            ab = c_tipo.value == "abil"
            c_voto.visible = c_lode.visible = not ab
            c_vabil.visible = c_itp.visible = c_abil_note.visible = ab
            total, parts = calc_total()
            c_total.value = fmt_score(total)
            c_detail.value = "  ·  ".join(f"{n}: {fmt_score(v)}" for n, v in parts)
            rows = []
            for i, (t, d) in enumerate(calc["serv"]):
                pts = gps_points_service(d, t == "s")
                rows.append(ft.Row(spacing=4, controls=[
                    ft.Text(f"{'Specifico' if t == 's' else 'Aspecifico'} · {d} giorni → {fmt_score(pts)} punti",
                            size=13, expand=True),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=20, tooltip="Togli",
                                  on_click=lambda ev, i=i: drop_service(i))]))
            c_serv_list.controls = rows
            save_calc()
            page.update()

        def drop_service(i):
            if 0 <= i < len(calc["serv"]):
                del calc["serv"][i]
            paint_calc()

        def add_service(e=None):
            try:
                days = int((c_serv_days.value or "").strip())
            except ValueError:
                days = 0
            if days < 16 or days > 366:
                notify("Servono almeno 16 giorni di servizio in un anno scolastico (massimo 366).")
                return
            calc["serv"].append((c_serv_type.value or "s", days))
            c_serv_days.value = ""
            paint_calc()

        for ctl in [c_voto, c_lode, c_dig, c_digedu, c_itp, *c_extra.values()]:
            ctl.on_change = paint_calc
        for ctl in (c_master, c_lingua, c_tipo, c_vabil):
            ctl.on_select = paint_calc
        c_serv_days.on_submit = add_service

        calc_origin = {"home": False}

        def close_calc(e=None):
            calc_view.visible = False
            (home_view if calc_origin["home"] else gps_view).visible = True
            page.update()

        def use_score(e=None):
            total, _parts = calc_total()
            gps_score_field.value = fmt_score(total)
            calc_origin["home"] = False          # il punteggio si usa nella pagina «Dove fare le GPS»
            close_calc()

        restore_calc()

        def open_calc(e=None, from_home=False):
            calc_origin["home"] = from_home
            gps_view.visible = False
            home_view.visible = False
            calc_view.visible = True
            paint_calc()

        calc_header = ft.Container(
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[BRAND_DARK, BRAND_LIGHT]),
            padding=ft.Padding.only(left=6, right=18, top=18, bottom=18),
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            content=ft.Column(spacing=4, controls=[
                ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=26,
                                  tooltip="Indietro", on_click=close_calc),
                    ft.Text("Calcola il tuo punteggio", size=20, weight=ft.FontWeight.W_800,
                            color=ft.Colors.WHITE)]),
                ft.Container(padding=ft.Padding.only(left=16), content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.END, spacing=8,
                    controls=[c_total, ft.Text("punti", size=15, color=ft.Colors.WHITE)])),
                ft.Container(padding=ft.Padding.only(left=16), content=c_detail),
            ]),
        )

        def calc_section(title, controls):
            return section_card([ft.Text(title, size=14, weight=ft.FontWeight.W_700), *controls])

        calc_body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
            ft.Container(padding=ft.Padding.only(left=16, right=16, top=16, bottom=28), content=ft.Column(
                spacing=14, controls=[
                    calc_section("1. Titolo di accesso", [c_tipo, c_voto, c_lode, c_vabil, c_itp, c_abil_note]),
                    calc_section("2. Titoli aggiuntivi", [*c_extra.values(), c_master, c_lingua, c_dig, c_digedu]),
                    calc_section("3. Servizio prestato", [
                        ft.Text("Un inserimento per ogni anno scolastico (massimo 12 punti l'anno). Il servizio "
                                "aspecifico, su un'altra classe di concorso o tipologia di posto, vale la metà.",
                                size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Row(spacing=8, controls=[c_serv_type, c_serv_days]),
                        ft.FilledTonalButton(content="Aggiungi anno", icon=ft.Icons.ADD_ROUNDED,
                                             on_click=add_service),
                        c_serv_list]),
                    ft.FilledButton(content="Usa questo punteggio", icon=ft.Icons.CHECK_ROUNDED, height=50,
                                    on_click=use_score),
                    ft.Text("Calcolo indicativo con le regole dell'OM 27/2026 come riportate qui: controlla sempre "
                            "la domanda e i titoli valutabili sul sito del Ministero.", size=11.5,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                ])),
        ])
        calc_view = ft.Column(expand=True, spacing=0, visible=False, controls=[calc_header, calc_body])

        def on_search_change(e):
            clear_button.visible = bool(search_input.value)
            page.update()
            if timers["search"]:
                timers["search"].cancel()
            # attende 300 ms dall'ultimo tasto: la digitazione resta fluida
            timers["search"] = threading.Timer(0.3, lambda: load_results(reset=True))
            timers["search"].daemon = True
            timers["search"].start()

        def on_clear(e):
            search_input.value = ""
            clear_button.visible = False
            load_results(reset=True)

        def on_region(e):
            state["region"] = region_dropdown.value or ""
            load_results(reset=True)

        def on_status(e):
            state["status"] = status_dropdown.value or ""
            load_results(reset=True)

        search_input.on_change = on_search_change
        clear_button.on_click = on_clear
        region_dropdown.on_select = on_region
        status_dropdown.on_select = on_status

        # ---- Aggiornamento fonti -------------------------------------------
        def notify(message):
            try:
                page.show_dialog(ft.SnackBar(content=ft.Text(message), behavior=ft.SnackBarBehavior.FLOATING))
            except Exception:
                pass

        def refresh(e=None):
            if state["refreshing"]:
                return
            state["refreshing"] = True
            refresh_button.disabled = True
            progress_bar.visible = True
            progress_bar.value = None  # indeterminata finché non si conosce il totale
            region = state["region"]
            status_text.value = f"Download in corso per {region}…" if region else "Download in corso…"
            load_results(reset=False, live=True)   # mostra subito lo stato "sto cercando…"

            def background_task():
                new_count = 0
                mine_count = 0
                failed = 0
                try:
                    init_db()
                    known = known_urls()
                    conn = db_connect()

                    target_sources = {region: SOURCES[region]} if region and region in SOURCES else SOURCES
                    tasks_info = []
                    for reg, sources in target_sources.items():
                        for src_tuple in sources:
                            source_name, base_url = src_tuple[0], src_tuple[1]
                            max_pages = src_tuple[2] if len(src_tuple) > 2 else 1
                            for p in range(1, max_pages + 1):
                                tasks_info.append((reg, source_name, get_page_url(base_url, p)))

                    if not region or region == "Altre fonti":
                        for custom in prefs["sources"]:
                            tasks_info.append(("Altre fonti", custom["n"], custom["u"]))
                    SOURCE_LOG.clear()
                    total = len(tasks_info)
                    completed = 0
                    last_ui = 0.0
                    last_live = 0.0
                    shown_new = 0

                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = [executor.submit(parse_source_page, reg, src, url, known)
                                   for reg, src, url in tasks_info]
                        for future in as_completed(futures):
                            completed += 1
                            try:
                                items, ok = future.result()
                                if not ok:
                                    failed += 1
                                for item in items:
                                    try:
                                        cur = conn.execute(
                                            """INSERT INTO interpelli (title, url, region, source, target, published, deadline, cdc, post_type, doc_url, email)
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                               ON CONFLICT(url) DO UPDATE SET title=excluded.title, target=excluded.target,
                                               published=excluded.published, deadline=excluded.deadline, post_type=excluded.post_type,
                                               doc_url=excluded.doc_url, email=excluded.email""",
                                            item)
                                        if cur.rowcount:
                                            new_count += 1
                                            if matches_classes(item[0], item[7], prefs["classes"]):
                                                mine_count += 1
                                        known.add(item[1])
                                    except sqlite3.Error:
                                        pass
                                conn.commit()
                            except Exception:
                                failed += 1

                            now = time.monotonic()
                            # i risultati si vedono subito: la lista si aggiorna mentre si cerca
                            if new_count != shown_new and now - last_live > 1.2:
                                last_live, shown_new = now, new_count
                                status_text.value = f"Analizzo le fonti… {completed}/{total} · {new_count} nuovi"
                                progress_bar.value = completed / total if total else 1
                                load_results(reset=False, live=True)
                                last_ui = now
                            elif now - last_ui > 0.2 or completed == total:
                                last_ui = now
                                progress_bar.value = completed / total if total else 1
                                status_text.value = f"Analizzo le fonti… {completed}/{total} · {new_count} nuovi"
                                page.update()
                    conn.commit()
                    conn.close()
                except Exception as ex:
                    print(f"Errore scraping: {ex}")
                    notify("Aggiornamento interrotto da un errore.")
                finally:
                    try:
                        prefs["src_status"].update({k: dict(v, t=date.today().isoformat())
                                                    for k, v in SOURCE_LOG.items()})
                        save_prefs()
                    except Exception:
                        pass
                    state["refreshing"] = False
                    progress_bar.visible = False
                    refresh_button.disabled = False
                    load_results(reset=False, live=True)
                    msg = f"{new_count} nuovi interpelli" if new_count else "Nessun nuovo interpello"
                    if mine_count:
                        msg = f"⭐ {mine_count} nuovi per te · " + msg
                    if failed:
                        msg += f" · {failed} fonti non raggiungibili"
                    notify(msg)

            threading.Thread(target=background_task, daemon=True).start()

        refresh_button.on_click = refresh

        # ---- Composizione pagina -------------------------------------------
        home_view = ft.Column(expand=True, spacing=0, controls=[header, filters, status_row, results])
        paint_pills()
        refresh_classes_text()
        # ---- Radar opportunità: interpelli aperti per le tue classi + esito GPS per provincia ----
        r_score = ft.TextField(label="Il tuo punteggio GPS (facoltativo)", hint_text="es. 42,5", expand=True,
                               keyboard_type=ft.KeyboardType.NUMBER, border_radius=14, dense=True)
        r_fascia = ft.Dropdown(label="Fascia", value="II", expand=True, dense=True, border_radius=14,
                               options=[ft.DropdownOption(key=k, text=v) for k, v in GPS_FASCE.items()])
        r_summary = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)
        r_list = ft.Column(spacing=10)

        def close_radar(e=None):
            radar_view.visible = False
            home_view.visible = True
            page.update()

        def radar_see(name):
            state["profile"] = "ME"
            search_input.value = name
            clear_button.visible = True
            paint_pills()
            radar_view.visible = False
            home_view.visible = True
            load_results(reset=True)

        def paint_radar(e=None):
            num = parse_score(r_score.value or "")
            if num is not None:
                prefs["gps_score"] = (r_score.value or "").strip().replace(",", ".")
                save_prefs()
            classes = prefs["classes"]
            r_list.controls = []
            if not classes:
                r_summary.value = ""
                r_list.controls = [section_card([
                    ft.Text("Prima scegli le tue classi di concorso (tasto «Le mie classi» nella schermata "
                            "principale): il radar mostra solo gli interpelli per te.", size=13)])]
                page.update()
                return
            fascia = r_fascia.value or "II"
            ranks = {}
            if num is not None and gps_data:
                for c in classes:
                    ranks[c] = {r["provincia"]: r for r in gps_rank(gps_data, c, fascia, num, "",
                                                                    riserva=GPS_RISERVA)}
            province_names = sorted(gps_data.get("province", {}))
            today_s = date.today().strftime("%Y-%m-%d")
            conn = db_connect()
            rows = conn.execute(
                "SELECT title, source, cdc FROM interpelli WHERE target = 'DOCENTI' "
                "AND (deadline IS NULL OR deadline = '' OR deadline >= ?)", (today_s,)).fetchall()
            conn.close()
            groups = {}
            for title, source, cdc in rows:
                if not matches_classes(title, cdc, classes):
                    continue
                g = groups.setdefault(source, {"n": 0, "esiti": []})
                g["n"] += 1
                codes = [x.strip() for x in (cdc or "").upper().split(",")]
                mine = [c for c in classes if c in codes or re.search(rf"\b{re.escape(c)}\b", (title or "").upper())]
                for prov in source_provinces(source, province_names):
                    for c in mine:
                        r = ranks.get(c, {}).get(prov)
                        if r:
                            g["esiti"].append(r["esito"])
            order = {"si": 0, "forse": 1, "no": 2, None: 3}
            items = []
            for source, g in groups.items():
                best = min(g["esiti"], key=lambda x: order[x]) if g["esiti"] else None
                items.append((order[best], -g["n"], source, g["n"], best))
            items.sort()
            total = sum(i[3] for i in items)
            yes = sum(1 for i in items if i[4] == "si")
            r_summary.value = (f"{total} interpelli aperti per te in {len(items)} province"
                               + (f" · in {yes} ci saresti" if num is not None and gps_data else ""))
            if not items:
                r_list.controls = [section_card([ft.Text(
                    "Nessun interpello aperto per le tue classi. Aggiorna la ricerca dalla schermata principale.",
                    size=13)])]
            for _o, _n, source, n, best in items:
                label = re.sub(r"^(USP|AT)\s+", "", source, flags=re.I)
                color, verdict = {
                    "si": (GREEN, "Ci saresti"), "forse": ("#E08A00", "Forse"),
                    "no": (ft.Colors.ERROR, "Troppo alto"), None: (ft.Colors.OUTLINE, "Esito GPS non disponibile"),
                }[best]
                if num is None:
                    color, verdict = ft.Colors.OUTLINE, "Inserisci il punteggio per l'esito"
                r_list.controls.append(ft.Container(
                    border_radius=18, clip_behavior=ft.ClipBehavior.HARD_EDGE, ink=True,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    on_click=lambda ev, name=label: radar_see(name),
                    content=ft.Row(spacing=0, controls=[
                        ft.Container(width=6, bgcolor=color, height=64),
                        ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                                     content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                                         ft.Column(expand=True, spacing=1, controls=[
                                             ft.Text(label, size=15, weight=ft.FontWeight.W_800),
                                             ft.Text(verdict, size=12, weight=ft.FontWeight.W_700, color=color)]),
                                         ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END,
                                                   controls=[ft.Text(str(n), size=22, weight=ft.FontWeight.W_800),
                                                             ft.Text("interpelli", size=11,
                                                                     color=ft.Colors.ON_SURFACE_VARIANT)]),
                                         ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=ft.Colors.OUTLINE)]))])))
            page.update()

        def open_radar(e=None):
            r_score.value = prefs["gps_score"]
            r_fascia.value = gps_fascia.value or "II"
            home_view.visible = False
            radar_view.visible = True
            paint_radar()

        radar_button.on_click = open_radar
        r_score.on_submit = paint_radar
        r_fascia.on_select = paint_radar

        radar_header = ft.Container(
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[BRAND_DARK, BRAND_LIGHT]),
            padding=ft.Padding.only(left=6, right=18, top=18, bottom=18),
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            content=ft.Column(spacing=4, controls=[
                ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=26,
                                  tooltip="Indietro", on_click=close_radar),
                    ft.Column(expand=True, spacing=0, controls=[
                        ft.Text("Radar opportunità", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
                        ft.Text("Interpelli aperti per le tue classi + il tuo esito nelle GPS", size=12,
                                color=ft.Colors.with_opacity(0.88, ft.Colors.WHITE))])]),
                ft.Container(padding=ft.Padding.only(left=16), content=r_summary)]))

        radar_body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
            ft.Container(padding=ft.Padding.only(left=16, right=16, top=16, bottom=28), content=ft.Column(
                spacing=14, controls=[
                    section_card([
                        ft.Text("Con il tuo punteggio vedo in quali province, tra quelle con interpelli aperti, "
                                "saresti già chiamato dalle GPS. Tocca una provincia per vedere i suoi interpelli.",
                                size=12.5, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Row(spacing=10, controls=[r_score, r_fascia]),
                        ft.FilledTonalButton(content="Aggiorna", icon=ft.Icons.REFRESH_ROUNDED, on_click=paint_radar)]),
                    r_list]))])
        radar_view = ft.Column(expand=True, spacing=0, visible=False, controls=[radar_header, radar_body])

        _go_back_inner = go_back

        def go_back(e=None):
            if radar_view.visible:
                close_radar()
                return True
            return _go_back_inner(e)

        for _name in ("on_back_button", "on_view_pop"):
            try:
                setattr(page, _name, go_back)
            except Exception:
                pass

        # ---- Stato delle fonti e fonti personali -------------------------------------------
        sv_name = ft.TextField(label="Nome (es. IC Rossi)", dense=True, border_radius=14)
        sv_url = ft.TextField(label="Indirizzo della pagina o del feed RSS", dense=True, border_radius=14,
                              keyboard_type=ft.KeyboardType.URL)
        sv_summary = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE)
        sv_list = ft.Column(spacing=8)
        sv_hint = ft.Text("", size=12, color=ft.Colors.ERROR)

        def source_state(name):
            st = prefs["src_status"].get(name)
            if not st:
                return 3, ft.Colors.OUTLINE, "Mai controllata: tocca «Cerca nuovi interpelli»"
            if not st.get("ok"):
                return 0, ft.Colors.ERROR, f"Non risponde: {st.get('err') or 'errore sconosciuto'}"
            if not st.get("found"):
                return 1, "#E08A00", "Risponde ma non trova avvisi (pagina cambiata o nessun interpello)"
            return 2, GREEN, f"{st['found']} avvisi trovati" + (f", {st['new']} nuovi" if st.get("new") else "")

        def sources_report():
            lines = []
            names = [n for srcs in SOURCES.values() for n, *_ in srcs] + [c["n"] for c in prefs["sources"]]
            for n in names:
                o, _c, msg = source_state(n)
                if o <= 1:
                    lines.append(f"- {n}: {msg}")
            return "Fonti con problemi:\n" + "\n".join(lines) if lines else "Tutte le fonti rispondono."

        def paint_sources():
            entries = []
            for reg, srcs in SOURCES.items():
                for n, u, *_ in srcs:
                    entries.append((n, u, False))
            entries += [(c["n"], c["u"], True) for c in prefs["sources"]]
            ranked = sorted(entries, key=lambda x: (source_state(x[0])[0], x[0]))
            counts = [0, 0, 0, 0]
            rows = []
            for n, u, is_custom in ranked:
                o, color, msg = source_state(n)
                counts[o] += 1
                trailing = []
                if is_custom:
                    trailing.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=20,
                                                  tooltip="Togli la fonte",
                                                  on_click=lambda e, n=n: remove_source(n)))
                rows.append(ft.Container(
                    border_radius=14, padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Container(width=10, height=10, border_radius=5, bgcolor=color),
                        ft.Column(expand=True, spacing=0, controls=[
                            ft.Text(n + ("  (tua)" if is_custom else ""), size=13.5, weight=ft.FontWeight.W_700),
                            ft.Text(msg, size=11.5, color=ft.Colors.ON_SURFACE_VARIANT)]),
                        *trailing])))
            sv_list.controls = rows
            sv_summary.value = (f"{counts[2]} funzionano · {counts[1]} senza avvisi · {counts[0]} non rispondono"
                                + (f" · {counts[3]} da controllare" if counts[3] else ""))

        def add_source(e=None):
            name = (sv_name.value or "").strip()
            url = (sv_url.value or "").strip()
            if not name or not re.match(r"^https?://\S+\.\S+", url):
                sv_hint.value = "Scrivi un nome e un indirizzo completo che inizi con https://"
                page.update()
                return
            if any(c["n"].lower() == name.lower() for c in prefs["sources"]) or \
               any(name.lower() == n.lower() for srcs in SOURCES.values() for n, *_ in srcs):
                sv_hint.value = "Esiste già una fonte con questo nome."
                page.update()
                return
            prefs["sources"] = (prefs["sources"] + [{"n": name[:40], "u": url[:300]}])[:30]
            sv_name.value = sv_url.value = ""
            sv_hint.value = ""
            save_prefs()
            paint_sources()
            page.update()
            notify("Fonte aggiunta: la leggo al prossimo «Cerca nuovi interpelli».")

        def remove_source(name):
            prefs["sources"] = [c for c in prefs["sources"] if c["n"] != name]
            prefs["src_status"].pop(name, None)
            save_prefs()
            paint_sources()
            page.update()

        def copy_report(e=None):
            try:
                page.run_task(clipboard.set, sources_report())
                notify("Rapporto copiato.")
            except Exception:
                notify("Copia non riuscita.")

        def close_sources(e=None):
            sources_view.visible = False
            home_view.visible = True
            page.update()

        def open_sources(e=None):
            paint_sources()
            home_view.visible = False
            sources_view.visible = True
            page.update()

        sources_button.on_click = open_sources

        sources_header = ft.Container(
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[BRAND_DARK, BRAND_LIGHT]),
            padding=ft.Padding.only(left=6, right=18, top=18, bottom=18),
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            content=ft.Column(spacing=4, controls=[
                ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=26,
                                  tooltip="Indietro", on_click=close_sources),
                    ft.Column(expand=True, spacing=0, controls=[
                        ft.Text("Fonti degli interpelli", size=20, weight=ft.FontWeight.W_800,
                                color=ft.Colors.WHITE),
                        ft.Text("Quali siti rispondono e quali no", size=12,
                                color=ft.Colors.with_opacity(0.88, ft.Colors.WHITE))])]),
                ft.Container(padding=ft.Padding.only(left=16), content=sv_summary)]))

        sources_body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
            ft.Container(padding=ft.Padding.only(left=16, right=16, top=16, bottom=28), content=ft.Column(
                spacing=14, controls=[
                    section_card([
                        ft.Text("Aggiungi una fonte", size=14, weight=ft.FontWeight.W_700),
                        ft.Text("Incolla l'indirizzo della pagina degli interpelli di una scuola, di un ambito o di un "
                                "ufficio, meglio se è un feed RSS (di solito finisce con /feed/). L'app la leggerà "
                                "insieme alle altre.", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        sv_name, sv_url, sv_hint,
                        ft.FilledButton(content="Aggiungi", icon=ft.Icons.ADD_ROUNDED, on_click=add_source)]),
                    ft.TextButton(content="Copia l'elenco delle fonti con problemi",
                                  icon=ft.Icons.CONTENT_COPY_ROUNDED, on_click=copy_report),
                    sv_list]))])
        sources_view = ft.Column(expand=True, spacing=0, visible=False, controls=[sources_header, sources_body])

        _go_back_radar = go_back

        def go_back(e=None):
            if sources_view.visible:
                close_sources()
                return True
            return _go_back_radar(e)

        for _name in ("on_back_button", "on_view_pop"):
            try:
                setattr(page, _name, go_back)
            except Exception:
                pass

        # ---- Menù: tutte le funzioni in una pagina ---------------------------------------
        info_dlg = ft.AlertDialog(
            title=ft.Text("Informazioni"),
            content=ft.Column(tight=True, spacing=10, controls=[
                ft.Text("Interpelli Scuola raccoglie gli avvisi pubblicati dagli Uffici Scolastici e dalle scuole, "
                        "e li mostra in un posto solo.", size=13),
                ft.Text("Le stime GPS (province, riserva del 15%, punteggio) sono indicative: fanno fede gli "
                        "Uffici Scolastici e i bollettini ufficiali.", size=13),
                ft.Text("L'app non è collegata né affiliata al Ministero dell'Istruzione e del Merito. "
                        "Non raccoglie dati personali: classi e preferenze restano sul tuo telefono.",
                        size=13)]),
            actions=[ft.TextButton("Chiudi", on_click=lambda e: close_dialog(info_dlg))])

        theme_label = {"": "Come il telefono", "light": "Chiaro", "dark": "Scuro"}
        theme_sub = ft.Text(theme_label[prefs["theme"]], size=11.5, color=ft.Colors.ON_SURFACE_VARIANT)

        def cycle_theme(e=None):
            nxt = {"": "light", "light": "dark", "dark": ""}[prefs["theme"]]
            prefs["theme"] = nxt
            theme_sub.value = theme_label[nxt]
            apply_theme()
            save_prefs()
            page.update()

        def hide_all_pages():
            for v in (gps_view, calc_view, radar_view, sources_view, menu_view):
                v.visible = False

        def open_menu(e=None):
            hide_all_pages()
            home_view.visible = False
            menu_greeting.value = (f"Ciao {prefs['name'].split()[0]}!" if prefs["name"].strip() else "Cosa vuoi fare?")
            menu_view.visible = True
            page.update()

        def close_menu(e=None):
            menu_view.visible = False
            home_view.visible = True
            page.update()

        def open_menu_item(fn):
            """Apre una pagina partendo dalla home o dal menù."""
            menu_view.visible = False
            fn()

        def menu_goto_home(profile=""):
            menu_view.visible = False
            home_view.visible = True
            state["profile"] = profile
            paint_pills()
            page.update()
            load_results(reset=True)

        def menu_tile(icon, title, sub, handler, color=BRAND_LIGHT):
            return ft.Container(
                expand=True, ink=True, border_radius=22, height=122, on_click=handler,
                padding=14, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                content=ft.Column(spacing=2, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Container(width=40, height=40, border_radius=13, alignment=ft.Alignment.CENTER,
                                 bgcolor=ft.Colors.with_opacity(0.14, color), content=ft.Icon(icon, size=24, color=color)),
                    ft.Column(spacing=0, controls=[
                        ft.Text(title, size=14.5, weight=ft.FontWeight.W_800),
                        sub if isinstance(sub, ft.Control) else
                        ft.Text(sub, size=11.5, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=2)])]))

        menu_greeting = ft.Text("Cosa vuoi fare?", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE)
        menu_header = ft.Container(
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[BRAND_DARK, BRAND_LIGHT]),
            padding=ft.Padding.only(left=6, right=18, top=18, bottom=18),
            border_radius=ft.BorderRadius.only(bottom_left=28, bottom_right=28),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, icon_size=26,
                              tooltip="Indietro", on_click=close_menu),
                ft.Column(expand=True, spacing=0, controls=[
                    menu_greeting,
                    ft.Text("Tutte le funzioni dell'app", size=12,
                            color=ft.Colors.with_opacity(0.88, ft.Colors.WHITE))])]))

        def menu_label(text):
            return ft.Text(text, size=12, weight=ft.FontWeight.W_700, color=ft.Colors.ON_SURFACE_VARIANT)

        menu_body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
            ft.Container(padding=ft.Padding.only(left=16, right=16, top=16, bottom=28), content=ft.Column(
                spacing=12, controls=[
                    menu_label("INTERPELLI"),
                    ft.Row(spacing=12, controls=[
                        menu_tile(ft.Icons.HOME_ROUNDED, "Interpelli", "Tutti gli avvisi, con ricerca e filtri",
                                  lambda e: menu_goto_home("")),
                        menu_tile(ft.Icons.STAR_ROUNDED, "Per me", "Solo le tue classi di concorso",
                                  lambda e: menu_goto_home("ME") if prefs["classes"] else (close_menu(), open_settings()),
                                  GOLD)]),
                    ft.Row(spacing=12, controls=[
                        menu_tile(ft.Icons.BOOKMARK_ROUNDED, "Salvati", "Preferiti e candidature inviate",
                                  lambda e: menu_goto_home("SAVED"), GREEN),
                        menu_tile(ft.Icons.RADAR_ROUNDED, "Radar opportunità", "Province con interpelli per te",
                                  lambda e: open_menu_item(open_radar), "#E8590C")]),
                    menu_label("GPS"),
                    ft.Row(spacing=12, controls=[
                        menu_tile(ft.Icons.TRAVEL_EXPLORE_ROUNDED, "Dove fare le GPS", "Province e riserva del 15%",
                                  lambda e: open_menu_item(open_gps)),
                        menu_tile(ft.Icons.CALCULATE_ROUNDED, "Calcola punteggio", "Titoli, servizio, certificazioni",
                                  lambda e: open_menu_item(lambda: open_calc(from_home=True)))]),
                    menu_label("APP"),
                    ft.Row(spacing=12, controls=[
                        menu_tile(ft.Icons.TUNE_ROUNDED, "Le mie classi", "Classi, nome per le candidature",
                                  lambda e: open_settings(), BRAND_DARK),
                        menu_tile(ft.Icons.RSS_FEED_ROUNDED, "Fonti", "Quali siti rispondono",
                                  lambda e: open_menu_item(open_sources), "#6B7280")]),
                    ft.Row(spacing=12, controls=[
                        menu_tile(ft.Icons.DARK_MODE_ROUNDED, "Aspetto", theme_sub, cycle_theme, "#7048E8"),
                        menu_tile(ft.Icons.INFO_OUTLINE_ROUNDED, "Informazioni", "Avvertenze e privacy",
                                  lambda e: show_dialog(info_dlg), "#6B7280")]),
                ]))])
        menu_view = ft.Column(expand=True, spacing=0, visible=False, controls=[menu_header, menu_body])

        _go_back_sources = go_back

        def go_back(e=None):
            if menu_view.visible:
                close_menu()
                return True
            return _go_back_sources(e)

        for _name in ("on_back_button", "on_view_pop"):
            try:
                setattr(page, _name, go_back)
            except Exception:
                pass

        disclaimer = ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text("Le stime GPS sono indicative: fanno fede gli Uffici Scolastici. "
                        "L'app non è collegata al Ministero dell'Istruzione e del Merito.",
                        size=10.5, color=ft.Colors.ON_SURFACE_VARIANT, expand=True),
            ]),
        )
        page.add(home_view, gps_view, calc_view, radar_view, sources_view, menu_view, disclaimer)
        load_results(reset=True)

        # Primo avvio: se non c'è ancora nulla, scarica subito.
        try:
            conn = db_connect()
            empty = conn.execute("SELECT COUNT(*) FROM interpelli").fetchone()[0] == 0
            conn.close()
        except sqlite3.Error:
            empty = False
        if empty:
            refresh()

    except Exception as ex:
        print(f"Errore generale nell'app: {ex}")
        raise


async def main(page: ft.Page):
    raw = None
    try:
        raw = await ft.SharedPreferences().get("prefs")
    except Exception:
        pass
    build(page, raw)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
