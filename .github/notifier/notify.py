#!/usr/bin/env python3
"""Notificatore di nuovi interpelli (gira su GitHub Actions, non sul telefono).

Controlla le stesse fonti dell'app, ricorda quali avvisi ha già visto (seen.json) e invia una
notifica push tramite ntfy (https://ntfy.sh) per quelli nuovi che corrispondono ai filtri.
Funziona anche con l'app chiusa o il telefono in tasca: la notifica la consegna l'app "ntfy".

Configurazione (variabili d'ambiente, impostate dal workflow):
  NTFY_TOPIC       nome del canale ntfy (segreto: chi lo conosce può leggere le notifiche)
  NTFY_SERVER      server ntfy (default https://ntfy.sh)
  NOTIFY_CLASSES   le tue classi di concorso (le stesse di «Per me»), es. "A028, A022, PPPP".
                   Obbligatorio: se è vuoto non viene inviata nessuna notifica.
  NOTIFY_PROFILE   facoltativo: DOCENTI | ATA | vuoto per entrambi
  NOTIFY_REGIONS   regioni da controllare, es. "Toscana, Lazio" (vuoto = tutta Italia)
  SEEN_FILE        file con gli avvisi già visti (default seen.json)
  DRY_RUN=1        stampa le notifiche invece di inviarle

Opzioni:  --test  invia solo una notifica di prova.
"""
import json
import os
import sys
import tempfile
import time
import types
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from importlib import util
from pathlib import Path
from unittest.mock import MagicMock

MAX_INDIVIDUAL = 5        # oltre questa soglia si manda un solo riepilogo
MAX_SEEN = 6000           # quanti indirizzi ricordare
RECENT_DAYS = 21          # non avvisare per pubblicazioni più vecchie di così


def load_app():
    """Importa le funzioni di lettura dall'app (main.py) senza avviare l'interfaccia."""
    os.environ.setdefault("FLET_APP_STORAGE_DATA", tempfile.mkdtemp())
    sys.modules.setdefault("flet", MagicMock())          # l'interfaccia non serve qui
    root = Path(__file__).resolve().parents[2]
    spec = util.spec_from_file_location("interpelli_app", root / "main.py")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def split_list(value):
    return [x.strip() for x in (value or "").replace(";", ",").split(",") if x.strip()]


def load_seen(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        urls = data.get("urls")
        return list(urls) if isinstance(urls, list) else None
    except (OSError, ValueError):
        return None


def save_seen(path, urls):
    urls = urls[-MAX_SEEN:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"urls": urls, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)


def send_ntfy(server, topic, title, message, click=None, tags=None, priority=3, actions=None):
    """Pubblica su ntfy con l'API JSON (supporta accenti ed emoji). Solleva eccezione se fallisce."""
    payload = {"topic": topic, "title": title, "message": message, "priority": priority,
               "tags": tags or ["mortar_board"]}
    if click:
        payload["click"] = click
    if actions:
        payload["actions"] = actions
    req = urllib.request.Request(
        server.rstrip("/") + "/", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"ntfy ha risposto {resp.status}")


def notification_for(app, item):
    title, link, region, source, target, published, deadline, cdc, post_type, doc_url, email = item
    codes = ", ".join(app.cdc_label(c.strip()) for c in (cdc or "").split(",") if c.strip())
    head = f"{'ATA' if target == 'ATA' else 'Docenti'}" + (f" · {codes}" if codes else "")
    lines = [title, f"{source} · {region}"]
    if deadline:
        lines.append(f"Scadenza: {app.fmt_date(deadline)}")
    else:
        lines.append("Scadenza: controlla nell'avviso")
    actions = [{"action": "view", "label": "Apri avviso", "url": link, "clear": True}]
    if doc_url:
        actions.append({"action": "view", "label": "Documento", "url": doc_url})
    return {"title": f"Nuovo interpello – {head}", "message": "\n".join(lines), "click": link,
            "actions": actions}


def collect_new(app, regions, known, workers=15):
    """Scarica le fonti e restituisce (nuovi avvisi, fonti raggiunte, fonti totali)."""
    jobs = []
    for region, sources in app.SOURCES.items():
        if regions and region not in regions:
            continue
        for src in sources:
            pages = src[2] if len(src) > 2 else 1
            for p in range(1, pages + 1):
                jobs.append((region, src[0], app.get_page_url(src[1], p)))
    new_items, reached = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(app.parse_source_page, r, n, u, known) for r, n, u in jobs]
        for fut in as_completed(futures):
            try:
                items, ok = fut.result()
            except Exception as ex:                       # una fonte che si rompe non ferma le altre
                print(f"  fonte in errore: {ex}")
                continue
            reached += 1 if ok else 0
            new_items.extend(items)
    return new_items, reached, len(jobs)


def wanted(app, item, classes, profile):
    title, link, region, source, target, published, deadline, cdc, *_ = item
    if profile and target != profile:
        return False
    if not app.matches_classes(title, cdc, classes):
        return False
    today = date.today()
    d = app.to_date(deadline) if deadline else None
    if d and d < today:                                    # già scaduto
        return False
    p = app.to_date(published) if published else None
    if p and (today - p).days > RECENT_DAYS:               # vecchio: probabilmente appena scoperto
        return False
    return True


def main(argv):
    server = os.getenv("NTFY_SERVER") or "https://ntfy.sh"
    topic = (os.getenv("NTFY_TOPIC") or "").strip()
    dry = os.getenv("DRY_RUN") == "1"
    if not topic and not dry:
        print("NTFY_TOPIC non impostato: aggiungilo tra i Secrets del repository.")
        return 2

    if "--test" in argv:
        msg = "Le notifiche funzionano: riceverai un avviso quando esce un nuovo interpello."
        if dry:
            print("[prova]", msg)
        else:
            send_ntfy(server, topic, "Interpelli Scuola – prova", msg, tags=["white_check_mark"])
        print("Notifica di prova inviata.")
        return 0

    app = load_app()
    classes = app.parse_classes(os.getenv("NOTIFY_CLASSES", ""))
    profile = (os.getenv("NOTIFY_PROFILE") or "").strip().upper()
    if profile not in ("DOCENTI", "ATA"):
        profile = ""
    regions = split_list(os.getenv("NOTIFY_REGIONS"))
    seen_path = os.getenv("SEEN_FILE") or "seen.json"

    seen = load_seen(seen_path)
    bootstrap = seen is None
    seen = seen or []
    known = set(seen)
    print(f"Filtri · classi: {classes or 'nessuna'} · profilo: {profile or 'tutti'} · regioni: {regions or 'tutta Italia'}")
    print("Prima esecuzione: registro gli avvisi esistenti senza notificarli." if bootstrap
          else f"Avvisi già visti: {len(known)}")

    new_items, reached, total = collect_new(app, regions, known)
    print(f"Fonti raggiunte: {reached}/{total} · nuovi avvisi trovati: {len(new_items)}")
    if total and reached == 0:
        print("Nessuna fonte raggiungibile: non aggiorno lo stato.")
        return 1

    if not classes:
        print("NOTIFY_CLASSES è vuoto: non invio notifiche. Imposta le tue classi di concorso "
              "(le stesse del filtro «Per me» dell'app) per riceverle.")
    to_send = [] if (bootstrap or not classes) else [it for it in new_items if wanted(app, it, classes, profile)]
    sent_urls = set()
    failures = 0
    if len(to_send) > MAX_INDIVIDUAL:
        lines = [f"• {it[0][:90]}" for it in to_send[:MAX_INDIVIDUAL]] + [f"…e altri {len(to_send) - MAX_INDIVIDUAL}"]
        try:
            if dry:
                print("[riepilogo]", lines)
            else:
                send_ntfy(server, topic, f"{len(to_send)} nuovi interpelli per te", "\n".join(lines),
                          click=to_send[0][1])
            sent_urls.update(it[1] for it in to_send)
        except (urllib.error.URLError, RuntimeError, OSError) as ex:
            failures += 1
            print(f"Invio del riepilogo non riuscito: {ex}")
    else:
        for it in to_send:
            note = notification_for(app, it)
            try:
                if dry:
                    print("[notifica]", note["title"], "|", note["message"].replace("\n", " / "))
                else:
                    send_ntfy(server, topic, note["title"], note["message"], click=note["click"],
                              actions=note["actions"])
                sent_urls.add(it[1])
            except (urllib.error.URLError, RuntimeError, OSError) as ex:
                failures += 1
                print(f"Invio non riuscito per {it[1]}: {ex}")

    # Gli avvisi non inviati per errore restano "non visti" e si riprovano alla prossima esecuzione.
    failed_urls = {it[1] for it in to_send} - sent_urls
    for it in new_items:
        if it[1] not in failed_urls and it[1] not in known:
            seen.append(it[1])
            known.add(it[1])
    save_seen(seen_path, seen)
    print(f"Notifiche inviate: {len(sent_urls)} · errori: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
