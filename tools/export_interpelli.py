#!/usr/bin/env python3
"""Pubblica l'elenco degli interpelli in un file JSON che l'app scarica in un colpo solo.

Gira su GitHub Actions (vedi .github/workflows/pubblica-interpelli.yml) ogni 30 minuti circa: legge le fonti come fa
l'app (pagine degli interpelli e notizie degli uffici), tiene gli avvisi dei giorni scorsi e scrive `interpelli.json`.
Contiene solo informazioni pubbliche degli avvisi (titolo, indirizzo, ufficio, date, classi, allegato, email della
scuola): nessun dato personale. L'elenco precedente (--prec) fa da memoria, così ad ogni giro si scaricano solo gli
avvisi nuovi.

Uso:  python tools/export_interpelli.py --prec prec.json --out interpelli.json
"""
import argparse
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from importlib import util
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
KEEP_DAYS = 60            # quanto indietro tenere gli avvisi
MAX_ROWS = 2500
RECHECK = 60              # avvisi senza scadenza da rileggere per giro


def load_app():
    os.environ.setdefault("FLET_APP_STORAGE_DATA", tempfile.mkdtemp())
    sys.modules.setdefault("flet", MagicMock())
    spec = util.spec_from_file_location("interpelli_app", ROOT / "main.py")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_prev(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = [r for r in data.get("righe", []) if isinstance(r, list) and len(r) == 11]
        return rows, set(data.get("provati", []))
    except (OSError, ValueError, AttributeError):
        return [], set()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prec", default="prec.json")
    ap.add_argument("--out", default="interpelli.json")
    args = ap.parse_args(argv)

    app = load_app()
    rows, tried = read_prev(args.prec)
    by_url = {r[1]: r for r in rows}
    known = set(by_url)

    jobs = []
    for region, sources in app.SOURCES.items():
        for src in sources:
            pages = src[2] if len(src) > 2 else 1
            for p in range(1, pages + 1):
                jobs.append((region, src[0], app.get_page_url(src[1], p), False))
    jobs += [(r, n, u, True) for r, n, u in app.deep_pages(app.SOURCES.items())]

    reached = 0
    new = 0
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(app.parse_source_page, r, n, u, known, d) for r, n, u, d in jobs]
        for fut in as_completed(futures):
            try:
                items, ok = fut.result()
            except Exception as ex:
                print(f"fonte in errore: {ex}")
                continue
            reached += 1 if ok else 0
            for it in items:
                if it[1] not in by_url:
                    by_url[it[1]] = list(it)
                    new += 1
    print(f"Fonti raggiunte: {reached}/{len(jobs)} · nuovi avvisi: {new}")

    # avvisi senza scadenza: riprova a leggerla negli allegati (una volta sola per avviso)
    todo = [r for r in by_url.values() if not r[6] and r[9] and r[1] not in tried][:RECHECK]
    for r in todo:
        info = app.enrich_from_doc({"doc_url": r[9], "published": r[5] or "", "email": r[10] or "",
                                    "deadline": None, "text": ""})
        tried.add(r[1])
        if info.get("deadline"):
            r[6] = info["deadline"]
        if info.get("email") and not r[10]:
            r[10] = info["email"]

    limit = (date.today() - timedelta(days=KEEP_DAYS)).isoformat()
    grace = (date.today() - timedelta(days=14)).isoformat()
    keep = [r for r in by_url.values() if (r[5] or "9") >= limit or (r[6] or "") >= grace]
    keep.sort(key=lambda r: r[5] or "", reverse=True)
    keep = keep[:MAX_ROWS]
    alive = {r[1] for r in keep}
    out = {"aggiornato": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "righe": keep,
           "provati": sorted(tried & alive)[-3000:]}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scritti {len(keep)} avvisi in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
