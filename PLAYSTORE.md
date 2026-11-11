# Pubblicare su Google Play

## Stato del progetto
L'app usa **Flet 1.0.4**, che costruisce per Android 16 (API 36), come richiesto da Google Play dal
31 agosto 2026. Android minimo: 7.0 (API 24). Nome, identificativo e versione minima sono in
`pyproject.toml`.

## 1. Crea la chiave di caricamento (una volta sola, sul tuo computer)
Serve Java (`keytool`). Esegui:

    keytool -genkeypair -v -storetype JKS -keystore upload.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000

Scegli una password e conservala. **Salva `upload.jks` e le password in un posto sicuro (gestore di
password + copia di backup). Non metterli mai nel repository.** Con «Play App Signing» (attivo di
default) la chiave definitiva dell'app la custodisce Google: se perdi quella di caricamento si può
chiedere a Google di sostituirla, ma è una procedura lunga.

## 2. Metti la chiave nei Secrets di GitHub
Converti il file in testo: Linux/Mac `base64 -w0 upload.jks`, Windows PowerShell
`[Convert]::ToBase64String([IO.File]::ReadAllBytes("upload.jks"))`.
Repository → Settings → Secrets and variables → Actions → **Secrets**:

| Nome | Valore |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | il testo base64 |
| `ANDROID_KEYSTORE_PASSWORD` | password del keystore |
| `ANDROID_KEY_ALIAS` | `upload` |
| `ANDROID_KEY_PASSWORD` | password della chiave |

## 3. Identificativo dell'app
È `it.interpelliscuola.interpelli_scuola`, scritto in `pyproject.toml` (`bundle_id`). **Dopo la
pubblicazione non si può più cambiare.** Se vuoi un altro nome, modificalo lì **prima** del primo
caricamento su Play.

## 4. Costruisci il file
Actions → «Build AAB per Google Play» → Run workflow (indica la versione, es. 1.0.0). Il numero di
versione interno aumenta da solo a ogni esecuzione, come richiesto da Play. Scarica l'artifact
`interpelli-scuola-aab`. Nel log «Verifica la firma» compare l'impronta SHA256: deve essere la stessa
a ogni build.

## 5. Play Console
1. Account sviluppatore Google Play (tassa una tantum di 25 $).
2. Crea l'app → carica il .aab in un test (interno o chiuso). Gli account personali nuovi devono in
   genere fare un test chiuso con almeno 12 tester per 14 giorni prima della produzione: verifica le
   regole attuali in Play Console.
3. Scheda dello store: nome, descrizione, icona 512×512 (`store/icona-512.png`), immagine in
   evidenza 1024×500, almeno 2 screenshot del telefono.
4. **Informativa sulla privacy** (URL pubblico): obbligatoria. L'app salva solo sul telefono le tue
   classi, nome e telefono e non li invia a nessuno.
5. Modulo «Sicurezza dei dati», classificazione dei contenuti, pubblico di destinazione.
6. Le fonti sono siti pubblici di scuole e uffici scolastici: nella descrizione indica che l'app non
   è ufficiale e non è collegata al Ministero.

## 6. Testo di avvertenza per la scheda del Play Store
Aggiungi in fondo alla descrizione completa (e tienilo coerente con l'app):

    Interpelli Scuola non è collegata né affiliata al Ministero dell'Istruzione e del Merito né agli Uffici
    scolastici. Gli avvisi sono pubblici e vengono letti dai siti ufficiali; ogni avviso rimanda alla pagina
    originale, che fa sempre fede. Le date lette da immagini sono segnate con ⚠ e vanno verificate.
    Per correzioni o rimozioni di una fonte: lorisbono@hotmail.it. Informativa: (link alla privacy policy).

Nella sezione «Sicurezza dei dati» dichiara che l'app non raccoglie né condivide dati personali (coerente con
la privacy policy). Non usare nel Play Store lo stemma della Repubblica né i loghi del Ministero o degli Uffici.


## 7. Descrizioni complete per Google Play (rifiuto «link alla fonte mancante»)
Sostituisci la descrizione completa in ENTRAMBE le lingue (it e en-US), poi invia l'aggiornamento.

### Italiano

    Interpelli Scuola è un'app INDIPENDENTE: non rappresenta alcun ente governativo e non è collegata né affiliata al Ministero dell'Istruzione e del Merito né agli Uffici Scolastici.
    
    Raccoglie in un unico posto gli interpelli e le convocazioni pubblicati dagli Uffici Scolastici e dalle scuole, con filtri per classe di concorso, provincia e scadenza, promemoria e calendario delle scadenze.
    
    FONTI UFFICIALI (informazioni governative)
    Tutte le informazioni provengono da siti pubblici ufficiali. Ogni avviso mostra il link alla pagina originale, che fa sempre fede; l'elenco completo delle fonti è nell'app (menu Fonti).
    • Ministero dell'Istruzione e del Merito: https://www.mim.gov.it/
    • https://ag.usr.sicilia.it/
    • https://atpromaistruzione.it/
    • https://bo.istruzioneer.gov.it/
    • https://cl-en.usr.sicilia.it/
    • https://csalatina.it/
    • https://csateramo.it/
    • https://ct.usr.sicilia.it/
    • https://fc.istruzioneer.gov.it/
    • https://fe.istruzioneer.gov.it/
    • https://istruzione-ancona.it/
    • https://istruzione.calabria.it/
    • https://istruzione.umbria.it/
    • https://istruzioneatprc.it/
    • https://istruzionechietipescara.it/
    • https://istruzionematera.it/
    • https://istruzionepiemonte.it/
    • https://lnx.csalaquila.it/
    • https://me.usr.sicilia.it/
    • https://mo.istruzioneer.gov.it/
    • https://pa.usr.sicilia.it/
    • https://padova.istruzioneveneto.gov.it/
    • https://pc.istruzioneer.gov.it/
    • https://pr.istruzioneer.gov.it/
    • https://provveditoratostudiviterbo.it/
    • https://ra.istruzioneer.gov.it/
    • https://re.istruzioneer.gov.it/
    • https://rn.istruzioneer.gov.it/
    • https://rovigo.istruzioneveneto.gov.it/
    • https://scuole.vda.it/
    • https://servizi.istruzioneliguria.gov.it/
    • https://sr.usr.sicilia.it/
    • https://tp.usr.sicilia.it/
    • https://treviso.istruzioneveneto.gov.it/
    • https://uat-caserta.it/
    • https://uat-napoli.it/
    • https://usp-pi.it/
    • https://uspbari.it/
    • https://uspistruzione.fr.it/
    • https://usplecce.it/
    • https://usppesarourbino.it/
    • https://uspss.it/
    • https://usptaranto.it/
    • https://ust.fi.it/
    • https://ustfoggia.it/
    • https://ustlucca.it/
    • https://venezia.istruzioneveneto.gov.it/
    • https://verona.istruzioneveneto.gov.it/
    • https://vivoscuola.it/
    
    Le date lette da immagini sono segnate con ⚠ e vanno verificate nell'avviso originale. Le stime GPS sono indicative.
    Correzioni o rimozioni di una fonte: lorisbono@hotmail.it
    Privacy: https://github.com/loristeky/Interpelli-Docenti-e-ATA/blob/main/privacy-policy.md

### English (en-US)

    Interpelli Scuola is an INDEPENDENT app: it does not represent any government entity and is not connected to or affiliated with the Italian Ministry of Education and Merit or any School Offices.
    
    It gathers in one place the school job notices (interpelli) published by Italian School Offices and schools, with filters by teaching class, province and deadline, reminders and a deadline calendar.
    
    OFFICIAL SOURCES (government information)
    All information comes from official public websites. Every notice links to the original page, which always prevails; the full list of sources is in the app (Sources menu).
    • Ministry of Education and Merit: https://www.mim.gov.it/
    • https://ag.usr.sicilia.it/
    • https://atpromaistruzione.it/
    • https://bo.istruzioneer.gov.it/
    • https://cl-en.usr.sicilia.it/
    • https://csalatina.it/
    • https://csateramo.it/
    • https://ct.usr.sicilia.it/
    • https://fc.istruzioneer.gov.it/
    • https://fe.istruzioneer.gov.it/
    • https://istruzione-ancona.it/
    • https://istruzione.calabria.it/
    • https://istruzione.umbria.it/
    • https://istruzioneatprc.it/
    • https://istruzionechietipescara.it/
    • https://istruzionematera.it/
    • https://istruzionepiemonte.it/
    • https://lnx.csalaquila.it/
    • https://me.usr.sicilia.it/
    • https://mo.istruzioneer.gov.it/
    • https://pa.usr.sicilia.it/
    • https://padova.istruzioneveneto.gov.it/
    • https://pc.istruzioneer.gov.it/
    • https://pr.istruzioneer.gov.it/
    • https://provveditoratostudiviterbo.it/
    • https://ra.istruzioneer.gov.it/
    • https://re.istruzioneer.gov.it/
    • https://rn.istruzioneer.gov.it/
    • https://rovigo.istruzioneveneto.gov.it/
    • https://scuole.vda.it/
    • https://servizi.istruzioneliguria.gov.it/
    • https://sr.usr.sicilia.it/
    • https://tp.usr.sicilia.it/
    • https://treviso.istruzioneveneto.gov.it/
    • https://uat-caserta.it/
    • https://uat-napoli.it/
    • https://usp-pi.it/
    • https://uspbari.it/
    • https://uspistruzione.fr.it/
    • https://usplecce.it/
    • https://usppesarourbino.it/
    • https://uspss.it/
    • https://usptaranto.it/
    • https://ust.fi.it/
    • https://ustfoggia.it/
    • https://ustlucca.it/
    • https://venezia.istruzioneveneto.gov.it/
    • https://verona.istruzioneveneto.gov.it/
    • https://vivoscuola.it/
    
    Dates read from images are marked ⚠ and must be checked in the original notice. GPS estimates are indicative.
    Corrections or source removal: lorisbono@hotmail.it
    Privacy: https://github.com/loristeky/Interpelli-Docenti-e-ATA/blob/main/privacy-policy.md
