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
from urllib.parse import urljoin
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
PAGE_SIZE = 25          # interpelli mostrati per "blocco"
DB_VERSION = 5          # alzare per forzare il rifacimento della cache
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
    (re.compile(r"personale\s+educativ\w*|educatric[ei]|educator[ei]\s+(?:di\s+)?convitt\w*", re.I), "PPPP"),
    (re.compile(r"educazione\s+motoria|\bed\.?\s*motoria|insegnante\s+di\s+motoria", re.I), "EEEM"),
]
# Parole di ricerca che rimandano a una classe (es. cercando "motoria" trova EEEM)
CDC_SEARCH_ALIASES = {
    "motoria": "EEEM", "motorie": "EEEM",
    "educativo": "PPPP", "educativi": "PPPP", "educativa": "PPPP", "educatore": "PPPP", "educatori": "PPPP",
}
_CDC_SPECIAL_RE = re.compile(r"\b(" + "|".join(CDC_SPECIAL) + r")\b", re.I)
_CDC_CODE_RE = re.compile(r"\b(?<![A-Za-z0-9])([A-Z]\d{2,3}|[A-Z]{2}\d{2})(?![A-Za-z0-9])")
_CDC_BAD_PREFIX = ("L", "D", "N")      # L.107, D25, n123: leggi/decreti/numeri, non classi


def _codes_in(text, limit=3):
    """Codici di classe in ordine di apparizione, senza doppioni."""
    found = []
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
    for _, code in sorted(spans):
        if code not in found:
            found.append(code)
        if len(found) >= limit:
            break
    return found


def detect_cdc(title, body=""):
    """Classi di concorso: prima quelle scritte nel titolo, poi quelle nell'inizio del testo."""
    codes = _codes_in(title or "")
    if not codes and body:
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


def detect_target(title, body=""):
    """'ATA' solo con una dicitura ATA esplicita; se compare una classe di concorso da docente, è DOCENTI."""
    title = title or ""
    title_ata = ATA_TITLE_RE.search(title)
    title_cdc = _codes_in(title)
    if title_ata and not title_cdc:
        return "ATA"
    if title_cdc:
        return "DOCENTI"

    # titolo neutro: guarda l'inizio del testo e decide per ciò che compare per primo
    head = (body or "")[:2500]
    body_ata = ATA_BODY_RE.search(head)
    body_cdc = _codes_in(head, limit=1)
    if body_ata and body_cdc:
        first_cdc = min(m.start() for m in [_CDC_SPECIAL_RE.search(head), _CDC_CODE_RE.search(head)] if m) \
            if (_CDC_SPECIAL_RE.search(head) or _CDC_CODE_RE.search(head)) else 10**9
        return "ATA" if body_ata.start() < first_cdc else "DOCENTI"
    if body_ata:
        return "ATA"
    return "DOCENTI"


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


def parse_source_page(region, source_name, url, known):
    """Scarica una pagina-fonte e restituisce (nuovi_interpelli, raggiungibile).

    Gli avvisi già presenti nel database (`known`) non vengono riscaricati:
    questo rende gli aggiornamenti successivi al primo molto più veloci.
    """
    items = []
    try:
        html_content = fetch_url(url)
    except Exception:
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

    links = re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_content, re.I | re.S)
    for href, txt in links:
        title = clean_text(txt)
        if len(title) > 6 and any(k in title.lower() for k in ["interpell", "supplenz", "avviso", "graduatoria", "docente", "ata", "dsga"]):
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
        return ("Scadenza non indicata", ft.colors.SURFACE_VARIANT, ft.colors.ON_SURFACE_VARIANT,
                ft.icons.SCHEDULE_ROUNDED)
    days = (d - date.today()).days
    if days < 0:
        return (f"Scaduto il {fmt_short(d)}", ft.colors.SURFACE_VARIANT, ft.colors.OUTLINE,
                ft.icons.EVENT_BUSY_ROUNDED)
    if days == 0:
        return ("Scade oggi", ft.colors.ERROR_CONTAINER, ft.colors.ON_ERROR_CONTAINER,
                ft.icons.TIMER_ROUNDED)
    if days == 1:
        return ("Scade domani", ft.colors.ERROR_CONTAINER, ft.colors.ON_ERROR_CONTAINER,
                ft.icons.TIMER_ROUNDED)
    if days <= 3:
        return (f"Scade tra {days} giorni", ft.colors.ERROR_CONTAINER, ft.colors.ON_ERROR_CONTAINER,
                ft.icons.TIMER_ROUNDED)
    return (f"Scade il {fmt_short(d)}", ft.colors.TERTIARY_CONTAINER, ft.colors.ON_TERTIARY_CONTAINER,
            ft.icons.EVENT_AVAILABLE_ROUNDED)


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
def main(page: ft.Page):
    try:
        page.title = "Interpelli Scuola"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.theme = ft.Theme(color_scheme_seed=BRAND_LIGHT, use_material3=True)
        page.dark_theme = ft.Theme(color_scheme_seed=BRAND_LIGHT, use_material3=True)
        page.padding = 0
        page.spacing = 0
        try:
            page.window_width = 420
            page.window_height = 820
        except Exception:
            pass

        init_db()

        state = {"profile": "", "region": "", "status": "", "shown": 0, "refreshing": False}
        timers = {"search": None}

        # ---- Preferenze dell'utente (classi di concorso, dati per le candidature)
        prefs = {"classes": [], "name": "", "phone": ""}

        def load_prefs():
            try:
                raw = page.client_storage.get("prefs")
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    classes = data.get("classes", [])
                    if isinstance(classes, list):
                        prefs["classes"] = [c for c in classes if isinstance(c, str)]
                    for key in ("name", "phone"):
                        if isinstance(data.get(key), str):
                            prefs[key] = data[key]
            except Exception:
                pass

        def save_prefs():
            try:
                page.client_storage.set("prefs", json.dumps(prefs))
            except Exception:
                pass

        load_prefs()

        # ---- Intestazione con logo e ricerca -------------------------------
        refresh_button = ft.IconButton(
            icon=ft.icons.SYNC_ROUNDED,
            icon_color=ft.colors.WHITE,
            icon_size=24,
            tooltip="Aggiorna interpelli",
            style=ft.ButtonStyle(bgcolor=ft.colors.with_opacity(0.16, ft.colors.WHITE)),
        )

        settings_button = ft.IconButton(
            icon=ft.icons.TUNE_ROUNDED,
            icon_color=ft.colors.WHITE,
            icon_size=24,
            tooltip="Le mie classi e i miei dati",
            style=ft.ButtonStyle(bgcolor=ft.colors.with_opacity(0.16, ft.colors.WHITE)),
        )

        clear_button = ft.IconButton(icon=ft.icons.CLOSE_ROUNDED, icon_size=18, visible=False,
                                     icon_color="#6B7280")

        search_input = ft.TextField(
            hint_text="Cerca classe di concorso, ruolo, ufficio…",
            hint_style=ft.TextStyle(color="#6B7280", size=14),
            text_style=ft.TextStyle(color="#111827", size=14),
            prefix_icon=ft.icons.SEARCH_ROUNDED,
            suffix=clear_button,
            filled=True,
            fill_color=ft.colors.with_opacity(0.96, ft.colors.WHITE),
            border=ft.InputBorder.NONE,
            border_radius=16,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=14),
            cursor_color=BRAND_LIGHT,
        )

        header = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[BRAND_DARK, BRAND_LIGHT],
            ),
            padding=ft.padding.only(left=18, right=14, top=22, bottom=18),
            border_radius=ft.border_radius.only(bottom_left=28, bottom_right=28),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Image(src="logo.png", width=46, height=46, border_radius=12),
                            ft.Column(
                                expand=True, spacing=0,
                                controls=[
                                    ft.Text("Interpelli Scuola", size=21, weight=ft.FontWeight.W_800,
                                            color=ft.colors.WHITE),
                                    ft.Text("Supplenze in tutta Italia, in un tocco",
                                            size=12, color=ft.colors.with_opacity(0.85, ft.colors.WHITE)),
                                ],
                            ),
                            settings_button,
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
            btn = ft.ElevatedButton(
                text=label,
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
                    bgcolor=ft.colors.PRIMARY if active else ft.colors.SURFACE_VARIANT,
                    color=ft.colors.ON_PRIMARY if active else ft.colors.ON_SURFACE_VARIANT,
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    elevation=0,
                )

        pills_row = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                make_pill("", "Tutti", ft.icons.APPS_ROUNDED),
                make_pill("DOCENTI", "Docenti", ft.icons.SCHOOL_ROUNDED),
                make_pill("ATA", "ATA", ft.icons.WORK_ROUNDED),
                make_pill("ME", "Per me", ft.icons.STAR_ROUNDED),
            ],
        )

        region_options = [ft.dropdown.Option("", "Tutta Italia")]
        for reg in sorted(SOURCES.keys()):
            region_options.append(ft.dropdown.Option(reg, reg))

        # Stessa configurazione del Dropdown originale (che funzionava),
        # direttamente in colonna e a larghezza piena.
        region_dropdown = ft.Dropdown(
            label="Regione",
            options=region_options,
            value="",
            border_radius=14,
            filled=True,
            border_color=ft.colors.TRANSPARENT,
        )

        status_dropdown = ft.Dropdown(
            label="Stato",
            options=[
                ft.dropdown.Option("", "Tutti gli stati"),
                ft.dropdown.Option("active", "Attivi"),
                ft.dropdown.Option("soon", f"In scadenza (entro {SOON_DAYS} giorni)"),
                ft.dropdown.Option("expired", "Scaduti"),
            ],
            value="",
            border_radius=14,
            filled=True,
            border_color=ft.colors.TRANSPARENT,
        )

        classes_text = ft.Text("", size=12, color=ft.colors.ON_SURFACE_VARIANT)

        filters = ft.Container(
            padding=ft.padding.only(left=16, right=16, top=14, bottom=4),
            content=ft.Column(
                spacing=10,
                controls=[pills_row, classes_text, region_dropdown, status_dropdown],
            ),
        )

        # ---- Stato / progresso ---------------------------------------------
        status_text = ft.Text("", size=12, color=ft.colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.W_500,
                              expand=True)
        progress_bar = ft.ProgressBar(value=0, visible=False, bar_height=3, border_radius=3)
        status_row = ft.Container(
            padding=ft.padding.symmetric(horizontal=18, vertical=6),
            content=ft.Column(spacing=6, controls=[progress_bar, ft.Row([status_text])]),
        )

        # ---- Lista risultati -----------------------------------------------
        results = ft.ListView(expand=True, spacing=10,
                              padding=ft.padding.only(left=16, right=16, top=4, bottom=28))

        more_button = ft.Container(
            alignment=ft.alignment.center,
            padding=ft.padding.only(top=6, bottom=6),
            content=ft.FilledTonalButton(
                text="Mostra altri", icon=ft.icons.EXPAND_MORE_ROUNDED,
                on_click=lambda e: load_results(reset=False),
            ),
        )

        def empty_state(db_empty):
            if state["refreshing"]:
                return ft.Container(
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=48, left=24, right=24),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
                        controls=[
                            ft.ProgressRing(width=34, height=34, stroke_width=4),
                            ft.Text("Sto cercando gli interpelli…", size=16, weight=ft.FontWeight.W_700,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text("I risultati compaiono qui man mano che li trovo.", size=13,
                                    color=ft.colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                        ],
                    ),
                )
            if db_empty:
                title, sub = "Nessun interpello scaricato", "Tocca il pulsante per scaricare gli avvisi di tutta Italia."
                action = ft.FilledButton("Scarica interpelli", icon=ft.icons.CLOUD_DOWNLOAD_ROUNDED,
                                         on_click=lambda e: refresh())
            else:
                title, sub = "Nessun risultato", "Prova a cambiare ricerca o filtri."
                action = ft.TextButton("Azzera filtri", on_click=lambda e: reset_filters())
            return ft.Container(
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=48, left=24, right=24),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
                    controls=[
                        ft.Icon(ft.icons.SEARCH_OFF_ROUNDED, size=56, color=ft.colors.OUTLINE),
                        ft.Text(title, size=16, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
                        ft.Text(sub, size=13, color=ft.colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
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
                padding=ft.padding.symmetric(horizontal=9, vertical=4),
                border_radius=8,
            )

        def meta_row(icon, text):
            return ft.Row(
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(icon, size=14, color=ft.colors.OUTLINE),
                    ft.Text(text, size=12, color=ft.colors.ON_SURFACE_VARIANT, expand=True,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ],
            )

        def open_url(url):
            try:
                page.launch_url(url)
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
                      ft.colors.SECONDARY_CONTAINER if is_ata else ft.colors.PRIMARY_CONTAINER,
                      ft.colors.ON_SECONDARY_CONTAINER if is_ata else ft.colors.ON_PRIMARY_CONTAINER,
                      ft.icons.WORK_ROUNDED if is_ata else ft.icons.SCHOOL_ROUNDED),
            ]
            for code in [c.strip() for c in (cdc or "").split(",") if c.strip()]:
                chips.append(badge(cdc_label(code), ft.colors.SURFACE_VARIANT, ft.colors.ON_SURFACE_VARIANT))
            if mine:
                chips.append(badge("PER TE", GOLD, "#3B2A00", ft.icons.STAR_ROUNDED))
            if is_new(published):
                chips.append(badge("NUOVO", GREEN, ft.colors.WHITE))
            if verified:
                chips.append(badge("Date verificate", ft.colors.SURFACE_VARIANT, GREEN, ft.icons.VERIFIED_ROUNDED))

            body = [
                ft.Row(chips, spacing=6, wrap=True, run_spacing=6),
                ft.Text(title, size=14, weight=ft.FontWeight.W_600, max_lines=4,
                        overflow=ft.TextOverflow.ELLIPSIS),
                meta_row(ft.icons.PLACE_ROUNDED, f"{source} · {region}"),
                meta_row(ft.icons.CALENDAR_TODAY_ROUNDED,
                         f"Pubblicato il {fmt_date(published)}" if published else "Data di pubblicazione non indicata"),
            ]
            if post_type and post_type != "Non specificato":
                body.append(meta_row(ft.icons.WORK_OUTLINE_ROUNDED, post_type))
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
                                        color=ft.colors.PRIMARY),
                                ft.Icon(ft.icons.OPEN_IN_NEW_ROUNDED, size=15, color=ft.colors.PRIMARY),
                            ],
                        ),
                    ],
                )
            )

            # Azioni come sul sito: documento originale e candidatura via email
            actions = []
            if doc_url:
                actions.append(ft.TextButton(text="Documento", icon=ft.icons.DOWNLOAD_ROUNDED, url=doc_url))
            if email and status != "expired":
                mailto = build_mailto(email, title, cdc, prefs["name"] or "Candidato", prefs["phone"])
                actions.append(ft.TextButton(text="Candidati", icon=ft.icons.MAIL_OUTLINE_ROUNDED, url=mailto))
            if actions:
                body.append(ft.Row(actions, spacing=4, wrap=True))

            return ft.Container(
                content=ft.Column(body, spacing=8),
                padding=14,
                border_radius=18,
                bgcolor=ft.colors.SURFACE_VARIANT,
                border=ft.border.all(1.5, STATUS_COLORS[status]) if status in ("active", "soon") else None,
                opacity=0.7 if status == "expired" else 1,
                ink=True,
                data=url,
                on_click=lambda e, u=url: open_interpello(u),
            )

        # ---- Apertura di un interpello: rilegge le date sulla pagina ----------
        detail_title = ft.Text("", size=15, weight=ft.FontWeight.W_700, max_lines=4,
                               overflow=ft.TextOverflow.ELLIPSIS)
        detail_body = ft.Column(tight=True, spacing=10)
        detail_open_btn = ft.FilledButton("Apri avviso", icon=ft.icons.OPEN_IN_NEW_ROUNDED)
        detail_close_btn = ft.TextButton("Chiudi")
        detail_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Controllo dell'avviso"),
            content=ft.Column(tight=True, spacing=12, controls=[detail_title, detail_body]),
            actions=[detail_close_btn, detail_open_btn],
        )

        def close_detail(e=None):
            detail_dlg.open = False
            page.update()

        def go_to_notice(url):
            close_detail()
            open_url(url)

        detail_close_btn.on_click = close_detail

        def date_line(icon, label, value_text, note, color=None):
            col = [ft.Text(value_text, size=14, weight=ft.FontWeight.W_700, color=color)]
            if note:
                col.append(ft.Text(note, size=11, color=ft.colors.ON_SURFACE_VARIANT, italic=True))
            return ft.Row(
                spacing=10, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(icon, size=20, color=ft.colors.PRIMARY),
                    ft.Column(spacing=1, tight=True, expand=True,
                              controls=[ft.Text(label, size=11, color=ft.colors.ON_SURFACE_VARIANT)] + col),
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
                    date_line(ft.icons.CALENDAR_TODAY_ROUNDED, "Pubblicazione",
                              fmt_date(stored_pub) if stored_pub else "Non indicata",
                              "Non verificata: la pagina non risponde"),
                    date_line(ft.icons.EVENT_BUSY_ROUNDED, "Scadenza",
                              fmt_date(stored_deadline) if stored_deadline else "Non indicata",
                              "Non verificata: la pagina non risponde"),
                    ft.Text("Controlla la connessione e riprova, oppure apri l'avviso e verifica le date.",
                            size=12, color=ft.colors.ON_SURFACE_VARIANT),
                ]
                return

            pub, deadline = info["published"], info["deadline"]
            d_text, _, _, _ = deadline_info(deadline)
            lines = [
                date_line(ft.icons.CALENDAR_TODAY_ROUNDED, "Data di pubblicazione",
                          fmt_date(pub) if pub else "Non trovata nella pagina",
                          f"Letta da: {info['published_src']}" if pub else "Controllala nell'avviso"),
                date_line(ft.icons.EVENT_BUSY_ROUNDED, "Scadenza per la candidatura",
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
            lines.append(date_line(ft.icons.BADGE_ROUNDED, "Profilo e classe di concorso",
                                   profile + (f" · {cdc_txt}" if cdc_txt else ""), note))
            if info.get("doc_url"):
                lines.append(ft.Text("Nell'avviso è presente un allegato: se la scadenza è indicata solo lì, "
                                     "controllala nel documento.", size=11, color=ft.colors.ON_SURFACE_VARIANT))
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
            page.dialog = detail_dlg
            detail_dlg.open = True
            page.update()

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
                        f"FROM interpelli WHERE {where} ORDER BY published DESC, id DESC LIMIT ? OFFSET ?",
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
                            results.scroll_to(offset=0, duration=0)
                        except Exception:
                            pass
                    page.update()
                except Exception as ex:
                    status_text.value = f"Errore nel caricamento: {ex}"
                    page.update()

        # ---- Eventi filtri --------------------------------------------------
        def refresh_classes_text():
            if prefs["classes"]:
                classes_text.value = "Le mie classi: " + ", ".join(prefs["classes"])
            else:
                classes_text.value = "Tocca ⚙ in alto per scegliere le tue classi di concorso"

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
            helper_text="Separale con virgole o spazi",
        )
        name_field = ft.TextField(label="Nome e cognome (per le candidature)")
        phone_field = ft.TextField(label="Telefono (facoltativo)")

        def close_settings(e=None):
            dlg.open = False
            page.update()

        def save_settings(e=None):
            prefs["classes"] = parse_classes(classes_field.value)
            prefs["name"] = (name_field.value or "").strip()
            prefs["phone"] = (phone_field.value or "").strip()
            save_prefs()
            refresh_classes_text()
            if state["profile"] == "ME" and not prefs["classes"]:
                state["profile"] = ""
                paint_pills()
            dlg.open = False
            page.update()
            load_results(reset=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Le mie classi"),
            content=ft.Column(
                tight=True, spacing=12,
                controls=[
                    ft.Text("Usale col filtro «Per me» e per ricevere l'avviso sui nuovi interpelli "
                            "che ti riguardano.", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                    classes_field, name_field, phone_field,
                ],
            ),
            actions=[ft.TextButton("Annulla", on_click=close_settings),
                     ft.FilledButton("Salva", on_click=save_settings)],
        )

        def open_settings(e=None):
            classes_field.value = ", ".join(prefs["classes"])
            name_field.value = prefs["name"]
            phone_field.value = prefs["phone"]
            page.dialog = dlg
            dlg.open = True
            page.update()

        settings_button.on_click = open_settings

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
        region_dropdown.on_change = on_region
        status_dropdown.on_change = on_status

        # ---- Aggiornamento fonti -------------------------------------------
        def notify(message):
            try:
                page.snack_bar = ft.SnackBar(ft.Text(message), behavior=ft.SnackBarBehavior.FLOATING)
                page.snack_bar.open = True
                page.update()
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
        paint_pills()
        refresh_classes_text()
        page.add(
            ft.Column(
                expand=True, spacing=0,
                controls=[header, filters, status_row, results],
            )
        )
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


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
