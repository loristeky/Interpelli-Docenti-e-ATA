# Dati per «Dove mi conviene fare le GPS?»

L'app confronta classe, fascia e punteggio dell'utente con i **bollettini di nomina GPS** pubblicati
dagli Uffici scolastici provinciali. Per ogni provincia, classe e fascia usa: quante nomine ci sono
state, il punteggio dell'ultimo nominato (la «soglia») e la posizione raggiunta. I dati stanno in
`assets/gps_data.json` e contengono **solo valori aggregati, nessun nome**.

Ora il file contiene Pescara, Chieti e L'Aquila (1° bollettino 2026/27).

## Aggiungere province o bollettini (automatico)
Carica i PDF nella cartella `bollettini` del repository (vedi `bollettini/LEGGIMI.md`): l'automazione
«Aggiorna dati GPS» li legge, aggiorna `assets/gps_data.json` e cancella i PDF. Poi ricostruisci l'app.

A mano (serve `pdftotext`, pacchetto *poppler-utils*):

    python tools/gps/build_gps_data.py --cartella bollettini --output assets/gps_data.json --aggiungi

- La provincia si riconosce dai codici delle scuole (se non succede usa `--provincia TE`).
- Il turno si legge dal nome del file (`...bollettino-2...`); senza numero vale 1. Un turno già presente
  viene sostituito, quelli nuovi si aggiungono.
- I formati letti finora sono i tre PDF di esempio (Excel esportato in PDF e «Stampa in PDF»).
  Se un file non si legge, il comando lo segnala e lo salta: mandami il PDF e adatto il lettore.

## Limiti
- Il bollettino n. 1 è solo il primo giro: nei successivi si scende più in basso, quindi la soglia
  reale a fine anno è più bassa. La stima è prudente.
- Le nomine dipendono dai posti: una provincia con tante nomine offre più occasioni.
- Con poche nomine (1–2) la soglia è poco significativa: nell'app compare il numero di nomine.
- Fascia I e II hanno punteggi non confrontabili e sono tenute separate.

## Riserva servizio civile (15%)
La riserva copre **il 15% dei chiamati di quella classe in quel bollettino (le due fasce insieme, arrotondato per difetto: 20 chiamati = 3 posti)**: l'algoritmo
scorre la graduatoria per punteggio e «salta» ai riservisti solo finché la quota non è raggiunta.
I bollettini non dicono chi sono i riservisti (colonne oscurate), quindi l'app mostra due soglie:

- **sicura**: punteggio dell'ultimo nominato dopo aver tolto il 15% dei punteggi più bassi (arrotondato
  per difetto, quindi con meno di 7 nomine non toglie nulla). Se il tuo punteggio la raggiunge, ci
  saresti anche con la quota piena → «Ci saresti».
- **minima**: punteggio dell'ultimo nominato in assoluto. Se la raggiungi ma non arrivi alla sicura →
  «Forse: dipende dalla riserva».

La percentuale è `GPS_RISERVA` in `main.py`. Ogni bollettino è un turno: per questo non vanno uniti
bollettini di turni diversi della stessa provincia (i PDF dello stesso turno, per esempio allegati A e B, sì).
