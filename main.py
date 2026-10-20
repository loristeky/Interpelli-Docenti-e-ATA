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
DB_VERSION = 8
SOON_DAYS = 3


def get_db_path():
    db_dir = os.getenv("FLET_APP_STORAGE_DATA")
    if not db_dir:
        try:
            base_dir = os.
