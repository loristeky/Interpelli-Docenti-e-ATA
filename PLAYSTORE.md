# Pubblicare su Google Play

## ⚠️ Prima di tutto: il livello API richiesto
Dal 31 agosto 2026 Google Play accetta nuove app e aggiornamenti solo se puntano ad **Android 16
(API 36)**. L'app oggi è costruita con Flet 0.23.2 / Flutter 3.22, che punta ad **API 34**:
Play Console rifiuterebbe il caricamento. Il workflow qui sotto produce un .aab firmato correttamente,
ma **per essere accettato serve prima passare a una versione recente di Flet** (con Flutter aggiornato).
Il codice dell'app va adattato a quella versione e provato su un telefono: è il passo successivo.

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
Di default è `it.interpelliscuola.interpelli_scuola`. **Dopo la pubblicazione non si può più
cambiare.** Per sceglierne un altro crea (scheda Variables) `ANDROID_ORG`, es. `it.tuonome`.

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
