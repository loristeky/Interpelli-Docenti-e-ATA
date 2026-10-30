#!/usr/bin/env python3
"""Controlla una per una le fonti degli interpelli (SOURCES di main.py) e scrive un rapporto.

Gira su GitHub Actions (vedi .github/workflows/verifica-fonti.yml), dove la rete è libera: da lì si vede quali indirizzi
funzionano davvero. Per ogni fonte dice se è raggiungibile e quanti avvisi ci trova; per quelle che non funzionano
guarda la home del sito e propone i collegamenti che sembrano la pagina giusta (interpelli, supplenze, convocazioni...).

Uso:  python tools/verifica_fonti.py --out tools/fonti_report.md
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from export_interpelli import load_app  # noqa: E402

HINT_RE = re.compile(r"interpell|supplenz|convocazion|messa\s+a\s+disposizione|\bmad\b|nomine|reclutamento|"
                     r"graduatorie\s+provinciali|\bgps\b|docenti", re.I)


def tag_text(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def suggestions(app, url, limit=6):
    """Collegamenti della home (e della pagina stessa) che sembrano la pagina degli interpelli."""
    u = urlparse(url)
    home = f"{u.scheme}://{u.netloc}/"
    found = {}
    for page_url in dict.fromkeys([url, home]):
        try:
            html = app.fetch_url(page_url)
        except Exception:
            continue
        for href, txt in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            label = tag_text(txt)
            full = urljoin(page_url, unescape(href))
            if urlparse(full).netloc.replace("www.", "") != u.netloc.replace("www.", ""):
                continue
            if HINT_RE.search(label + " " + full) and 3 <= len(label) <= 90:
                found.setdefault(full, label)
        if len(found) >= limit:
            break
    return list(found.items())[:limit]


def check(app, region, name, url):
    try:
        items, ok = app.parse_source_page(region, name, url, set(), False)
    except Exception as ex:
        return {"regione": region, "nome": name, "url": url, "stato": "errore", "avvisi": 0, "dettaglio": str(ex)[:80]}
    if not ok:
        return {"regione": region, "nome": name, "url": url, "stato": "irraggiungibile", "avvisi": 0, "dettaglio": ""}
    return {"regione": region, "nome": name, "url": url, "stato": "ok" if items else "vuota", "avvisi": len(items),
            "dettaglio": ""}


def diagnosi_digest(app, region, name, url):
    """Per le fonti con avviso riassuntivo (PDF): mostra passo per passo cosa trova l'app, per capire dove si ferma."""
    import re as _re
    out = [f"### Diagnosi {name}", f"- Pagina: {url}"]
    try:
        page = app.fetch_url(url)
    except Exception as ex:
        return out + [f"- Pagina non raggiungibile: {str(ex)[:100]}"]
    out.append(f"- Pagina scaricata: {len(page)} caratteri")
    links = app._links_in(page, url) + app._links_in(app._light_html(page), url)
    links = list(dict.fromkeys(links))
    out.append(f"- Collegamenti da avviso trovati: {len(links)}")
    for t, l, _d in links[:8]:
        out.append(f"  - {t[:70]} -> {l[:90]}")
    good = [x for x in links if len(x[0]) > 30 and _re.search(r"\bn\.?\s*\d+|conferimento", x[0], _re.I)
            and x[1].rstrip("/").lower() != url.rstrip("/").lower()]
    out.append(f"- Avvisi con numero: {len(good)}")
    if good:
        try:
            notice = app.fetch_url(good[0][1])
            hrefs = [h for h in _re.findall(r'href=["\']([^"\']+)["\']', notice, _re.I)
                     if _re.search(r"\.pdf|/documents/", h, _re.I)]
            out.append(f"- Avviso più recente: {good[0][0][:70]} ({len(notice)} caratteri), allegati: {len(hrefs)}")
            for h in hrefs[:4]:
                full = app.urljoin(good[0][1], h.replace("&amp;", "&"))
                try:
                    import pypdf  # noqa: F401
                    lettore = "pypdf ok"
                except ImportError:
                    lettore = "pypdf NON installato"
                try:
                    raw = app.fetch_bytes(full, limit=25_000_000)
                    scarico = f"{len(raw)} byte, inizia con {raw[:5]!r}"
                except Exception as ex:
                    scarico = f"scaricamento fallito: {str(ex)[:80]}"
                text = app.doc_full_text(full)
                rows = app.parse_digest_rows(text)
                out.append(f"  - {full[:100]} -> {len(rows)} righe lette ({lettore}; {scarico}; testo estratto: {len(text)} caratteri)")
        except Exception as ex:
            out.append(f"- Avviso non letto: {str(ex)[:100]}")
    return out + [""]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="tools/fonti_report.md")
    args = ap.parse_args(argv)
    app = load_app()
    jobs = [(r, s[0], s[1]) for r, srcs in app.SOURCES.items() for s in srcs]
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda j: check(app, *j), jobs))
    bad = [r for r in results if r["stato"] != "ok"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for r, sug in zip(bad, pool.map(lambda r: suggestions(app, r["url"]), bad)):
            r["proposte"] = sug

    lines = [f"# Rapporto sulle fonti ({datetime.now():%d/%m/%Y %H:%M})", "",
             f"Fonti controllate: {len(results)}. Funzionano: {len(results) - len(bad)}. "
             f"Da guardare: {len(bad)}.", ""]
    if bad:
        lines += ["## Da guardare", ""]
        for r in sorted(bad, key=lambda r: (r["stato"], r["regione"], r["nome"])):
            lines.append(f"### {r['nome']} ({r['regione']}) - {r['stato']}")
            lines.append(f"- Indirizzo attuale: {r['url']}")
            if r.get("dettaglio"):
                lines.append(f"- Errore: {r['dettaglio']}")
            if r["stato"] == "vuota":
                lines.append("- La pagina si apre ma non ci trovo avvisi: forse è cambiata la struttura o è la pagina sbagliata.")
            for link, label in r.get("proposte", []):
                lines.append(f"- Forse: [{label}]({link})")
            lines.append("")
    lines += ["## Funzionano", ""] + [f"- {r['nome']} ({r['regione']}): {r['avvisi']} avvisi"
                                       for r in sorted(results, key=lambda r: (r['regione'], r['nome'])) if r["stato"] == "ok"]
    for r in app.SOURCES.items():
        for src in r[1]:
            if src[0] in app.DIGEST_SOURCES:
                lines += [""] + diagnosi_digest(app, r[0], src[0], src[1])
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path(args.out).with_suffix(".json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines[:4]))
    for r in bad:
        print(f"[{r['stato']}] {r['nome']} - {r['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
