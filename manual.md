# Manuale di DOPAMINIC

Conoscenza del programma usata dall'assistente. Ogni sezione `##` è una risposta
auto-contenuta; la riga "Parole chiave:" aiuta l'assistente a trovarla.

## Cos'è il programma
Parole chiave: cosa fa, a cosa serve, programma, introduzione, panoramica, come funziona
Trasformo un video lungo in più short verticali (9:16), tutto in locale sul tuo PC.
Analizzo l'audio per trovare i momenti più "rumorosi" (gli highlight), taglio le clip,
le porto in verticale, e posso aggiungere watermark e sottotitoli. Gli short finiti
vanno nella cartella output. C'è anche una tab YouTube per programmarne la pubblicazione.

## Come generare gli short
Parole chiave: generare, genero, generazione, creare, come si fa, avviare, produrre, genera, start, passi, short, spezzare, tagliare
1) Tab "Genera", premi "Sfoglia" e scegli il video lungo.
2) Imposta numero di short e durata.
3) (Opzionale) attiva watermark, sottotitoli, face-tracking.
4) Premi "GENERA SHORT" e aspetta: vedi l'avanzamento nel log in basso.
Gli short finiti finiscono nella cartella output (pulsante "Apri cartella output").

## Modalita' di rilevamento highlight (loudness e talk)
Parole chiave: rilevamento, modalita', loudness, talk, rumore, parlato, monologhi, longplay, by talk, by loudness, come trovo i momenti
Nella tab Genera scegli come trovo i momenti da tagliare. "Per rumore (loudness)" e'
il default: prendo i tratti piu' rumorosi, di solito risate, urla, azione. "Per parlato
(talk)" invece trascrive tutto il video e prende i monologhi piu' lunghi, scartando
rumore e musica: e' pensato per i longplay in cui parli solo a tratti e vuoi beccare i
momenti in cui parli. La trascrizione completa viene salvata in cache: se rilanci sullo
stesso video (stesso modello e lingua) non la rifaccio, e la riuso anche per i
sottotitoli senza ri-trascrivere clip per clip. La modalita' talk e' piu' pesante: con
video lunghi conviene la GPU. Nel log vedi una barra di avanzamento della trascrizione.

## Aggiornamenti e versioni
Parole chiave: aggiornamento, aggiornare, versione, versioni, update, release, downgrade, changelog, novita'
In alto c'e' il pulsante "Versioni": apre l'elenco delle release pubblicate su GitHub, con il
changelog di ognuna. Da li' puoi installare qualsiasi versione, anche tornare a una precedente
(downgrade) per verificare. All'avvio controllo da solo se ce n'e' una piu' nuova: se si', sul
pulsante "Versioni" compare un asterisco. Installando, scarico il pacchetto e lo lancio: si
aggiorna sul posto. Serve connessione a internet solo in quel momento.

## Anteprima e modifica delle clip
Parole chiave: anteprima, preview, editor, modifica, ritoccare, timeline, conferma, annulla, testina, inizio, fine
Dopo aver premuto GENERA SHORT individuo i momenti e apro una finestra di anteprima
stile editor. Li' vedi i fotogrammi trascinando la testina sulla timeline (un tasto Play
li riproduce con l'audio della clip), e per ogni clip puoi ritoccare inizio e fine: trascini le
maniglie verde (inizio) e rossa (fine), oppure aggiusti coi tasti -30s/-1s/+1s/+30s quando
col trascinamento non sei preciso. Puoi aggiungere una nuova clip alla testina con
"Aggiungi clip" e togliere quella selezionata con "Rimuovi clip". Quando sei a posto premi
"Conferma e genera" per produrre gli short, oppure "Annulla" per non generare niente. Il
pulsante "Anteprima" riapre l'editor sull'ultimo rilevamento senza rifarlo. Se il video e'
lungo e le clip si vedono piccole, usa lo zoom della timeline (tasti +/- o rotella del
mouse) e la barra di scorrimento sotto per spostarti nel punto giusto.

## Numero di short e durata
Parole chiave: numero, quanti, durata, secondi, lunghezza, clip
"Numero di short" = quante clip estrarre. "Durata" = lunghezza di ognuna in secondi.
Se il video è troppo corto per i valori scelti, li adatto in automatico. Se trovo meno
momenti distinti di quelli richiesti, genero quelli disponibili e te lo dico nel log.

## Tracking del crop (OpenCV e VTUBER)
Parole chiave: tracking, face tracking, volti, opencv, vtuber, avatar, inquadratura, crop, ritaglio, destra, sinistra
Il crop verticale ha una spunta "Tracking" e un menu con la modalità. Spento = crop centrale
veloce. "OpenCV (volti)" segue il volto più centrato (più lento, richiede la libreria OpenCV
che ti propongo da scaricare al primo uso; se il video non ha volti lascialo perdere).
"VTUBER destra" e "VTUBER sinistra" alternano ogni 5 secondi tra il centro dello schermo e il
lato dove sta l'avatar (destra o sinistra): così mostri un po' di gameplay e un po' l'avatar, a
turno. Le modalità VTUBER non richiedono OpenCV e sono veloci.

## Watermark
Parole chiave: watermark, logo, firma, testo sovraimpresso, marchio
Aggiunge un testo semitrasparente in basso al video. Attiva la spunta "Watermark" e
scrivi il testo che vuoi (es. il tuo @nome). Si può disattivare.

## Sottotitoli
Parole chiave: sottotitoli, subtitle, whisper, trascrizione, testo, captions, lingua
I sottotitoli sono generati in locale con Whisper. Attiva "Sottotitoli (Whisper locale)".
Al primo uso ti propongo di scaricare la libreria. Puoi scegliere la LINGUA (consiglio
"it" per l'italiano, così non sbaglia lingua) e il MODELLO (più grande = più preciso ma
più lento/pesante). I sottotitoli sono sincronizzati parola per parola.

## Modello Whisper e dimensioni
Parole chiave: modello, whisper, tiny, base, small, medium, large, peso, dimensione
Modelli disponibili: tiny (~75 MB), base (~145 MB), small (~480 MB), medium (~1.5 GB),
large-v3 (~3 GB). Più grande = più accurato ma più lento e pesante. Default consigliato:
base o small per l'italiano. Il modello si scarica al primo utilizzo.

## GPU NVIDIA per i sottotitoli
Parole chiave: gpu, nvidia, cuda, scheda video, vram, accelerazione, veloce
Se hai una GPU NVIDIA puoi attivare "Usa GPU": la trascrizione va molto più veloce,
specie con i modelli grandi. Al primo uso scarico le librerie CUDA (~1 GB). Se non hai
NVIDIA o manca qualcosa, uso automaticamente la CPU senza bloccarmi. La riga sotto la
spunta ti dice quanta VRAM hai e quale modello ti consiglio.

## Stile dei sottotitoli (font, dimensione, contorno)
Parole chiave: font, stile, colore, dimensione, contorno, aspetto, carattere, anteprima
Pulsante "Stile..." apre un editor con anteprima in tempo reale: scegli font
(PT Sans, Anton, Bebas Neue, Poppins, Bangers), dimensione, spessore del contorno nero e
colore del testo. Vedi subito come verrà mentre cambi i valori.

## Cartella output
Parole chiave: output, dove finiscono, file, cartella, salvati, risultato, trovo
Gli short generati vanno nella cartella output. Dalla tab "Genera" premi "Apri cartella
output" per aprirla. Se il programma è installato, output e impostazioni stanno in una
cartella scrivibile nella tua home utente.

## Tab YouTube: panoramica
Parole chiave: youtube, caricare, upload, pubblicare, canale, programmare
Nella tab "YouTube" colleghi il tuo canale, definisci degli slot settimanali, assegni
automaticamente i video della cartella output agli slot e li carichi programmati. Funziona
come la programmazione di Buffer/YouTube Studio.

## Collegare il canale YouTube (OAuth)
Parole chiave: account, oauth, client secret, collegare, accesso, autorizzazione, google
Premi "Configura accesso..." e seleziona il tuo file client_secret.json (lo crei nella
Google Cloud Console, abilitando "YouTube Data API v3" e creando credenziali OAuth tipo
"App desktop"). Si apre il browser, accedi col canale e dai il permesso: lo fai una volta.

## Slot settimanali e auto-assegnazione
Parole chiave: slot, calendario, programmazione, settimanali, auto assegna, pianificazione
Definisci gli slot (giorno + ora) in cui vuoi pubblicare. Premi "Auto-assegna" e assegno
ogni video della cartella output al prossimo slot libero, mostrandoti il calendario.
Poi "Carica e programma" li carica come privati con orario di pubblicazione automatico.

## Upload programmato: come funziona
Parole chiave: programmato, privato, pubblico, publishat, pubblicazione, quando esce
I video vengono caricati subito ma come PRIVATI, con un orario di pubblicazione: YouTube
li rende pubblici da solo all'orario dello slot. Non perdi il "boost" dell'algoritmo,
perché la spinta parte da quando diventa pubblico. C'è un limite di ~6 caricamenti al
giorno (quota YouTube): gli altri li carichi un altro giorno.

## Il secondo video si blocca / è lentissimo
Parole chiave: blocco, bloccato, lento, loop, non finisce, freeze, piantato, errore
Se la generazione sembra ferma: con i sottotitoli su GPU il modello ora viene caricato
una volta sola (prima poteva incantarsi sul secondo short). Con face-tracking ON su video
senza volti era lentissimo: ora è risolto. Se è solo lento, prova un modello Whisper più
piccolo, disattiva il face-tracking, o usa la GPU.

## Errori e crash all'avvio
Parole chiave: errore, crash, non parte, non si avvia, problema, log
Se l'app non parte, controlla il file crash.log (nella cartella del programma o nella tua
home, in DOPAMINIC). Contiene il dettaglio dell'errore. Le funzioni pesanti (OpenCV,
Whisper, GPU, YouTube) si scaricano al primo uso: serve internet quella prima volta.
