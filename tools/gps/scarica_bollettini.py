#!/usr/bin/env python3
"""Scarica da soli i nuovi bollettini di nomina GPS dalle pagine degli Uffici scolastici.

Gira su GitHub Actions (vedi .github/workflows/aggiorna-gps.yml), non sul telefono. Guarda le stesse pagine
delle fonti dell'app più quelle elencate in tools/gps/pagine_bollettini.json, cerca gli avvisi che parlano di
«bollettino» / «nomine» e scarica gli allegati PDF o Excel nella cartella `bollettini/`. Poi il passo successivo
del workflow li legge, aggiorna assets/gps_data.json e li butta via: nel repository restano solo dati aggregati,
mai i nomi dei candidati. Gli indirizzi già visti si ricordano in tools/gps/bollettini_visti.json (solo URL).

Uso:  python tools/gps/scarica_bollettini.py --cartella bollettini [--prova]
"""
import argparse
import json
import os
import re
import ssl
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from importlib import util
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
VISTI = Path(__file__).with_name("bollettini_visti.json")
EXTRA = Path(__file__).with_name("pagine_bollettini.json")
MAX_BYTES = 60_000_000
DOC_RE = re.compile(r"\.(pdf|xlsx|xlsm)(?:$|[?#])", re.I)
# Un avviso è un bollettino GPS solo se dice «bollettino» o «nomine (a tempo determinato / da GPS)».
TITLE_RE = re.compile(r"bollettin\w*|\bnomin[ae]\s+(?:a\s+tempo\s+determinato|da\s+gps|gps|supplenz\w*)|\bnomine\s+gps\b", re.I)
GPS_RE = re.compile(r"\bgps\b|graduatori\w*\s+provincial|supplenz|docent|sostegno|tempo\s+determinato", re.I)
# ...e non se parla d'altro (immissioni in ruolo, GAE, interpelli, rettifiche, disponibilità, decreti, ATA).
SKIP_RE = re.compile(r"\bata\b|\bdsga\b|personale\s+ata|collaborator\w*|assistent\w*|educativ\w*|religion\w*|\birc\b|"
                     r"immission\w*|\bin\s+ruolo|\bgae\b|\bgm\b|ad\s+esaurimento|concors\w*|interpell\w*|rettific\w*|"
                     r"disponibilit\w*|decret\w*|riscontro|\bmad\b|mobilit\w*|assunzion\w*|tempo\s+indeterminato|"
                     r"\bposti\s+residu\w*|cattedre", re.I)


# Siti che ospitano più uffici: la prima parte del percorso dice quale (es. istruzionepiemonte.it/torino/).
MULTI_UFFICIO = ("istruzionepiemonte.it", "toscana.istruzione.it", "toscana-istruzione.it", "mim.gov.it")
# Dove gli uffici di solito mettono comunicazioni e notizie (il bollettino sta lì, non tra gli interpelli).
NEWS_PATHS = ("", "feed/", "category/notizie/", "category/comunicazioni/", "category/news/", "category/avvisi/",
              "notizie/", "comunicazioni/", "category/comunicati/", "category/personale-docente/")


def news_pages(sources):
    """Da ogni fonte degli interpelli ricava le pagine di notizie/comunicazioni dello stesso ufficio."""
    out, seen = [], set()
    for name, url in sources:
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.netloc:
            continue
        seg = [x for x in u.path.split("/") if x]
        prefix = ""
        if seg and any(u.netloc.lower().endswith(h) for h in MULTI_UFFICIO) and seg[0] not in ("category", "tag", "web", "feed"):
            prefix = "/" + seg[0]
        base = f"{u.scheme}://{u.netloc}{prefix}/"
        if base in seen:
            continue
        seen.add(base)
        out += [(name, base + path) for path in NEWS_PATHS]
    return out


# Pagine che raccolgono i link diretti ai bollettini di tutte le province (le rettifiche si saltano).
ELENCHI = ["https://www.orizzontescuola.it/supplenze-docenti-ecco-i-bollettini-nomine-al-31-agosto-o-30-giugno-2027-in-aggiornamento/"]
RETTIFICA_RE = re.compile(r"rettific\w*|\berrata\b|\bavviso\b.*\bmodific", re.I)
ESTERNI_NO = ("facebook.", "twitter.", "x.com", "whatsapp.", "t.me", "telegram.", "google.", "linkedin.", "instagram.",
              "youtube.", "orizzontescuola.", "mailto:", "tecnicadellascuola.", "wa.me")


def province_in(text):
    """Nome della provincia citato nel testo di un collegamento (la più lunga trovata), o None."""
    sys.path.insert(0, str(Path(__file__).parent))
    import bollettini
    t = bollettini._slug(text)
    best = None
    for prov, _reg in bollettini.SIGLE.values():
        sl = bollettini._slug(prov)
        if len(sl) >= 4 and sl in t and (best is None or len(sl) > len(bollettini._slug(best))):
            best = prov
    return best


def elenco_links(page_html, base):
    """Collegamenti ai bollettini in una pagina-elenco: [(testo, url)], senza rettifiche."""
    m = re.search(r"<article\b.*</article>", page_html, re.S | re.I)
    body = m.group(0) if m else page_html
    # Solo la sezione «I bollettini delle nomine GaE – GPS al 31 agosto e 30 giugno…»: più su ci sono altri link
    # (notizie, articoli collegati) che non c'entrano.
    h = re.search(r"bollettini\s+delle\s+nomine\s+GaE", re.sub(r"<[^>]+>", "", body), re.I)
    if h:
        tagged = re.search(r"b\s*o\s*l\s*l\s*e\s*t\s*t\s*i\s*n\s*i(?:\s|<[^>]+>|&nbsp;)+delle(?:\s|<[^>]+>|&nbsp;)+nomine(?:\s|<[^>]+>|&nbsp;)+GaE",
                           body, re.I)
        if tagged:
            body = body[tagged.start():]
    out = []
    for href, txt in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.I | re.S):
        url = urljoin(base, unescape(href))
        text = clean(txt)
        low = url.lower()
        if not low.startswith(("http://", "https://")) or any(x in low for x in ESTERNI_NO):
            continue
        label = text + " " + unquote(url.rsplit("/", 1)[-1])
        if RETTIFICA_RE.search(label):
            continue
        if DOC_RE.search(url) or TITLE_RE.search(label) or province_in(text):
            out.append((text or unquote(url.rsplit("/", 1)[-1]), url))
    return list(dict.fromkeys(out))


def load_app():
    os.environ.setdefault("FLET_APP_STORAGE_DATA", tempfile.mkdtemp())
    sys.modules.setdefault("flet", MagicMock())
    spec = util.spec_from_file_location("interpelli_app", ROOT / "main.py")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def links_of(page_html, base):
    """[(titolo, url)] dai feed RSS/Atom e dai collegamenti nel corpo della pagina."""
    out = []
    if re.search(r"<(rss|feed|channel)\b", page_html, re.I):
        for item in re.findall(r"<item\b.*?</item>|<entry\b.*?</entry>", page_html, re.S | re.I):
            t = re.search(r"<title[^>]*>(.*?)</title>", item, re.S | re.I)
            l = re.search(r"<link[^>]*>\s*([^<\s]+)\s*</link>", item, re.I) or re.search(r'<link[^>]*href="([^"]+)"', item, re.I)
            if t and l:
                out.append((clean(re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1))), urljoin(base, unescape(l.group(1)))))
    body = re.sub(r"<(script|style|nav|footer|aside)\b.*?</\1>", " ", page_html, flags=re.S | re.I)
    for href, txt in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, re.I | re.S):
        if not href.startswith(("#", "mailto:", "tel:", "javascript:")):
            out.append((clean(txt), urljoin(base, unescape(href))))
    return out


def doc_links(page_html, base):
    """Allegati PDF/Excel di una pagina, tranne quelli che dal nome non sono bollettini (decreti, rettifiche...)."""
    found = []
    for href, txt in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_html, re.I | re.S):
        if DOC_RE.search(href):
            u = urljoin(base, unescape(href))
            label = clean(txt) + " " + unquote(u.rsplit("/", 1)[-1])
            if u not in found and not SKIP_RE.search(label):
                found.append(u)
    return found


def same_site(a, b):
    ha, hb = urlparse(a).netloc.lower(), urlparse(b).netloc.lower()
    return ha == hb or (ha.endswith(".gov.it") and hb.endswith(".gov.it")) or \
        ha.removeprefix("www.") == hb.removeprefix("www.")


ROMANI = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
          "XIII": 13, "XIV": 14, "XV": 15}


def turn_of(title, fallback):
    m = re.search(r"\b(XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|IV|V|III|II|I)\b\s*[°ºª]?\s*(?i:bollettino|turno)", title)
    if m:
        return str(ROMANI[m.group(1)])
    for pat in (r"boll\w*\s*(?:n\.?|numero|nr\.?)?\s*(\d{1,2})\b", r"\b(\d{1,2})\s*[°ºª]?\s*(?:turno|bollettino|convocazione)",
                r"(?:turno|convocazione)\s*(?:n\.?\s*)?(\d{1,2})\b"):
        m = re.search(pat, title, re.I)
        if m and 1 <= int(m.group(1)) <= 30:
            return str(int(m.group(1)))
    return fallback


def sembra_bollettino_gps(path):
    """Controlla il testo: deve parlare di GPS/supplenze e non di immissioni in ruolo, GAE, concorsi."""
    if str(path).lower().endswith((".xlsx", ".xlsm")):
        return True
    try:
        import subprocess
        txt = subprocess.run(["pdftotext", "-l", "3", str(path), "-"], capture_output=True, text=True, timeout=60).stdout.lower()
    except Exception:
        return True                       # senza pdftotext non si può controllare: lo decide il lettore
    if not txt.strip():
        return True                       # PDF scansionato: lo decide il lettore
    gps = re.search(r"\bgps\b|graduatori\w*\s+provincial|supplenz|tempo\s+determinato", txt)
    bad = re.search(r"immission\w*\s+in\s+ruolo|ad\s+esaurimento|\bgae\b|tempo\s+indeterminato|interpell", txt)
    return bool(gps) and not (bad and not re.search(r"\bgps\b", txt))


def download(url, dest):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; InterpelliScuola/1.0)"})
    for ctx in (ssl.create_default_context(), None):
        try:
            if ctx is None:                       # catene incomplete di certificati: solo pagine pubbliche
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            with urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return "file troppo grande"
            if not (data[:4] == b"%PDF" or data[:2] == b"PK"):
                return "non è un PDF o un Excel"
            Path(dest).write_bytes(data)
            return None
        except ssl.SSLError:
            continue
        except Exception as ex:                   # rete, 404...
            return str(ex)[:80]
    return "errore di certificato"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cartella", default="bollettini")
    ap.add_argument("--prova", action="store_true", help="elenca cosa scaricherebbe, senza scaricare né ricordare nulla")
    ap.add_argument("--max", type=int, default=150, help="massimo di file scaricati per esecuzione")
    args = ap.parse_args(argv)

    app = load_app()
    visti = read_json(VISTI, {"urls": [], "turni": {}})
    seen = set(visti.get("urls", []))
    counters = dict(visti.get("turni", {}))
    sources = [(name, url) for srcs in app.SOURCES.values() for name, url, *_ in srcs]
    sources += [(x["nome"], x["url"]) for x in read_json(EXTRA, []) if isinstance(x, dict) and x.get("url")
                and x.get("tipo") != "elenco"]
    news = news_pages(sources)
    print(f"Pagine da guardare: {len(sources)} fonti degli interpelli + {len(news)} pagine di notizie/comunicazioni")
    sources = [(n, u, False) for n, u in sources] + [(n, u, True) for n, u in news]

    def scan(src):
        name, url, derived = src
        try:
            page = app.fetch_url(url)
        except Exception as ex:
            return name, url, [], (None if derived else str(ex)[:60])   # le pagine "provate" spesso non esistono
        cands = []
        for title, link in links_of(page, url):
            if len(title) < 8 and not DOC_RE.search(link):
                continue
            label = title + " " + unquote(link.rsplit("/", 1)[-1])
            if TITLE_RE.search(label) and GPS_RE.search(label) and not SKIP_RE.search(title):
                cands.append((title, link))
        return name, url, list(dict.fromkeys(cands)), None

    todo = []
    for url in ELENCHI + [x["url"] for x in read_json(EXTRA, []) if isinstance(x, dict) and x.get("tipo") == "elenco"]:
        try:
            page = app.fetch_url(url)
            found = elenco_links(page, url)
            print(f"Elenco {url[:70]}...: pagina di {len(page)} caratteri, {len(found)} collegamenti ai bollettini")
            for title, link in found:
                if link not in seen:
                    todo.append((province_in(title) or "Bollettino", url, title, link))
        except Exception as ex:
            print(f"[!] elenco {url[:70]}: non raggiungibile ({str(ex)[:60]})")
    n_elenco = len(todo)
    with ThreadPoolExecutor(max_workers=12) as ex:
        for name, url, cands, err in ex.map(scan, sources):
            if err:
                print(f"[!] {name}: pagina non raggiungibile ({err})")
            for title, link in cands:
                if link not in seen:
                    todo.append((name, url, title, link))
    print(f"Candidati nuovi: {len(todo)} ({n_elenco} dall'elenco, {len(todo) - n_elenco} dalle pagine degli uffici)")

    out = Path(args.cartella)
    out.mkdir(parents=True, exist_ok=True)
    got = 0
    for name, page_url, title, link in todo:
        if got >= args.max:
            break
        docs = [link] if DOC_RE.search(link) else []
        if not docs:
            try:
                docs = [d for d in doc_links(app.fetch_url(link), link) if same_site(d, link)][:4]
            except Exception as ex:
                print(f"[!] {name}: {title[:60]}: pagina non letta ({str(ex)[:50]})")
                continue
            if not docs:
                seen.add(link)            # avviso senza allegati (es. solo testo): non riprovare
                continue
        key = re.sub(r"^(USP|AT|UST|ATP)\s+", "", name, flags=re.I)
        for doc in docs:
            if doc in seen:
                continue
            turno = turn_of(title, None)
            if turno is None:                 # senza numero nel titolo: è il bollettino successivo di quell'ufficio
                counters[key] = counters.get(key, 0) + 1
                turno = str(counters[key])
            else:
                counters[key] = max(counters.get(key, 0), int(turno))
            ext = ".xlsx" if re.search(r"\.xls[xm]", doc, re.I) else ".pdf"
            fname = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_") + f"_bollettino-{turno}{ext}"
            dest, n = out / fname, 2
            while dest.exists():
                dest = out / (fname[:-len(ext)] + f"_{n}" + ext)
                n += 1
            if args.prova:
                print(f"[prova] {name}: {title[:70]} -> {dest.name}  ({doc})")
                continue
            err = download(doc, dest)
            seen.add(doc)
            if not err and not sembra_bollettino_gps(dest):
                dest.unlink(missing_ok=True)
                err = "non è un bollettino GPS (immissioni in ruolo, GAE o altro)"
            if err:
                print(f"[!] {name}: {doc}: {err}")
            else:
                got += 1
                print(f"[ok] {name}: {title[:70]} -> {dest.name}")
        seen.add(link)

    if not args.prova:
        visti = {"urls": sorted(seen)[-8000:], "turni": counters}
        VISTI.write_text(json.dumps(visti, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Scaricati {got} file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
