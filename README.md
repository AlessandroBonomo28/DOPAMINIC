# DOPAMINIC

<img width="90%" alt="Immagine 2026-06-19 233213" src="https://github.com/user-attachments/assets/927b6c7f-43ec-46eb-ad98-81e1189d45fd" />

Prendi un video lungo e in pochi minuti ne tiri fuori una manciata di short verticali pronti da pubblicare, senza mandare niente in giro per internet e senza API a pagamento. Tutto gira sul tuo PC.

L'idea è semplice: i momenti che funzionano in un video di solito sono quelli in cui succede qualcosa, e quasi sempre dove succede qualcosa il volume sale. DOPAMINIC ascolta l'audio, trova i picchi, ritaglia le clip attorno a quei picchi e te le sforna già in 9:16, con watermark e sottotitoli se li vuoi. Niente account, niente cloud, niente chiavi da configurare per generare gli short.

Il criceto sulla destra si chiama CRI ed è un assistente locale che non usa GPU e nemmeno LLM, ha un albero di if ma risponderà a tutte le tue domande sul funzionamento del programma, è un criceto che **sa il fatto suo**. E' molto pigro e si stanca si mette a dormire 

<img width="100%"  alt="2026-06-19 23-37-29" src="https://github.com/user-attachments/assets/5a476cfc-3f7a-4acc-8434-1a4ffe4544dd" />

## Cosa fa, passo per passo

1. Analizza l'audio del video e individua i momenti più rumorosi (gli highlight).
2. Taglia N clip attorno a quei picchi, in ordine cronologico.
3. Porta ogni clip in verticale 9:16: crop centrale veloce, oppure face-tracking con OpenCV che segue il volto.
4. Aggiunge il watermark e, se attivi, i sottotitoli generati in locale con Whisper, sincronizzati parola per parola.
5. Salva gli short pronti nella cartella di output.

Il testo (watermark e sottotitoli) viene disegnato con Pillow, quindi non serve ImageMagick né nessun altro programma di sistema. L'unica cosa che scarica da sola è ffmpeg, ma lo fa tramite `imageio-ffmpeg` e non devi installarlo a mano.

## Avvio rapido (da sorgente)

```bash
# 1. Installa le dipendenze base (una volta sola)
pip install -r requirements.txt

# 2. Avvia
python app.py
```

Su Windows puoi anche fare doppio clic su `run.bat`. Su Linux o Mac c'è `run.sh`. Entrambi usano in automatico la virtualenv `env/` se la trovano, altrimenti il Python di sistema.

Serve Python 3.11. Le funzioni pesanti (face-tracking e sottotitoli) non sono nel pacchetto base: la prima volta che le attivi, l'app ti chiede se vuole installarle al volo. Se preferisci farlo a mano:

```bash
pip install opencv-python     # per il face-tracking
pip install faster-whisper    # per i sottotitoli
```

Il modello Whisper (tiny, base, small, medium oppure large-v3) si scarica al primo utilizzo. Dimensione e lingua le scegli dall'interfaccia e restano salvate.

## L'interfaccia

Tre schede in alto: Genera, YouTube e Impostazioni.

Nella scheda Genera scegli il video, imposti quanti short vuoi e quanto devono durare, e accendi quello che ti serve: watermark con il tuo testo, face-tracking, sottotitoli con lingua e modello, stile dei sottotitoli (font, dimensione, contorno, colore) con anteprima dal vivo. Premi GENERA SHORTS e il log in basso ti dice a che punto è. Quando ha finito apri la cartella di output con un pulsante.

A tenerti compagnia mentre lavora c'è CRI il criceto, un assistente offline a cui puoi fare domande sul programma: sa rispondere leggendo il manuale incluso e fa anche due chiacchiere. Se lo lasci stare per un po' si addormenta sulla ruota, e si sveglia appena gli scrivi. Il nome glielo puoi cambiare dalle impostazioni.

Sopra a tutto trovi i tre interruttori rapidi: lingua (italiano o inglese, cambia tutti i testi e pure le risposte di CRI), tema (scuro o chiaro) e musica (accesa o muta). Dietro al log c'è un piccolo visualizzatore audio in stile vecchio lettore multimediale che reagisce alla musica di sottofondo.

Dalle Impostazioni regoli la musica (file, volume, mute), il nome dell'assistente, gli effetti sonori in stile MSN (click, cambio scheda, invio, risposta), le animazioni, e trovi la sezione About con i link.

## Sottotitoli e GPU

I sottotitoli sono generati in locale con Whisper, quindi non lasciano il PC. Puoi forzare la lingua (metti "it" o "en" così non sbaglia quando ci sono voci sovrapposte o musica) e scegliere il modello: più è grande più è preciso, ma è anche più lento e pesante.

Se hai una scheda NVIDIA puoi attivare la GPU: la trascrizione diventa molto più veloce, soprattutto con i modelli grossi. Al primo utilizzo l'app scarica le librerie CUDA. Se non hai una NVIDIA o manca qualcosa, torna in automatico sulla CPU. La riga sotto la spunta ti dice quanta VRAM hai e quale modello conviene.

## La sezione YouTube

Questa parte serve a programmare la pubblicazione degli short che hai generato, un po' come fa Buffer o lo strumento di pianificazione di YouTube Studio. Definisci degli slot settimanali (giorno e ora), premi l'assegnazione automatica e DOPAMINIC mette ogni video nel primo slot libero, mostrandoti il calendario. Poi con il caricamento i video vengono messi su come privati con un orario di pubblicazione: ci pensa YouTube a renderli pubblici da solo all'ora dello slot, così non perdi la spinta dell'algoritmo che parte quando il video diventa pubblico.

Per collegare il canale serve un file `client_secret.json`, che è la cosa un po' più macchinosa di tutto il programma perché va creato sulla Google Cloud Console. La procedura è spiegata bene qui:

https://wpythub.com/documentation/getting-started/set-youtube-oauth-client-id-client-secret/

Una avvertenza importante: nella guida a un certo punto fanno creare le credenziali OAuth come "Web application". Per DOPAMINIC NON va bene, perché questa non è una web app ma un programma desktop. Quando arrivi a quel passaggio scegli "Desktop app" come tipo di applicazione (il resto della guida, cioè abilitare la "YouTube Data API v3" e creare le credenziali OAuth, vale uguale). Scaricato il JSON, dal programma premi "Configura accesso", selezioni il file, si apre il browser, accedi col canale e dai il consenso. Lo fai una volta sola.

Tieni presente il limite di YouTube di circa 6 caricamenti al giorno via API: il resto lo carichi un altro giorno. Il `client_secret.json` e il token salvato dopo l'accesso sono dati tuoi e restano sul tuo PC, sono già esclusi da git e non vanno condivisi con nessuno.

## Creare l'installer (Setup.exe)

Se vuoi dare il programma a un amico senza fargli installare Python o configurare niente, puoi impacchettare tutto in un classico installer Windows con wizard, icona e disinstallazione. Dentro c'è già un Python autonomo, quindi sul suo PC non serve nient'altro. Le dipendenze pesanti (OpenCV e Whisper) restano on-demand e si scaricano dall'app solo quando lui attiva quelle funzioni.

Sul tuo PC, una volta sola, ti serve: connessione internet, un Python 3.11 completo installato (serve solo per copiare i file di tkinter dentro al pacchetto) e Inno Setup 6, che prendi da https://jrsoftware.org/isdl.php.

Poi, dalla radice del progetto:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

Lo script scarica un Python 3.11 embeddable, gli inietta tkinter e pip, installa le dipendenze base nel runtime, copia l'app e gli asset, e compila l'installer con Inno Setup. Alla fine trovi `installer\Output\DOPAMINIC-Setup.exe`: è questo il file da mandare. Per cambiare nome, versione o publisher dell'installer apri `installer\app.iss` nella sezione `[Setup]`. Tutti i dettagli sono in [installer/README.md](installer/README.md).

## Struttura del progetto

```
app.py                  GUI tkinter, punto di ingresso
launch.py               avvio con log di crash (usato dall'installer)
clipper/
  highlights.py         rilevamento dei momenti più rumorosi
  cropping.py           crop verticale: centrale o face-tracking OpenCV
  subtitles.py          sottotitoli locali con Whisper
  textrender.py         rendering del testo con Pillow
  pipeline.py           orchestrazione del flusso long verso shorts
  youtube_uploader.py   OAuth, slot e caricamento programmato
  assistant.py          il criceto CRI (chat offline)
  music.py              musica, effetti sonori e visualizzatore
  deps.py               installazione on-demand di opencv e whisper
  settings.py           impostazioni persistenti
data/                   classificatore Haar per i volti
fonts/                  font per watermark e sottotitoli
installer/              build dell'installer Windows (Inno Setup)
manual.md, manual_en.md conoscenza usata da CRI per rispondere
```

## Dove finiscono i file

In sviluppo, output, impostazioni e file temporanei stanno nella cartella del progetto. Quando l'app è installata in una posizione di sola lettura, scrive invece nella cartella `DOPAMINIC` dentro la home dell'utente. Lì trovi anche il `crash.log` se qualcosa va storto all'avvio.

## Crediti

Scritto da goodman. Il software è libero da multinazionali cattive, dormi tranquillo.

<img width="220" height="224" alt="gotosleep" src="https://github.com/user-attachments/assets/00962d74-df09-41f2-be59-739acb386d08" />

GitHub: https://github.com/AlessandroBonomo28/DOPAMINIC

Se ti è utile e ti va di offrire un caffè: https://buymeacoffee.com/servizibon0

La musica di default è "Rolling Down The Street, In My Katamari".
