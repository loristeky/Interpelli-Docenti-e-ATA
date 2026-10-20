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
# Fonti (Uffici scolastici e Argo Interpelli)
# ----------------------------------------------------------------------------
PAGES_TO_FETCH = 5

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
MAX_WORKERS = 15
PAGE_SIZE = 25
DB_VERSION = 7
SOON_DAYS = 3

BRAND_DARK = "#1C248C"
BRAND_LIGHT = "#347CF6"
GOLD = "#FFC83D"
GREEN = "#16A363"


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
# Download e simulazione richieste HTTP (inclusa ricerca filtrata Argo)
# ----------------------------------------------------------------------------
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<(script|style|noscript)\b.*?</\1>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()


def _open(url, context=None, data=None, headers=None):
    default_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if headers:
        default_headers.update(headers)
    req = Request(url, data=data, headers=default_headers)
    with urlopen(req, timeout=12, context=context) as resp:
        raw = resp.read(3_000_000)
        return raw.decode(resp.headers.get_content_charset() or 'utf-8', errors='replace')


def fetch_url(url, data=None, headers=None):
    try:
        return _open(url, ssl.create_default_context(), data=data, headers=headers)
    except Exception as ex:
        reason = getattr(ex, "reason", ex)
        if isinstance(reason, ssl.SSLError) or "CERTIFICATE" in str(ex).upper():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return _open(url, ctx, data=data, headers=headers)
        raise


def fetch_argo_filtrato(provincia="", classe_concorso="", known_urls_set=None):
    """
    Simula l'invio del modulo di ricerca con filtri specifici (es. Provincia e Classe di Concorso)
    direttamente al portale di Argo Interpelli.
    """
    if known_urls_set is None:
        known_urls_set = set()
        
    url_ricerca = "https://interpelloweb.it/"
    items = []
    
    # Parametri inviati simulando l'interazione umana nel form di ricerca del sito
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


# Funzioni di supporto per parsing date, classi di concorso, target
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
    if not value:
        return None
    value = value.strip()
    if re.match(r"^[A-Za-z]{3},", value):
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


_KEY = (r"(?:entro(?:\s+e\s+non\s+oltre)?|non\s+oltre|scadenz[ae]|termine(?:\s+ultimo)?|"
        r"improrogabilmente|presentat[ae]\s+(?:dal\s+\S+\s+)?al)")
_NOSTOP = r"(?:(?!\.\s)(?!\n).)"
DEADLINE_RE = re.compile(rf"({_KEY})({_NOSTOP}{{0,110}}?)({DATE_ANY})", re.I | re.S)
APPLY_WORDS = re.compile(r"domand|candidatur|disponibilit|istanz|present|invia|trasmett|pervenir|"
                         r"comunicar|manifest|aspirant|\bMAD\b|aderir|adesion", re.I)


def find_deadline(text, published=None):
    pub = datetime.strptime(published, "%Y-%m-%d") if published else None
    default_year = pub.year if pub else date.today().year
    best = None
    for m in DEADLINE_RE.finditer(text):
        key, between, raw = m.group(1), m.group(2), m.group(3)
        iso = parse_date(raw, default_year)
        if not iso:
            continue
        d = datetime.strptime(iso, "%Y-%m-%d")
        if pub and not re.search(r"\d{4}|/\d{2}\b|\.\d{2}\b", raw) and (pub - d).days > 30:
            iso = _mk(d.year + 1, d.month, d.day) or iso
            d = datetime.strptime(iso, "%Y-%m-%d")

        before = text[max(0, m.start() - 90):m.start()]
        context = before + key + between
        score = 0
        if APPLY_WORDS.search(context):
            score += 3
        if re.search(r"\bore\b|\d{1,2}[:.]\d{2}", between):
            score += 2
        if re.match(r"(?i)entro|non\s+oltre|scadenz", key):
            score += 1
        if score >= 1 and (best is None or score > best[0]):
            a = max(0, m.start() - 25)
            snippet = text[a:m.end() + 25].strip()
            best = (score, iso, snippet)
    if best:
        return best[1], best[2]
    return None, ""


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


def main_region(page_html):
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

CDC_SPECIAL = ["ADMM", "ADSS", "ADEE", "ADAA", "AAAA", "EEEE", "EEEM", "PPPP"]
_CDC_SPECIAL_RE = re.compile(r"\b(" + "|".join(CDC_SPECIAL) + r")\b", re.I)
_CDC_CODE_RE = re.compile(r"\b(?<![A-Za-z0-9])([A-Z]\d{2,3}|[A-Z]{2}\d{2})(?![A-Za-z0-9])")
_CDC_BAD_PREFIX = ("L", "D", "N")


def _codes_in(text, limit=3):
    spans = [(m.start(), m.group(1).upper()) for m in _CDC_SPECIAL_RE.finditer(text)]
    for m in _CDC_CODE_RE.finditer(text):
        code = m.group(1)
        if code[0] in _CDC_BAD_PREFIX and code[1:].isdigit():
            continue
        if re.fullmatch(r"AR\d{2}", code):
            continue
        spans.append((m.start(), code))
    ordered = []
    for _, code in sorted(spans):
        if code not in ordered:
            ordered.append(code)
    return ordered[:limit]


def detect_cdc(title, body=""):
    codes = _codes_in(title or "")
    if not codes and body:
        codes = _codes_in(body[:2500], limit=2)
    return ", ".join(codes)


DOC_WORDS_RE = re.compile(
    r"(?:personale\s+docente|\bdocent[ei]\b|\binsegnant[ei]\b|personale\s+educativ\w*|"
    r"\beducator[ei]\b|\beducatric[ei]\b|\bcl(?:asse|\.)?\s+di\s+concorso|\bcdc\b)", re.I)


def detect_target(title, body=""):
    title = title or ""
    if DOC_WORDS_RE.search(title) or _codes_in(title):
        return "DOCENTI"
    if ATA_TITLE_RE.search(title):
        return "ATA"
    head = (body or "")[:2500]
    body_ata = ATA_BODY_RE.search(head)
    if not body_ata:
        return "DOCENTI"
    return "ATA"


DOC_RE = re.compile(r'href=["\']([^"\']+\.(?:pdf|docx?|odt)(?:\?[^"\']*)?)["\']', re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def extract_doc_url(page_html, base_url):
    found = [urljoin(base_url, h) for h in DOC_RE.findall(page_html)]
    for u in found:
        if any(k in u.lower() for k in ["interpell", "supplenz", "avviso"]):
            return u
    return found[0] if found else ""


def extract_email(text):
    emails = []
    for e in EMAIL_RE.findall(text):
        e = e.strip(".").lower()
        if e not in emails:
            emails.append(e)
    for e in emails:
        if e.endswith(".edu.it") or "istruzione.it" in e or "pec" in e:
            return e
    return emails[0] if emails else ""


def analyze_page(page_html, link, rss_published=None):
    main_html = main_region(page_html)
    text = clean_text(main_html)
    if len(text) < 3:
        main_html = strip_chrome(page_html)
        text = clean_text(main_html)
    pub, pub_src = find_published(page_html, main_html, text)
    if not pub and rss_published:
        pub, pub_src = rss_published, "elenco dell'ufficio"
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


def verify_interpello(url, rss_published=None, title=""):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            page_html = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return None
    info = analyze_page(page_html, url, rss_published)
    heading = ""
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", info.get("html", ""), re.I | re.S)
    if m:
        heading = clean_text(m.group(1))
    info["heading"] = heading
    info["not_interpello"] = False
    info["target"] = detect_target(title or heading, info["text"])
    info["cdc"] = detect_cdc(title or heading, info["text"])
    return info


# ----------------------------------------------------------------------------
# Interfaccia Grafica Flet con Filtri e Integrazione Argo
# ----------------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "Ricerca Interpelli Nazionali & Argo"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20

    init_db()

    # Controlli UI per i filtri avanzati
    provincia_dropdown = ft.Dropdown(
        label="Filtra per Provincia",
        hint_text="Seleziona provincia",
        options=[ft.dropdown.Option("Tutte")] + [ft.dropdown.Option(p) for p in SOURCES.keys() if p != "Nazionale / Piattaforme"],
        value="Tutte",
        width=250
    )

    cdc_input = ft.TextField(
        label="Classe di Concorso (es. A028)",
        hint_text="Lascia vuoto per tutti",
        width=250
    )

    status_text = ft.Text("Pronto per la ricerca.", italic=True)
    results_list = ft.ListView(expand=1, spacing=10, padding=10)

    def esegui_ricerca(e):
        status_text.value = "Ricerca in corso (con filtri Argo)..."
        results_list.controls.clear()
        page.update()

        prov = provincia_dropdown.value
        cdc = cdc_input.value.strip().upper()
        known = known_urls()

        # Esempio di chiamata con filtri su Argo Interpelli
        nuovi_da_argo = fetch_argo_filtrato(provincia=prov if prov != "Tutte" else "", classe_concorso=cdc, known_urls_set=known)

        conn = db_connect()
        c = conn.cursor()
        
        # Inserisce i risultati nel DB
        for title, url, pub in nuovi_da_argo:
            info = verify_interpello(url, pub, title)
            if info and not info.get("not_interpello"):
                try:
                    c.execute("""INSERT OR IGNORE INTO interpelli 
                        (title, url, region, source, target, published, deadline, cdc, post_type, doc_url, email, verified)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                        (title, url, prov if prov != "Tutte" else "Nazionale", "Argo Interpelli", 
                         info["target"], info["published"], info["deadline"], info["cdc"], 
                         info["post_type"], info["doc_url"], info["email"]))
                except sqlite3.Error:
                    pass
        conn.commit()

        # Legge dal DB applicando i filtri locali
        query = "SELECT title, url, region, published, deadline, cdc, target FROM interpelli WHERE 1=1"
        params = []
        if prov != "Tutte":
            query += " AND region = ?"
            params.append(prov)
        if cdc:
            query += " AND cdc LIKE ?"
            params.append(f"%{cdc}%")
        
        query += " ORDER BY published DESC LIMIT 50"
        rows = c.execute(query, params).fetchall()
        conn.close()

        results_list.controls.clear()
        if not rows:
            results_list.controls.append(ft.Text("Nessun interpello trovato con questi filtri."))
        else:
            for r in rows:
                title, url, region, pub, deadline, found_cdc, target = r
                results_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text(title, weight=ft.FontWeight.BOLD, size=16),
                                ft.Row([
                                    ft.Chip(label=ft.Text(f"Regione/Prov: {region}")),
                                    ft.Chip(label=ft.Text(f"Target: {target}")),
                                    ft.Chip(label=ft.Text(f"CDC: {found_cdc if found_cdc else 'N/D'}")),
                                ]),
                                ft.Text(f"Scadenza: {deadline or 'Non specificata'}"),
                                ft.TextButton("Apri Avviso", url=url)
                            ]),
                            padding=15
                        )
                    )
                )
        status_text.value = f"Trovati {len(rows)} interpelli."
        page.update()

    btn_cerca = ft.ElevatedButton("Avvia Ricerca Filtrata", on_click=esegui_ricerca, icon=ft.Icons.SEARCH)

    page.add(
        ft.Text("Gestione Interpelli Scolastici con Filtri", size=20, weight=ft.FontWeight.BOLD),
        ft.Row([provincia_dropdown, cdc_input, btn_cerca], alignment=ft.MainAxisAlignment.START, wrap=True),
        status_text,
        results_list
    )

if __name__ == "__main__":
    ft.app(target=main)
