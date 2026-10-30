"""Lettura dei bollettini di nomina GPS (PDF) e aggregazione per provincia, classe e fascia.

Dei bollettini si usano SOLO: classe di concorso, tipo di graduatoria (GPS), fascia, posizione,
punteggio e codice scuola (per riconoscere la provincia). Nomi e altri dati personali non vengono
letti né salvati.
"""
import os
import re
import subprocess

# Codice meccanografico (prime due lettere) -> (provincia, regione)
SIGLE = {
    "AG": ("Agrigento", "Sicilia"), "AL": ("Alessandria", "Piemonte"), "AN": ("Ancona", "Marche"),
    "AO": ("Aosta", "Valle d'Aosta"), "AP": ("Ascoli Piceno", "Marche"), "AQ": ("L'Aquila", "Abruzzo"),
    "AR": ("Arezzo", "Toscana"), "AT": ("Asti", "Piemonte"), "AV": ("Avellino", "Campania"),
    "BA": ("Bari", "Puglia"), "BG": ("Bergamo", "Lombardia"), "BI": ("Biella", "Piemonte"),
    "BL": ("Belluno", "Veneto"), "BN": ("Benevento", "Campania"), "BO": ("Bologna", "Emilia-Romagna"),
    "BR": ("Brindisi", "Puglia"), "BS": ("Brescia", "Lombardia"), "BT": ("Barletta-Andria-Trani", "Puglia"),
    "BZ": ("Bolzano", "Trentino-Alto Adige"), "CA": ("Cagliari", "Sardegna"), "CB": ("Campobasso", "Molise"),
    "CE": ("Caserta", "Campania"), "CH": ("Chieti", "Abruzzo"), "CL": ("Caltanissetta", "Sicilia"),
    "CN": ("Cuneo", "Piemonte"), "CO": ("Como", "Lombardia"), "CR": ("Cremona", "Lombardia"),
    "CS": ("Cosenza", "Calabria"), "CT": ("Catania", "Sicilia"), "CZ": ("Catanzaro", "Calabria"),
    "EN": ("Enna", "Sicilia"), "FC": ("Forlì-Cesena", "Emilia-Romagna"), "FE": ("Ferrara", "Emilia-Romagna"),
    "FG": ("Foggia", "Puglia"), "FI": ("Firenze", "Toscana"), "FM": ("Fermo", "Marche"),
    "FR": ("Frosinone", "Lazio"), "GE": ("Genova", "Liguria"), "GO": ("Gorizia", "Friuli-Venezia Giulia"),
    "GR": ("Grosseto", "Toscana"), "IM": ("Imperia", "Liguria"), "IS": ("Isernia", "Molise"),
    "KR": ("Crotone", "Calabria"), "LC": ("Lecco", "Lombardia"), "LE": ("Lecce", "Puglia"),
    "LI": ("Livorno", "Toscana"), "LO": ("Lodi", "Lombardia"), "LT": ("Latina", "Lazio"),
    "LU": ("Lucca", "Toscana"), "MB": ("Monza e Brianza", "Lombardia"), "MC": ("Macerata", "Marche"),
    "ME": ("Messina", "Sicilia"), "MI": ("Milano", "Lombardia"), "MN": ("Mantova", "Lombardia"),
    "MO": ("Modena", "Emilia-Romagna"), "MS": ("Massa-Carrara", "Toscana"), "MT": ("Matera", "Basilicata"),
    "NA": ("Napoli", "Campania"), "NO": ("Novara", "Piemonte"), "NU": ("Nuoro", "Sardegna"),
    "OR": ("Oristano", "Sardegna"), "PA": ("Palermo", "Sicilia"), "PC": ("Piacenza", "Emilia-Romagna"),
    "PD": ("Padova", "Veneto"), "PE": ("Pescara", "Abruzzo"), "PG": ("Perugia", "Umbria"),
    "PI": ("Pisa", "Toscana"), "PN": ("Pordenone", "Friuli-Venezia Giulia"), "PO": ("Prato", "Toscana"),
    "PR": ("Parma", "Emilia-Romagna"), "PT": ("Pistoia", "Toscana"), "PU": ("Pesaro e Urbino", "Marche"),
    "PV": ("Pavia", "Lombardia"), "PZ": ("Potenza", "Basilicata"), "RA": ("Ravenna", "Emilia-Romagna"),
    "RC": ("Reggio Calabria", "Calabria"), "RE": ("Reggio Emilia", "Emilia-Romagna"), "RG": ("Ragusa", "Sicilia"),
    "RI": ("Rieti", "Lazio"), "RM": ("Roma", "Lazio"), "RN": ("Rimini", "Emilia-Romagna"),
    "RO": ("Rovigo", "Veneto"), "SA": ("Salerno", "Campania"), "SI": ("Siena", "Toscana"),
    "SO": ("Sondrio", "Lombardia"), "SP": ("La Spezia", "Liguria"), "SR": ("Siracusa", "Sicilia"),
    "SS": ("Sassari", "Sardegna"), "SU": ("Sud Sardegna", "Sardegna"), "SV": ("Savona", "Liguria"),
    "TA": ("Taranto", "Puglia"), "TE": ("Teramo", "Abruzzo"), "TN": ("Trento", "Trentino-Alto Adige"),
    "TO": ("Torino", "Piemonte"), "TP": ("Trapani", "Sicilia"), "TR": ("Terni", "Umbria"),
    "TS": ("Trieste", "Friuli-Venezia Giulia"), "TV": ("Treviso", "Veneto"), "UD": ("Udine", "Friuli-Venezia Giulia"),
    "VA": ("Varese", "Lombardia"), "VB": ("Verbano-Cusio-Ossola", "Piemonte"), "VC": ("Vercelli", "Piemonte"),
    "VE": ("Venezia", "Veneto"), "VI": ("Vicenza", "Veneto"), "VR": ("Verona", "Veneto"),
    "VT": ("Viterbo", "Lazio"), "VV": ("Vibo Valentia", "Calabria"),
}

CLASS_RE = r"[A-Z]{1,2}[0-9A-Z]{2,3}"
# Codice meccanografico di una scuola: 2 lettere provincia + 2 lettere tipo + 5 cifre + 1 carattere
SCHOOL_RE = re.compile(r"\b([A-Z]{2})[A-Z]{2}[0-9]{5}[0-9A-Z]\b")
# Formato a colonne: classe, descrizione, TIPO GRADUATORIA (il primo GPS/GAE/GUI che segue), fascia, ... posizione, punteggio,
# inclusione con riserva (N-, S- o R-). Le righe «GUI» (elenco di utilizzo) non sono GPS e si scartano dopo.
ROW_LAYOUT = re.compile(
    r"^(?P<cdc>" + CLASS_RE + r")\s+-\s+.*?\s(?P<tipo>GPS|GAE|GUI)\s+F(?P<fascia>\d)\b(?P<rest>.*)")
POS_SCORE = re.compile(r"\s(?P<pos>\d{1,5})\s+(?P<score>\d{1,3}(?:[.,]\d{1,3})?)\s+[NSR]\s?-")
# formato con riga della classe e riga dei dati separate (pdftotext -raw)
CLASS_LINE = re.compile(r"^(?P<cdc>" + CLASS_RE + r")\s+-\s+\S")
ROW_RAW = re.compile(r"^(?P<tipo>GPS|GAE|GUI)\s+F(?P<fascia>\d)\s+(?P<pos>\d{1,5})\s+(?P<score>\d{1,3}(?:[.,]\d{1,3})?)(?:\s|$)")
# formato CSV stampato nel PDF: classe;GPS;F1;;;;;posizione;punteggio;...
ROW_CSV = re.compile(r"^(?P<cdc>" + CLASS_RE + r") - [^;]*;(?P<tipo>GPS|GAE|GUI);F(?P<fascia>\d);(?:[^;]*;){4}"
                     r"(?P<pos>\d{1,5});(?P<score>\d{1,3}(?:[.,]\d{1,3})?);")


PARSER_VERSION = 2          # cambia quando il lettore migliora: i bollettini che non si leggevano vengono riprovati
CHUNK_PAGES = 150           # i PDF grandi (Milano, Napoli, Catania...) si leggono a blocchi di pagine
OCR_MAX_PAGES = 400


def pdf_pages(path):
    """Numero di pagine del PDF (0 se non si riesce a saperlo)."""
    try:
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def pdf_text(path, raw):
    """Testo del PDF. Sopra CHUNK_PAGES pagine si legge a blocchi, così un file enorme non blocca né riempie la memoria."""
    mode = "-raw" if raw else "-layout"
    n = pdf_pages(path)
    ranges = [(None, None)] if n <= CHUNK_PAGES else [(a, min(a + CHUNK_PAGES - 1, n)) for a in range(1, n + 1, CHUNK_PAGES)]
    parts = []
    for first, last in ranges:
        cmd = ["pdftotext", mode] + (["-f", str(first), "-l", str(last)] if first else []) + [str(path), "-"]
        try:
            parts.append(subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300).stdout)
        except subprocess.TimeoutExpired:
            continue                       # un blocco che non si legge non butta via gli altri
    return "".join(parts)


def ocr_text(path, max_pages=OCR_MAX_PAGES):
    """Bollettino scansionato (immagini senza testo): riconoscimento dei caratteri con tesseract, se installato."""
    import shutil
    import tempfile
    if not (shutil.which("tesseract") and shutil.which("pdftoppm")):
        return ""
    n = min(pdf_pages(path) or max_pages, max_pages)
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        for first in range(1, n + 1, 20):
            last = min(first + 19, n)
            try:
                subprocess.run(["pdftoppm", "-r", "200", "-gray", "-f", str(first), "-l", str(last), str(path),
                                f"{tmp}/p"], check=True, timeout=600, capture_output=True)
            except (subprocess.SubprocessError, OSError):
                continue
            for img in sorted(os.listdir(tmp)):
                if not img.startswith("p"):
                    continue
                f = os.path.join(tmp, img)
                try:
                    out = subprocess.run(["tesseract", f, "-", "-l", "ita+eng", "--psm", "6"],
                                         capture_output=True, text=True, timeout=180).stdout
                    parts.append(out)
                except (subprocess.SubprocessError, OSError):
                    pass
                os.remove(f)
    return "\n".join(parts)


_KEEP = {"gps", "gae", "gui", "f1", "f2", "fascia", "classe", "concorso", "punteggio", "posizione", "tipo",
         "graduatoria", "scuola", "codice", "sostegno", "riserva", "grado", "pos", "cod"}


def text_shape(text, lines=14):
    """Impronta di un testo senza dati personali: le parole lunghe (nomi!) diventano «x», restano codici e numeri.
    Serve a capire in un log pubblico com'è fatto un bollettino che non si legge."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 6:
            continue
        toks = [t if (t.lower().strip(".,:;") in _KEEP or not re.fullmatch(r"[^\W\d_]{2,}[.,:;]?", t)) else "x"
                for t in line.split()]
        out.append(" ".join(toks)[:150])
        if len(out) >= lines:
            break
    return "\n".join(out)


def _school_siglas(text):
    """Province dei codici scuola presenti nel testo (una per codice)."""
    return [m.group(1) for m in SCHOOL_RE.finditer(text) if m.group(1) in SIGLE]


def tipo_code(cdc, tipo):
    """Codice con cui si salva una riga: GPS = «ADMM»; GUI (solo sostegno, classi AD**) = «ADMM#GUI»; altro = None."""
    if tipo == "GPS":
        return cdc
    if tipo == "GUI" and cdc.startswith("AD"):
        return cdc + "#GUI"
    return None


def parse_rows(text):
    """Restituisce [(classe, fascia, posizione, punteggio)] per le righe GPS."""
    rows = []
    cur = None
    for line in text.splitlines():
        line = line.rstrip()
        m = ROW_CSV.match(line)
        if m:
            code = tipo_code(m["cdc"], m["tipo"])
            if code:
                rows.append((code, "I" if m["fascia"] == "1" else "II",
                             int(m["pos"]), float(m["score"].replace(",", "."))))
            continue
        m = ROW_LAYOUT.match(line) if line[:1].strip() else None
        if m:
            cur = None
            code = tipo_code(m["cdc"], m["tipo"])
            if not code:
                continue
            ps = POS_SCORE.search(m["rest"])
            if ps:
                rows.append((code, "I" if m["fascia"] == "1" else "II",
                             int(ps["pos"]), float(ps["score"].replace(",", "."))))
            continue
        m = CLASS_LINE.match(line)
        if m:
            cur = m["cdc"]
            continue
        m = ROW_RAW.match(line)
        if m and cur and tipo_code(cur, m["tipo"]):
            rows.append((tipo_code(cur, m["tipo"]), "I" if m["fascia"] == "1" else "II",
                         int(m["pos"]), float(m["score"].replace(",", "."))))
    return rows


# Lettura «tollerante» (PDF con colonne spostate o testo da OCR): in una riga che contiene il tipo e la fascia, la
# prima coppia «posizione punteggio-con-decimali» che segue; la classe è all'inizio della riga o quella vista prima.
LOOSE_TIPO = re.compile(r"(?<![A-Z0-9])(?P<tipo>GPS|GAE|GUI)\s*[-:]?\s*F\s?(?P<fascia>[12lI|])(?![\dA-Za-z])(?P<rest>.*)")
LOOSE_POS = re.compile(r"(?<![\d.,])(?P<pos>\d{1,5})\s+(?P<score>\d{1,3}[.,]\d{1,3})(?![\d])")
LOOSE_CLASS = re.compile(r"(?<![A-Z0-9])(?P<cdc>" + CLASS_RE + r")\s*[-–]\s*\S")


def parse_rows_loose(text):
    rows, cur = [], None
    for line in text.splitlines():
        m = LOOSE_CLASS.match(line.strip())
        mt = LOOSE_TIPO.search(line)
        if m and not mt:
            cur = m["cdc"]
            continue
        if not mt:
            continue
        head = LOOSE_CLASS.match(line.strip())
        cdc = head["cdc"] if head else cur
        if head:
            cur = cdc
        code = tipo_code(cdc, mt["tipo"]) if cdc else None
        ps = LOOSE_POS.search(mt["rest"])
        if code and ps:
            rows.append((code, "II" if mt["fascia"] == "2" else "I", int(ps["pos"]), float(ps["score"].replace(",", "."))))
    return rows


def _norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _colmap(hdr):
    m = {}
    for i, c in enumerate(hdr):
        n = _norm(c)
        if n in ("classediconcorso", "cc", "cdc"):
            m["cdc"] = i
        elif n.startswith("tipograduat") or n.startswith("tipogr"):
            m["tipo"] = i
        elif n.startswith("fasci"):
            m.setdefault("fascia", i)
        elif (n.startswith("posi") or n == "pos") and "origine" not in n:
            m.setdefault("pos", i)
        elif n.startswith("punteg") or n == "punti":
            m.setdefault("score", i)
        elif n == "codicescuola":
            m["school"] = i
    return m if {"cdc", "tipo", "fascia", "pos", "score"} <= set(m) else None


def parse_tables(path):
    """Per i bollettini con tabelle a griglia (celle su più righe): legge le colonne dall'intestazione.
    Restituisce (righe GPS, codici scuola trovati)."""
    try:
        import pdfplumber
    except ImportError:
        return [], []
    rows, schools, cm = [], [], None
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            for t in pg.extract_tables():
                for r in t:
                    h = _colmap(r)
                    if h:
                        cm = h
                        continue
                    if not cm or len(r) <= max(cm.values()):
                        continue
                    cell = {k: (r[i] or "").replace("\n", " ").strip() for k, i in cm.items()}
                    mc = re.match(r"^(" + CLASS_RE + r")\b", cell["cdc"])
                    mf = re.match(r"^F?(\d)$", cell["fascia"])
                    code = tipo_code(mc.group(1), cell["tipo"]) if mc else None
                    if not (mc and mf and code
                            and re.fullmatch(r"\d{1,5}", cell["pos"])
                            and re.fullmatch(r"\d{1,3}(?:[.,]\d{1,3})?", cell["score"])):
                        continue
                    rows.append((code, "I" if mf.group(1) == "1" else "II",
                                 int(cell["pos"]), float(cell["score"].replace(",", "."))))
                    if cell.get("school"):
                        schools.append(cell["school"])
    return rows, schools


def pdf_date(path):
    """Data di creazione del PDF (YYYY-MM-DD) o None."""
    from datetime import datetime
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    m = re.search(r"^CreationDate:\s+(.+)$", out, re.M)
    if m:
        for fmt in ("%a %b %d %H:%M:%S %Y %Z", "%a %b %d %H:%M:%S %Y"):
            try:
                return datetime.strptime(m.group(1).strip(), fmt).date().isoformat()
            except ValueError:
                pass
    return None


def read_xlsx(path):
    """Bollettino in Excel (.xlsx / .xlsm: le macro non vengono mai eseguite, si leggono solo i valori)."""
    from openpyxl import load_workbook
    rows, schools = [], []
    wb = load_workbook(path, read_only=True, data_only=True, keep_vba=False)
    for ws in wb.worksheets:
        cm = None
        for r in ws.iter_rows(values_only=True):
            r = ["" if c is None else str(c).strip() for c in r]
            h = _colmap(r)
            if h:
                cm = h
                continue
            if not cm or len(r) <= max(cm.values()):
                continue
            mc = re.match(r"^(" + CLASS_RE + r")\b", r[cm["cdc"]])
            mf = re.match(r"^F?(\d)$", r[cm["fascia"]])
            pos = re.sub(r"\.0$", "", r[cm["pos"]])
            score = r[cm["score"]]
            code = tipo_code(mc.group(1), r[cm["tipo"]]) if mc else None
            if not (mc and mf and code and re.fullmatch(r"\d{1,5}", pos)
                    and re.fullmatch(r"\d{1,3}(?:[.,]\d{1,3})?", score)):
                continue
            rows.append((code, "I" if mf.group(1) == "1" else "II", int(pos), float(score.replace(",", "."))))
            if cm.get("school"):
                schools.append(r[cm["school"]])
    wb.close()
    siglas = [m.group(1) for c in schools for m in [SCHOOL_RE.search(c)] if m and m.group(1) in SIGLE]
    return (max(set(siglas), key=siglas.count) if siglas else None), rows


def read_pdf(path):
    """Legge un bollettino. Restituisce (sigla_provincia, righe). Un bollettino riguarda una sola provincia:
    la sigla è quella più frequente tra i codici delle scuole.
    Ordine: testo del PDF (due modi di lettura x tre lettori di righe); se non basta le tabelle (pdfplumber, solo per
    PDF di dimensioni ragionevoli); se il PDF è una scansione, il riconoscimento dei caratteri (OCR)."""
    if str(path).lower().endswith((".xlsx", ".xlsm")):
        return read_xlsx(path)
    best_rows, best_text = [], ""
    texts = []
    for raw in (False, True):
        text = pdf_text(path, raw).replace("\x00", "")
        texts.append(text)
        for parser in (parse_rows, parse_rows_loose):
            rows = parser(text)
            if len(rows) > len(best_rows):
                best_rows, best_text = rows, text
    pages = pdf_pages(path)
    if pages <= 120 or (not best_rows and pages <= 300):      # i PDF enormi si provano con le tabelle solo se il testo non basta
        t_rows, t_schools = parse_tables(path)
        if len(t_rows) > len(best_rows):
            best_rows = t_rows
            best_text = ""
            siglas = [m.group(1) for c in t_schools for m in [SCHOOL_RE.search(c)] if m and m.group(1) in SIGLE]
            if siglas:
                return max(set(siglas), key=siglas.count), best_rows
    if not best_rows and sum(len(t.strip()) for t in texts) < 40 * max(pages, 1):     # quasi senza testo: scansione
        ocr = ocr_text(path)
        for parser in (parse_rows, parse_rows_loose):
            rows = parser(ocr)
            if len(rows) > len(best_rows):
                best_rows, best_text = rows, ocr
    if not best_rows:
        read_pdf.last_shape = text_shape(texts[0] or texts[1])
    siglas = _school_siglas(best_text)
    sigla = max(set(siglas), key=siglas.count) if siglas else None
    return sigla, best_rows


read_pdf.last_shape = ""


def _slug(text):
    import unicodedata
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\b(e|di|del|della|d)\b", " ", t)
    return re.sub(r"[^a-z]", "", t)


def sigla_from_name(path):
    """Ultima risorsa quando il bollettino non ha il codice scuola: il nome del file («Ragusa1.pdf», «Pesaro_Urbino1.pdf.pdf»)."""
    name = re.sub(r"^.*[\\/]", "", str(path))
    name = re.sub(r"(\.(pdf|xlsx?|xlsm))+$", "", name, flags=re.I)
    name = re.sub(r"[\s._-]*(boll(ettino)?.*)?\d*$", "", name, flags=re.I)
    slug = _slug(name)
    if len(slug) < 4:
        return None
    for sigla, (prov, _reg) in SIGLE.items():
        if _slug(prov) == slug:
            return sigla
    for sigla, (prov, _reg) in SIGLE.items():
        if _slug(prov).startswith(slug) or slug.startswith(_slug(prov)):
            return sigla
    return None


def turn_from_name(path):
    """Numero del bollettino dal nome del file («bollettino-2», «Bollettino n. 3»...); '1' se non c'è."""
    name = re.sub(r"^.*[\\/]", "", str(path))
    m = re.search(r"boll(?:ettino)?[\s._-]*(?:n\.?[\s._-]*)?(\d{1,2})", name, re.I)
    return m.group(1) if m else "1"


def aggregate(rows_by_sigla_turn):
    """rows_by_sigla_turn: {(sigla, turno): [(classe, fascia, pos, punteggio), ...]}.
    Per provincia/classe/fascia salva: n nomine totali, punteggio minimo e massimo, posizione più bassa e,
    per ogni turno (bollettino), l'elenco "s" dei nominati come [punteggio, posizione] in ordine di punteggio
    decrescente (nessun nome: serve a escludere la quota riservata, che si calcola turno per turno)."""
    provinces = {}
    for (sigla, turno), rows in sorted(rows_by_sigla_turn.items()):
        prov, reg = SIGLE[sigla]
        entry = provinces.setdefault(prov, {"regione": reg, "classi": {}})
        turns = {}
        for cdc, fascia, pos, score in rows:
            e = entry["classi"].setdefault(f"{cdc}:{fascia}", {"n": 0, "min": score, "max": score, "pos": pos, "t": []})
            e["n"] += 1
            if score < e["min"]:
                e["min"], e["pos"] = score, pos
            elif score == e["min"]:
                e["pos"] = max(e["pos"], pos)
            e["max"] = max(e["max"], score)
            turns.setdefault(f"{cdc}:{fascia}", []).append([score, pos])
        for key, lst in turns.items():
            lst.sort(key=lambda x: (-x[0], x[1]))
            entry["classi"][key]["t"].append({"b": turno, "s": lst})
    return provinces


def merge(old, new):
    """Unisce due elenchi di province: un turno già presente viene sostituito, gli altri si aggiungono.
    Province e classi non toccate restano come sono."""
    out = json_copy(old)
    for prov, info in new.items():
        dst = out.setdefault(prov, {"regione": info["regione"], "classi": {}})
        dst["regione"] = info["regione"]
        for key, e in info["classi"].items():
            cur = dst["classi"].get(key)
            old_turns = (cur.get("t") or ([{"b": "1", "s": cur["s"]}] if cur.get("s") else [])) if cur else []
            turns = {t["b"]: t for t in old_turns}
            for t in e["t"]:
                turns[t["b"]] = t
            merged = [turns[b] for b in sorted(turns, key=lambda x: (int(x) if x.isdigit() else 0, x))]
            dst["classi"][key] = _entry_from_turns(merged)
    return out


def json_copy(obj):
    import json
    return json.loads(json.dumps(obj))


def _entry_from_turns(turns):
    allrows = [(sc, pos) for t in turns for sc, pos in t["s"]]
    lowest = min(sc for sc, _ in allrows)
    return {"n": len(allrows), "min": lowest, "max": max(sc for sc, _ in allrows),
            "pos": max(pos for sc, pos in allrows if sc == lowest), "t": turns}
