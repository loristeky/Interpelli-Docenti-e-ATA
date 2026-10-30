#!/usr/bin/env python3
"""Prepara assets/gps_data.json per «Dove mi conviene fare le GPS?» dai bollettini di nomina GPS (PDF).

Per ogni provincia, classe di concorso e fascia salva: quante nomine, punteggio più basso e più alto
dei nominati, posizione più bassa raggiunta. Non vengono letti né salvati nomi o dati personali.
La provincia si riconosce dai codici delle scuole nel bollettino.

Uso (serve il comando `pdftotext`, pacchetto poppler-utils):
  python tools/gps/build_gps_data.py --cartella bollettini --output assets/gps_data.json
  oppure elencando i file:  python tools/gps/build_gps_data.py a.pdf b.pdf --output assets/gps_data.json

Il numero del turno si legge dal nome del file («bollettino-2.pdf»); se manca vale 1. Più bollettini della
stessa provincia sono turni diversi: la quota riservata si calcola turno per turno.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bollettini  # noqa: E402


def default_year(today=None):
    today = today or date.today()
    y = today.year if today.month >= 7 else today.year - 1
    return f"{y}/{(y + 1) % 100:02d}"


PROBLEMI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bollettini_problemi.json")


def write_problems(problems, done=None):
    """Elenco (solo nomi dei file, mai contenuti) dei bollettini che non si sono potuti leggere con questa versione
    del lettore: il downloader li riscarica quando il lettore migliora (PARSER_VERSION)."""
    old = {}
    try:
        with open(PROBLEMI, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        pass
    keep = {x["file"]: x for x in old.get("file", []) if isinstance(x, dict) and "file" in x}
    for x in problems:
        keep[x["file"]] = x
    for f in done or []:
        keep.pop(os.path.basename(f), None)
    data = {"versione": bollettini.PARSER_VERSION, "file": sorted(keep.values(), key=lambda x: x["file"])}
    with open(PROBLEMI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="*", help="uno o più bollettini di nomina (PDF)")
    ap.add_argument("--cartella", help="cartella con tutti i PDF (anche nelle sottocartelle)")
    ap.add_argument("--output", default="assets/gps_data.json")
    ap.add_argument("--anno", default=default_year(), help="anno scolastico, es. 2026/27")
    ap.add_argument("--bollettino", default="", help="numero del bollettino per file senza numero nel nome (default 1)")
    ap.add_argument("--provincia", help="sigla (es. PE) se non si riconosce dai codici scuola; vale per tutti i PDF")
    ap.add_argument("--aggiungi", action="store_true",
                    help="unisci ai dati già presenti (un turno già presente viene sostituito)")
    ap.add_argument("--elaborati", help="scrive qui l'elenco dei PDF letti con successo")
    args = ap.parse_args(argv)

    paths = list(args.pdf)
    if args.cartella:
        for root, _dirs, files in os.walk(args.cartella):
            paths += [os.path.join(root, f) for f in files if f.lower().endswith((".pdf", ".xlsx", ".xlsm"))]
    paths = sorted(set(paths))
    if not paths:
        print("Nessun PDF trovato.", file=sys.stderr)
        return 1
    rows_by_sigla = {}
    dates = []
    failed = 0
    processed = []
    problems = []
    for path in paths:
        try:
            sigla, rows = bollettini.read_pdf(path)
        except Exception:
            print(f"ATTENZIONE {os.path.basename(path)}: file non leggibile: file saltato", file=sys.stderr)
            problems.append({"file": os.path.basename(path), "motivo": "file non leggibile"})
            failed += 1
            continue
        sigla = (args.provincia or sigla or bollettini.sigla_from_name(path) or "").upper()
        if sigla not in bollettini.SIGLE or not rows:
            print(f"ATTENZIONE {os.path.basename(path)}: "
                  + ("provincia non riconosciuta (usa --provincia)" if rows else "nessuna riga GPS trovata")
                  + ": file saltato", file=sys.stderr)
            problems.append({"file": os.path.basename(path),
                             "motivo": "provincia non riconosciuta" if rows else "nessuna riga GPS trovata"})
            shape = getattr(bollettini.read_pdf, "last_shape", "")
            if shape and not rows:
                print("  Com'è fatto il file (parole sostituite da «x», nessun nome):\n    "
                      + shape.replace("\n", "\n    "), file=sys.stderr)
            failed += 1
            continue
        processed.append(path)
        turno = args.bollettino or bollettini.turn_from_name(path)
        rows_by_sigla.setdefault((sigla, turno), []).extend(rows)
        dates.append(bollettini.pdf_date(path))
        print(f"{os.path.basename(path)}: {bollettini.SIGLE[sigla][0]}, bollettino {turno}, {len(rows)} nomine GPS")

    write_problems(problems, processed)
    if not rows_by_sigla:
        return 1
    provinces = bollettini.aggregate(rows_by_sigla)
    if args.aggiungi and os.path.exists(args.output):
        with open(args.output, encoding="utf-8") as f:
            old = json.load(f)
        provinces = bollettini.merge(old.get("province", {}), provinces)
    data = {
        "anno": args.anno,
        "aggiornato": max([d for d in dates if d] or [date.today().isoformat()]),
        "bollettino": max({t for (_s, t) in rows_by_sigla}, key=lambda x: int(x) if x.isdigit() else 0),
        "fonte": "Bollettini di nomina GPS pubblicati dagli Uffici scolastici provinciali",
        "province": dict(sorted(provinces.items())),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    if args.elaborati:
        with open(args.elaborati, "w", encoding="utf-8") as f:
            f.write("\n".join(processed) + "\n")
    pairs = sum(len(p["classi"]) for p in provinces.values())
    print(f"{len(provinces)} province, {pairs} classi/fasce -> {args.output}"
          + (f" ({failed} file saltati)" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
