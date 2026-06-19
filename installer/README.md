# Creare l'installer (Setup.exe)

Genera un installer Windows classico (wizard + disinstallazione + icona) che il
tuo amico installa con un doppio-click. Include un Python autonomo, quindi
**non serve che lui abbia Python**. Le dipendenze pesanti opzionali (OpenCV per
il face-tracking, Whisper per i sottotitoli) si scaricano **on-demand** dall'app
quando attiva quelle funzioni.

## Cosa serve (solo sulla TUA macchina, una volta)
- Connessione internet
- **Python 3.11 completo** installato (serve per copiare i file di tkinter)
- **Inno Setup 6** → https://jrsoftware.org/isdl.php

## Build
Dalla radice del progetto:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

Lo script:
1. scarica Python 3.11 embeddable e gli aggiunge tkinter + pip,
2. installa le dipendenze core nel runtime,
3. copia l'app,
4. compila l'installer.

Risultato: **`installer\Output\DOPAMINIC-Setup.exe`** → è questo che mandi all'amico.

## Cosa ottiene l'amico
- Doppio-click su `DOPAMINIC-Setup.exe` → Avanti/Avanti/Fine, icona sul desktop.
- L'app parte e funziona subito per: highlight, taglio clip, crop centrale, watermark.
- Se attiva **Face-tracking** → l'app propone di scaricare OpenCV (una volta).
- Se attiva **Sottotitoli** → l'app propone di scaricare Whisper; il modello scelto
  (`small`, ecc.) si scarica al primo uso.
- Output e impostazioni vengono salvati in una cartella scrivibile dell'utente.

## Peso indicativo
Installer ~150–300 MB (Python + moviepy + ffmpeg + Pillow). OpenCV e Whisper si
aggiungono solo se servono. Il modello Whisper `small` (~480 MB) si scarica a parte.

## Note
- `installer\stage\` e `installer\Output\` sono generati dal build (git-ignored).
- Per cambiare nome/versione/publisher: `app.iss`, sezione `[Setup]`.
