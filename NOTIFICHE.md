# Notifiche anche ad app chiusa

Un'app Flet chiusa non può controllare i siti da sola. Per questo il controllo lo fa **GitHub Actions**
(lo stesso servizio che costruisce l'APK) ogni circa 30 minuti, e la notifica arriva sul telefono
tramite l'app gratuita **ntfy**. Ricevi un avviso **solo per i nuovi interpelli delle tue classi**
(quelle del filtro «Per me»).

## Attivazione (una volta sola, 5 minuti)

1. **Installa ntfy** sul telefono (Play Store o F-Droid) e apri «Iscriviti a un canale».
   Scegli un nome difficile da indovinare: chi lo conosce può leggere le tue notifiche. Esempio:
   `interpelli-8c28c20be7` (meglio generarne uno tuo). Server: `ntfy.sh`.
2. Su GitHub apri il repository → **Settings → Secrets and variables → Actions**.
   - Scheda **Secrets** → *New repository secret*: nome `NTFY_TOPIC`, valore il nome del canale.
   - Scheda **Variables** → *New repository variable*: nome `NOTIFY_CLASSES`, valore le tue classi,
     per esempio `A028, A022, PPPP`. **Sono le stesse del filtro «Per me»**: nell'app, ⚙ → «Copia le
     classi per le notifiche» e incolla qui.
   - Facoltative: `NOTIFY_REGIONS` (es. `Toscana, Lazio`: controlla solo quelle regioni) e
     `NOTIFY_PROFILE` (`DOCENTI` oppure `ATA`).
3. Scheda **Actions** → «Notifiche nuovi interpelli» → **Run workflow**, spunta *Invia solo una
   notifica di prova* → deve arrivarti «Interpelli Scuola – prova».
4. Fine. La **prima esecuzione automatica registra gli interpelli già esistenti senza notificarli**;
   da lì in poi ricevi solo quelli nuovi.

## Se cambi le classi
Aggiorna la variabile `NOTIFY_CLASSES` su GitHub **e** le classi nell'app (⚙): sono due elenchi
separati, perché GitHub non può leggere i dati dal tuo telefono. Se `NOTIFY_CLASSES` è vuota non
arriva nessuna notifica.

## Cosa aspettarti
- **Ritardo:** i controlli partono circa ogni 30 minuti, ma GitHub può ritardarli (anche di un'ora nelle
  ore di punta). Non è una notifica istantanea.
- **Repository privato:** i minuti gratuiti sono 2000 al mese. Un controllo ne usa circa 1–2: se il
  repository è privato cambia `*/30` in `0 * * * *` (ogni ora) in `.github/workflows/notify.yml`.
- **Repository pubblico:** GitHub sospende i controlli programmati dopo 60 giorni senza attività nel
  repository; basta riattivarli dalla scheda Actions.
- **Cosa viene notificato:** solo avvisi con una delle tue classi nel titolo o all'inizio del testo,
  non scaduti e pubblicati di recente. Se la classe è scritta solo nel PDF allegato, l'avviso non
  viene riconosciuto (nemmeno nell'app).
- **Tanti avvisi insieme:** oltre 5 nuovi nello stesso controllo arriva un solo riepilogo.
- Toccando la notifica si apre l'avviso; il pulsante «Documento» apre l'allegato.
