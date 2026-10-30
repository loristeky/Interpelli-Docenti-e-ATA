# Aggiungere province: basta caricare i PDF qui

1. Scarica il bollettino di nomina GPS (PDF, oppure Excel .xlsx/.xlsm) dal sito dell'Ufficio scolastico provinciale.
2. Su GitHub apri questa cartella `bollettini` → **Add file → Upload files** → trascina i file → **Commit changes**.
   Il numero del turno si legge dal nome del file: se si chiama `...bollettino-2...pdf` è il turno 2,
   altrimenti è il turno 1. Se carichi il turno 2 di una provincia, si aggiunge al turno 1.
3. Dopo un minuto circa parte da sola l'automazione «Aggiorna dati GPS»: legge i PDF, aggiorna
   `assets/gps_data.json` e **cancella i PDF dalla cartella** (contengono nomi dei candidati).
4. Per avere i dati nell'app, ricostruisci l'app (Actions → Build APK / Build AAB).

Controlla il risultato in Actions → «Aggiorna dati GPS»: il registro elenca ogni file con provincia,
turno e numero di nomine, e segnala i file che non riesce a leggere (restano qui).

Formati letti: PDF a tabella, PDF a testo, PDF con righe CSV e fogli Excel. Il nome della provincia si riconosce dai codici
delle scuole; se mancano si usa il nome del file (es. `Ragusa1.pdf`). I PDF con le colonne spezzate su pagine diverse
e quelli senza punteggio non sono leggibili e vengono saltati con un avviso.

## Aggiornamento automatico

L'automazione «Aggiorna dati GPS» parte da sola due volte al giorno: cerca nelle pagine di notizie e comunicazioni degli Uffici scolastici
(ricavate dai siti delle fonti dell'app: home, feed, «notizie», «comunicazioni», «avvisi») gli avvisi «bollettino» / «nomine» con allegati PDF o Excel, li scarica, li legge e aggiorna
`assets/gps_data.json`. I file scaricati non vengono mai salvati nel repository. Gli indirizzi già visti sono in
`tools/gps/bollettini_visti.json`.

- Se la pagina dove un ufficio pubblica i bollettini non viene trovata da sola, aggiungila in
  `tools/gps/pagine_bollettini.json`, per esempio: `[{"nome": "USP Napoli", "url": "https://..."}]`.
- Per provarla subito: GitHub → Actions → «Aggiorna dati GPS» → Run workflow.
- Il registro dell'esecuzione dice quali pagine non rispondono e quali file non è riuscita a leggere.
- Se un bollettino non viene letto, puoi sempre caricarlo a mano in questa cartella come prima.

### Elenco di Orizzonte Scuola

L'automazione legge anche la pagina di Orizzonte Scuola con i link diretti ai bollettini di tutte le province
(«Supplenze docenti, ecco i bollettini nomine…»), saltando le rettifiche. Per aggiungere altre pagine-elenco dello
stesso tipo, mettile in `tools/gps/pagine_bollettini.json` con `"tipo": "elenco"`.

## Bollettini che non si leggono o sono molto grandi
- I PDF grandi si leggono a blocchi di 150 pagine; si scaricano fino a 250 MB.
- I PDF scansionati (immagini, senza testo) si leggono con il riconoscimento dei caratteri (OCR, in italiano).
- Se un file non si legge, nel log compare «Com'è fatto il file» (parole sostituite da «x»: nessun nome) e il nome finisce in `tools/gps/bollettini_problemi.json`. Quando il lettore migliora (`PARSER_VERSION` in `bollettini.py`) quei bollettini vengono riscaricati e riprovati da soli.
