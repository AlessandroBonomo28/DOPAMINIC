"""GUI DOPAMINIC (100% locale).

Interfaccia in tema scuro costruita solo con tkinter/ttk (nessuna dipendenza extra).
Avvio:  python app.py
"""
import colorsys
import math
import os
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from moviepy.editor import VideoFileClip

from clipper import OUTPUT_DIR, APP_VERSION
from clipper.pipeline import detect_clips, render_clips
from clipper.settings import load_settings, save_settings

# --- Temi: light (retro XP grigio) e dark ---
LIGHT = {
    "BG": "#c0c0c0", "CARD": "#c0c0c0", "SUCCESS": "#c0c0c0",
    "INPUT_BG": "#ffffff", "LOG_BG": "#ffffff",
    "FG": "#000000", "MUTED": "#404040", "ACCENT": "#000080",
    "SUCCESS_HOVER": "#d4d0c8", "VIZ_BG": "#0b0b16", "XP_BLUE": "#0a246a",
    "XP_SHADOW": "#808080",
}
DARK = {
    "BG": "#2d2d30", "CARD": "#2d2d30", "SUCCESS": "#2d2d30",
    "INPUT_BG": "#1e1e1e", "LOG_BG": "#1e1e1e",
    "FG": "#e6e6e6", "MUTED": "#9a9a9a", "ACCENT": "#7aa2ff",
    "SUCCESS_HOVER": "#3e3e42", "VIZ_BG": "#0b0b16", "XP_BLUE": "#0a246a",
    "XP_SHADOW": "#555555",
}
PALETTES = {"light": LIGHT, "dark": DARK}

# Variabili di palette (riassegnate da apply_palette)
BG = CARD = SUCCESS = INPUT_BG = LOG_BG = FG = MUTED = ACCENT = ""
SUCCESS_HOVER = VIZ_BG = XP_BLUE = XP_SHADOW = ""


def apply_palette(p):
    global BG, CARD, SUCCESS, INPUT_BG, LOG_BG, FG, MUTED, ACCENT
    global SUCCESS_HOVER, VIZ_BG, XP_BLUE, XP_SHADOW
    BG, CARD, SUCCESS = p["BG"], p["CARD"], p["SUCCESS"]
    INPUT_BG, LOG_BG = p["INPUT_BG"], p["LOG_BG"]
    FG, MUTED, ACCENT = p["FG"], p["MUTED"], p["ACCENT"]
    SUCCESS_HOVER, VIZ_BG, XP_BLUE, XP_SHADOW = p["SUCCESS_HOVER"], p["VIZ_BG"], p["XP_BLUE"], p["XP_SHADOW"]


apply_palette(LIGHT)

# Traduzioni UI (italiano -> inglese). La rietichettatura cerca il testo esatto.
UI_TRANS = {
    "Da un video lungo a piu' short dopaminici verticali. Tutto in locale.":
        "Turn a long video into vertical dopaminic shorts. Fully local.",
    "  Genera  ": "  Generate  ",
    "  Impostazioni  ": "  Settings  ",
    "SORGENTE": "SOURCE",
    "📁  Sfoglia": "📁  Browse",
    "Numero di short": "Number of shorts",
    "Durata (s)": "Duration (s)",
    "Rilevamento highlight": "Highlight detection",
    "loudness = momenti più rumorosi (default).  talk = i monologhi più\n"
    "lunghi, trascrivendo il video (ottimo per i longplay in cui parli a tratti).":
        "loudness = loudest moments (default).  talk = the longest monologues,\n"
        "by transcribing the video (great for longplays where you talk now and then).",
    "OpenCV = segue i volti.  YOUTUBER FACE = alterna ogni 5s centro/lato dove sta\n"
    "l'avatar.  Longplay = inquadra chi parla nelle cutscene e segue l'azione nel\n"
    "gameplay.  Tracking spento = crop centrale.":
        "OpenCV = follows faces.  YOUTUBER FACE = every 5s alternates center/side where the\n"
        "avatar sits.  Longplay = frames who talks in cutscenes and follows the action in\n"
        "gameplay.  Tracking off = center crop.",
    "STILE": "STYLE",
    "Sottotitoli (Whisper locale)": "Subtitles (local Whisper)",
    "Colore": "Color",
    "Stile...": "Style...",
    "Lingua": "Language",
    "Modello Whisper": "Whisper model",
    "Usa GPU (NVIDIA)": "Use GPU (NVIDIA)",
    "Molto più veloce sui modelli grandi. Richiede una GPU NVIDIA;\n"
    "al primo uso scarica le librerie CUDA (~1 GB). Altrimenti usa la CPU.":
        "Much faster on big models. Requires an NVIDIA GPU;\n"
        "first use downloads the CUDA libraries (~1 GB). Otherwise uses the CPU.",
    "Versioni": "Versions",
    "GENERA SHORT": "GENERATE SHORTS",
    "GENERAZIONE IN CORSO...": "GENERATING...",
    "RILEVAMENTO...": "DETECTING...",
    "Anteprima": "Preview",
    "Apri cartella output": "Open output folder",
    "Invia": "Send",
    "Pronto. Seleziona un video e premi GENERA.":
        "Ready. Select a video and press GENERATE.",
    "ACCOUNT YOUTUBE": "YOUTUBE ACCOUNT",
    "Configura accesso...": "Set up access...",
    "Serve un file client_secret.json (Google Cloud Console, YouTube Data API v3,\n"
    "credenziali OAuth tipo «Desktop»). I video vengono caricati come privati e\n"
    "pubblicati in automatico all'orario dello slot.":
        "You need a client_secret.json file (Google Cloud Console, YouTube Data API v3,\n"
        "OAuth credentials of type «Desktop»). Videos are uploaded as private and\n"
        "auto-published at the slot time.",
    "Leggi le info sul repo di DOPAMINIC per configurare il client_secret di YouTube:":
        "Read the DOPAMINIC repo info to set up the YouTube client_secret:",
    "SLOT SETTIMANALI": "WEEKLY SLOTS",
    "Azzera": "Clear",
    "VIDEO IN OUTPUT -> PIANIFICAZIONE": "OUTPUT VIDEOS -> SCHEDULE",
    "Aggiorna": "Refresh",
    "Auto-assegna": "Auto-assign",
    "METADATI PREDEFINITI": "DEFAULT METADATA",
    "Titolo (max 100 caratteri; vuoto = nome del file)":
        "Title (max 100 chars; empty = file name)",
    "Descrizione (max 5000 caratteri)": "Description (max 5000 chars)",
    "Carica e programma su YouTube": "Upload and schedule on YouTube",
    "Non connesso.": "Not connected.",
    "MUSICA DI SOTTOFONDO": "BACKGROUND MUSIC",
    "Musica in loop": "Loop music",
    "Brano": "Track",
    "Scegli MP3...": "Choose MP3...",
    "ASSISTENTE (CRICETO)": "ASSISTANT (HAMSTER)",
    "Nome dell'assistente": "Assistant name",
    "Va a dormire dopo (secondi, 0 = mai)": "Sleeps after (seconds, 0 = never)",
    "Gif da sveglio (idle)": "Awake gif (idle)",
    "Gif addormentamento": "Falling-asleep gif",
    "Immagine che dorme (PNG)": "Sleeping image (PNG)",
    "SUONI (STILE MSN)": "SOUNDS (MSN STYLE)",
    "Effetti sonori (invio e risposta)": "Sound effects (send and reply)",
    "Suono invio": "Send sound",
    "Suono risposta": "Reply sound",
    "Scegli...": "Choose...",
    "Prova": "Test",
    "ANIMAZIONI": "ANIMATIONS",
    "Visualizzatore stile Media Player dietro al log":
        "Media Player style visualizer behind the log",
    "Applica impostazioni": "Apply settings",
    "Font": "Font",
    "Dimensione": "Size",
    "Spessore contorno": "Outline thickness",
    "Colore testo": "Text color",
    "Anteprima:": "Preview:",
    "Chiudi": "Close",
    "(default)": "(default)",
    "(brano di default)": "(default track)",
    "Musica: ON": "Music: ON",
    "Musica: MUTO": "Music: MUTED",
    "Tema: Scuro": "Theme: Dark",
    "Tema: Chiaro": "Theme: Light",
    "Questo software è gratuito, approfittane.":
        "This software is free to use, benefit from it.",
    "Autore: goodman": "Author: goodman",
}

# --- Font retro (Tahoma e' lo storico font di XP) ---
F_TITLE = ("Tahoma", 12, "bold")
F_SUB = ("Tahoma", 8)
F_SECTION = ("Tahoma", 8, "bold")
F_LABEL = ("Tahoma", 8)
F_BTN = ("Tahoma", 8, "bold")
F_MONO = ("Courier New", 9)

# Secondi di permanenza per salire di un livello di chill (10 minuti)
CHILL_LEVEL_SECONDS = 600

# Modelli Whisper: id, etichetta (con peso download), VRAM ~necessaria su GPU (GB, float16)
WHISPER_MODELS = [
    ("tiny", "tiny ~75 MB", 1),
    ("base", "base ~145 MB", 1),
    ("small", "small ~480 MB", 2),
    ("medium", "medium ~1.5 GB", 5),
    ("large-v3", "large-v3 ~3 GB", 6),
]
MODEL_LABELS = [lbl for _id, lbl, _v in WHISPER_MODELS]
MODEL_VRAM = {mid: vram for mid, _lbl, vram in WHISPER_MODELS}


def _model_label(model_id: str) -> str:
    for mid, lbl, _v in WHISPER_MODELS:
        if mid == model_id:
            return lbl
    return MODEL_LABELS[1]  # default: base


def _model_id(label: str) -> str:
    return label.split(" ")[0]


# Modalita' di rilevamento highlight: (id salvato, etichetta nel menu)
HIGHLIGHT_MODES = [
    ("loudness", "Per rumore (loudness)"),
    ("talk", "Per parlato (talk)"),
]
MODE_LABELS = [lbl for _id, lbl in HIGHLIGHT_MODES]


def _mode_label(mode_id: str) -> str:
    for mid, lbl in HIGHLIGHT_MODES:
        if mid == mode_id:
            return lbl
    return MODE_LABELS[0]  # default: loudness


def _mode_id(label: str) -> str:
    for mid, lbl in HIGHLIGHT_MODES:
        if lbl == label:
            return mid
    return "loudness"


# Modalita' di tracking del crop verticale: (id salvato, etichetta nel menu)
TRACKING_MODES = [
    ("opencv", "OpenCV (volti)"),
    ("vtuber_right", "YOUTUBER FACE destra"),
    ("vtuber_left", "YOUTUBER FACE sinistra"),
    ("longplay", "Longplay (volti + azione)"),
]
TRACK_LABELS = [lbl for _id, lbl in TRACKING_MODES]


def _track_label(mode_id: str) -> str:
    for mid, lbl in TRACKING_MODES:
        if mid == mode_id:
            return lbl
    return TRACK_LABELS[0]


def _track_id(label: str) -> str:
    for mid, lbl in TRACKING_MODES:
        if lbl == label:
            return mid
    return "opencv"


def _recommended_model(vram_gb: float) -> str:
    """Il modello più grande che sta comodo nella VRAM (con margine)."""
    best = WHISPER_MODELS[0][0]
    for mid, _lbl, need in WHISPER_MODELS:
        if need <= vram_gb * 0.8:
            best = mid
    return best


# Font sottotitoli disponibili: (nome mostrato, file in fonts/)
SUBTITLE_FONTS = [
    ("PT Sans", "ptsans.ttf"),
    ("Anton", "anton.ttf"),
    ("Bebas Neue", "bebas.ttf"),
    ("Poppins", "poppins.ttf"),
    ("Bangers", "bangers.ttf"),
]
FONT_LABELS = [n for n, _f in SUBTITLE_FONTS]


def _font_label(file: str) -> str:
    return next((n for n, f in SUBTITLE_FONTS if f == file), FONT_LABELS[0])


def _font_file(label: str) -> str:
    return next((f for n, f in SUBTITLE_FONTS if n == label), "ptsans.ttf")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = load_settings()
        self._theme = self.settings.get("theme", "light")
        apply_palette(PALETTES.get(self._theme, LIGHT))
        self._asst_name = self.settings.get("assistant_name", "CRI il criceto")
        self._lang = self.settings.get("language", "it")
        self.video_path = None
        self._busy = False
        self._detection = None  # ultimo rilevamento (per l'anteprima): vedi _on_detected
        self._update_info = None  # info ultima release piu' nuova (badge su Versioni)
        self._cancel_event = threading.Event()
        from clipper import deps
        self.gpu = deps.gpu_info()  # {"name","total_mb"} oppure None
        from clipper.music import MusicPlayer, SoundPlayer
        self.music = MusicPlayer()
        self.sounds = SoundPlayer()
        self._music_muted = False
        self._spectrum = None          # matrice [frame][bande] del brano
        self._spectrum_fps = 15
        self._bar_levels = [0.0] * 28  # livelli barre (smoothing)
        self._wave_phase = 0.0         # fase dell'onda (velocita' variabile)

        root.title("DOPAMINIC")
        root.geometry("1140x900")  # largo perche' la chat e' aperta di default
        root.minsize(740, 800)
        root.configure(bg=BG)

        self._init_style()
        self._build_vars()
        self._build_widgets()
        self._set_icon()
        # I widget sono costruiti con testi italiani: se la lingua e' EN, traduci ora.
        if self._lang == "en":
            self._lang = "it"
            self._set_language("en")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Controllo aggiornamenti (GitHub Releases), in background e non bloccante.
        if self.settings.get("update_check", True):
            threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _set_icon(self):
        """Icona dell'app dal file sleep.png (se presente)."""
        from clipper import PROJECT_ROOT
        p = PROJECT_ROOT / "sleep.png"
        if not p.exists():
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(p).convert("RGBA")
            img.thumbnail((64, 64))
            self._app_icon = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, self._app_icon)
        except Exception:
            pass

    def _on_close(self):
        # Salva il livello di chill e ferma la musica prima di chiudere
        try:
            total = self._chill_base + (time.time() - self._session_start)
            self.settings["chill_seconds"] = total
            save_settings(self.settings)
        except Exception:
            pass
        try:
            self.music.stop()
        except Exception:
            pass
        self.root.destroy()

    # ----------------------------------------------------------- aggiornamenti
    def _check_updates_worker(self):
        """Controlla su GitHub se c'e' una release piu' nuova (thread in background)."""
        try:
            from clipper.updater import check_for_update
            info = check_for_update()
        except Exception:
            info = None
        if info:
            self.root.after(0, self._on_update_available, info)

    def _on_update_available(self, info):
        # Niente popup: segnalo con un pallino sul pulsante Versioni.
        self._update_info = info
        try:
            self._versions_btn.config(
                text=self._L("Versioni  *", "Versions  *"), bg=ACCENT, fg="#ffffff")
        except Exception:
            pass

    def _open_versions(self):
        from clipper.versions import VersionsWindow
        colors = {"BG": BG, "CARD": CARD, "FG": FG, "MUTED": MUTED, "ACCENT": ACCENT,
                  "INPUT_BG": INPUT_BG, "SUCCESS_HOVER": SUCCESS_HOVER}
        VersionsWindow(self.root, colors=colors, lang=self._lang,
                       current_version=APP_VERSION, on_install=self._install_version)

    def _install_version(self, url, ver):
        if url:
            self._start_update_download(url, ver)
        else:
            import webbrowser
            webbrowser.open(f"https://github.com/AlessandroBonomo28/DOPAMINIC/releases")

    def _start_update_download(self, url, ver):
        self.log(self._L(f"[update] Scarico DOPAMINIC {ver}...",
                         f"[update] Downloading DOPAMINIC {ver}..."))

        def worker():
            try:
                from clipper.updater import download, download_path
                dest = download_path(ver)
                download(url, dest, progress=lambda f: self.root.after(
                    0, self.log_progress, f"[update] {int(f * 100)}%  scaricato"))
                self.root.after(0, self._launch_update, dest)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, self.log, f"[update] Errore: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _launch_update(self, path):
        self.log(self._L("[update] Avvio l'installer, l'app si chiude.",
                         "[update] Launching the installer, the app will close."))
        try:
            from clipper.updater import launch_installer
            launch_installer(path)
        except Exception as exc:  # noqa: BLE001
            self.log(f"[update] Errore avvio installer: {exc}")
            return
        self.root.after(800, self._on_close)

    # --------------------------------------------------------------- styling
    def _init_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        # Combobox: campo bianco, sfondo grigio, freccia nera
        style.configure(
            "Dark.TCombobox", fieldbackground="white", background=CARD,
            foreground="black", arrowcolor="black", bordercolor=XP_SHADOW,
            lightcolor="white", darkcolor=XP_SHADOW, padding=3, relief="raised",
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", "white")],
            foreground=[("readonly", "black")],
            selectbackground=[("readonly", "white")],
            selectforeground=[("readonly", "black")],
        )
        self.root.option_add("*TCombobox*Listbox.background", "white")
        self.root.option_add("*TCombobox*Listbox.foreground", "black")
        self.root.option_add("*TCombobox*Listbox.selectBackground", XP_BLUE)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.root.option_add("*TCombobox*Listbox.font", "Tahoma 8")
        # Progressbar: blocchi blu su solco bianco (stile XP)
        style.configure(
            "Accent.Horizontal.TProgressbar", background=XP_BLUE,
            troughcolor="white", bordercolor=XP_SHADOW,
            lightcolor=XP_BLUE, darkcolor=XP_BLUE,
        )
        # Scrollbar grigia
        style.configure("TScrollbar", background=CARD, troughcolor="#dfdfdf",
                        bordercolor=XP_SHADOW, arrowcolor="black")
        # Tab (Notebook) stile cartelline grigie
        style.configure("Dark.TNotebook", background=BG, borderwidth=1)
        style.configure(
            "Dark.TNotebook.Tab", background="#d4d0c8", foreground="black",
            padding=(14, 4), font=("Tahoma", 8, "bold"), borderwidth=1,
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", CARD)],
            foreground=[("selected", "black")],
        )

    # ----------------------------------------------------------------- vars
    def _build_vars(self):
        s = self.settings
        self.video_path_var = tk.StringVar(value="Nessun file selezionato")
        self.clips_var = tk.StringVar(value=str(s["n_clips"]))
        self.duration_var = tk.StringVar(value=str(s["clip_duration"]))
        self.highlight_mode_var = tk.StringVar(value=_mode_label(s.get("highlight_mode", "loudness")))
        # Tracking: spunta + modalita' (migrazione dal vecchio opencv_face_tracking)
        self.tracking_enabled_var = tk.BooleanVar(
            value=s.get("tracking_enabled", s.get("opencv_face_tracking", False)))
        self.tracking_mode_var = tk.StringVar(value=_track_label(s.get("tracking_mode", "opencv")))
        self.watermark_var = tk.BooleanVar(value=s["watermark"])
        self.watermark_text_var = tk.StringVar(value=s["watermark_text"])
        self.subtitles_var = tk.BooleanVar(value=s["subtitles_enabled"])
        self.subtitle_color_var = tk.StringVar(value=s["subtitles_color"])
        self.whisper_language_var = tk.StringVar(value=s["whisper_language"])
        self.whisper_model_var = tk.StringVar(value=_model_label(s["whisper_model"]))
        self.gpu_var = tk.BooleanVar(value=s.get("whisper_device") == "cuda")
        self.font_var = tk.StringVar(value=_font_label(s.get("subtitle_font", "ptsans.ttf")))
        self.fontsize_var = tk.IntVar(value=int(s.get("subtitle_fontsize", 80)))
        self.stroke_var = tk.IntVar(value=int(s.get("subtitle_stroke", 6)))

    # ----------------------------------------------------------- widget helpers
    def _card(self, title: str) -> tk.Frame:
        # Group box stile Win95/XP: bordo "groove" con titolo.
        # Il titolo e' un nostro Label (labelwidget) e non il titolo nativo del
        # LabelFrame: su Windows quest'ultimo ignora 'fg' e resterebbe NERO anche
        # in tema scuro. Con un Label il colore (ACCENT) e' rispettato e il
        # retheme/traduzione continuano a funzionare (sono Label come gli altri).
        lf = tk.LabelFrame(
            self.content, bg=CARD, fg=ACCENT,
            relief="groove", bd=2, padx=10, pady=8,
        )
        lf.configure(labelwidget=tk.Label(
            lf, text=" " + title + " ", bg=CARD, fg=ACCENT, font=F_SECTION))
        lf.pack(fill="x", pady=(0, 10), padx=2)
        return lf

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg=CARD, fg=FG, font=F_LABEL, anchor="w")

    def _entry(self, parent, var, **kw):
        return tk.Entry(
            parent, textvariable=var, bg=INPUT_BG, fg=FG, insertbackground=FG,
            relief="sunken", bd=2, font=F_LABEL, **kw
        )

    def _check(self, parent, text, var, command=None):
        # selectcolor = interno del riquadro della spunta. Lo leghiamo a INPUT_BG
        # (bianco in chiaro, scuro in dark): cosi' il segno di spunta, disegnato
        # nel colore del testo, resta sempre leggibile (prima era fisso "white",
        # quindi in dark un tick chiaro su bianco risultava invisibile).
        return tk.Checkbutton(
            parent, text=text, variable=var, command=command, bg=CARD, fg=FG,
            selectcolor=INPUT_BG, activebackground=CARD, activeforeground=FG,
            font=F_LABEL, anchor="w", bd=0, highlightthickness=0,
        )

    def _link(self, parent, text, url):
        import webbrowser
        lbl = tk.Label(parent, text=text, bg=CARD, fg=ACCENT,
                       font=(F_LABEL[0], F_LABEL[1], "underline"), cursor="hand2", anchor="w")
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
        return lbl

    def _combo(self, parent, var, values, width=12):
        return ttk.Combobox(
            parent, textvariable=var, values=values, state="readonly",
            style="Dark.TCombobox", font=F_LABEL, width=width,
        )

    def _btn(self, parent, text, command, primary=False, click_sound=True):
        # Pulsante grigio 3D raised (classico). Si "abbassa" da solo al click.
        def wrapped():
            if click_sound:
                self._play_sound("click")
            command()
        btn = tk.Button(
            parent, text=text, command=wrapped, bg=CARD, fg=FG,
            activebackground=SUCCESS_HOVER, activeforeground=FG,
            relief="raised", bd=3, font=F_BTN if primary else F_LABEL,
            padx=10, pady=(6 if primary else 2),
        )
        return btn

    # -------------------------------------------------------------- widgets
    def _build_widgets(self):
        # Titlebar stile Windows XP (barra blu, testo bianco)
        header = tk.Frame(self.root, bg=XP_BLUE)
        header.pack(fill="x")
        tk.Label(header, text="DOPAMINIC", bg=XP_BLUE, fg="white",
                 font=F_TITLE).pack(side="left", padx=8, pady=5)
        self._versions_btn = self._btn(header, "Versioni", self._open_versions)
        self._versions_btn.pack(side="left", padx=(0, 8), pady=4)
        self._asst_toggle_btn = self._btn(header, f"{self._asst_name} :)", self._toggle_assistant)
        self._asst_toggle_btn.pack(side="right", padx=6, pady=4)
        self._mute_btn = self._btn(header, "Musica: ON", self._toggle_mute)
        self._mute_btn.pack(side="right", padx=(0, 4), pady=4)
        self._theme_btn = self._btn(
            header, "Tema: Scuro" if self._theme == "light" else "Tema: Chiaro",
            self._toggle_theme)
        self._theme_btn.pack(side="right", padx=(0, 4), pady=4)
        self._lang_btn = self._btn(
            header, "Lingua: IT" if self._lang == "it" else "Language: EN",
            self._toggle_language)
        self._lang_btn.pack(side="right", padx=(0, 4), pady=4)
        # Sottotitolo nella barra grigia
        sub = tk.Frame(self.root, bg=BG)
        sub.pack(fill="x")
        tk.Label(sub, text="Da un video lungo a piu' short dopaminici verticali. Tutto in locale.",
                 bg=BG, fg=MUTED, font=F_SUB, anchor="w").pack(side="left", padx=10, pady=(4, 0))

        # Corpo: tab a sinistra + pannello assistente a destra (nascosto di default)
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        self.assistant_visible = False
        self._assistant_greeted = False
        self.assistant_panel = self._build_assistant_panel(body)

        # Tab: Genera / YouTube
        notebook = ttk.Notebook(body, style="Dark.TNotebook")
        self._notebook = notebook
        notebook.pack(side="left", fill="both", expand=True, padx=16, pady=(4, 12))
        gen_tab = tk.Frame(notebook, bg=BG)
        yt_tab = tk.Frame(notebook, bg=BG)
        settings_tab = tk.Frame(notebook, bg=BG)
        notebook.add(gen_tab, text="  Genera  ")
        notebook.add(yt_tab, text="  YouTube  ")
        notebook.add(settings_tab, text="  Impostazioni  ")
        notebook.bind("<<NotebookTabChanged>>", lambda e: self._play_sound("tab"))

        # Contenuto tab "Genera"
        self.content = tk.Frame(gen_tab, bg=BG)
        self.content.pack(fill="both", expand=True, padx=12, pady=8)

        # --- Sorgente ---
        c = self._card("SORGENTE")
        c.columnconfigure(0, weight=1)
        path_box = tk.Frame(c, bg=INPUT_BG)
        path_box.grid(row=0, column=0, sticky="we", padx=(0, 10))
        self.path_label = tk.Label(
            path_box, textvariable=self.video_path_var, bg=INPUT_BG, fg=MUTED,
            font=F_LABEL, anchor="w", padx=10, pady=8,
        )
        self.path_label.pack(fill="x")
        self._btn(c, "📁  Sfoglia", self.select_video).grid(row=0, column=1)

        # --- Output ---
        c = self._card("OUTPUT")
        c.columnconfigure(1, weight=1)
        c.columnconfigure(3, weight=1)
        self._label(c, "Numero di short").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self._entry(c, self.clips_var, width=6).grid(row=0, column=1, sticky="w", pady=4)
        self._label(c, "Durata (s)").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        self._entry(c, self.duration_var, width=6).grid(row=0, column=3, sticky="w", pady=4)
        # Modalita' di rilevamento highlight
        self._label(c, "Rilevamento highlight").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        self._combo(c, self.highlight_mode_var, MODE_LABELS, width=22).grid(
            row=1, column=1, columnspan=3, sticky="w", pady=(10, 0))
        tk.Label(
            c, text="loudness = momenti più rumorosi (default).  talk = i monologhi più\n"
                    "lunghi, trascrivendo il video (ottimo per i longplay in cui parli a tratti).",
            bg=CARD, fg=MUTED, font=("Tahoma", 9), anchor="w", justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(2, 0))
        # Tracking: spunta per attivarlo + menu della modalita'
        self._check(
            c, "Tracking", self.tracking_enabled_var, command=self._on_tracking_change,
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.track_combo = self._combo(c, self.tracking_mode_var, TRACK_LABELS, width=18)
        self.track_combo.grid(row=3, column=1, columnspan=3, sticky="w", pady=(10, 0))
        self.track_combo.bind("<<ComboboxSelected>>", lambda e: self._on_tracking_change())
        tk.Label(
            c, text="OpenCV = segue i volti.  YOUTUBER FACE = alterna ogni 5s centro/lato dove sta\n"
                    "l'avatar.  Longplay = inquadra chi parla nelle cutscene e segue l'azione nel\n"
                    "gameplay.  Tracking spento = crop centrale.",
            bg=CARD, fg=MUTED, font=("Tahoma", 9), anchor="w", justify="left",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(2, 0))

        # --- Stile ---
        c = self._card("STILE")
        c.columnconfigure(1, weight=1)
        # Watermark
        self._check(c, "Watermark", self.watermark_var).grid(row=0, column=0, sticky="w", pady=4)
        self._entry(c, self.watermark_text_var).grid(
            row=0, column=1, columnspan=2, sticky="we", padx=(10, 0), pady=4
        )
        # Sottotitoli
        self._check(
            c, "Sottotitoli (Whisper locale)", self.subtitles_var,
            command=lambda: self._ensure_dep("whisper", self.subtitles_var),
        ).grid(row=1, column=0, sticky="w", pady=4)
        color_box = tk.Frame(c, bg=CARD)
        color_box.grid(row=1, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=4)
        self.color_swatch = tk.Label(
            color_box, bg=self.subtitle_color_var.get(), width=4, relief="flat",
            highlightthickness=1, highlightbackground="#3a3a4d",
        )
        self.color_swatch.pack(side="left", ipady=8)
        self._btn(color_box, "Colore", self.choose_color).pack(side="left", padx=8)
        self._btn(color_box, "Stile...", self._open_subtitle_editor).pack(side="left")
        # Lingua + modello (con peso del download)
        self._label(c, "Lingua").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self._combo(c, self.whisper_language_var,
                    ["auto", "it", "en", "es", "fr", "de", "pt"]).grid(
            row=2, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self._label(c, "Modello Whisper").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.model_combo = self._combo(c, self.whisper_model_var, MODEL_LABELS, width=18)
        self.model_combo.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        self.model_combo.bind("<<ComboboxSelected>>", lambda e: self._update_gpu_hint())

        # GPU
        self._check(
            c, "Usa GPU (NVIDIA)", self.gpu_var, command=self._on_gpu_toggle,
        ).grid(row=4, column=0, sticky="w", pady=(10, 0))
        tk.Label(
            c, text="Molto più veloce sui modelli grandi. Richiede una GPU NVIDIA;\n"
                    "al primo uso scarica le librerie CUDA (~1 GB). Altrimenti usa la CPU.",
            bg=CARD, fg=MUTED, font=("Tahoma", 9), anchor="w", justify="left",
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(2, 0))
        # Riga dinamica: GPU rilevata + modello consigliato / avviso VRAM
        self.gpu_info_label = tk.Label(
            c, text="", bg=CARD, fg=MUTED, font=("Tahoma", 9, "bold"),
            anchor="w", justify="left",
        )
        self.gpu_info_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self._update_gpu_hint()

        # --- Pulsante Genera ---
        gen_row = tk.Frame(self.content, bg=BG)
        gen_row.pack(fill="x", pady=(4, 4))
        self.generate_btn = self._btn(
            gen_row, "GENERA SHORT", self.start_generation, primary=True
        )
        self.generate_btn.pack(side="left", fill="x", expand=True)
        self.preview_btn = self._btn(gen_row, "Anteprima", self._open_preview)
        self.preview_btn.pack(side="left", padx=(6, 0))
        self.preview_btn.config(state="disabled")  # si abilita dopo il rilevamento
        self.stop_btn = self._btn(gen_row, "STOP", self._stop_generation, primary=True)
        self.stop_btn.pack(side="left", padx=(6, 0))
        self.stop_btn.config(state="disabled")  # attivo solo durante la generazione
        # Shortcut alla cartella output
        self._btn(self.content, "Apri cartella output", self.open_output_folder).pack(
            fill="x", pady=(0, 8)
        )

        # Progress
        self.progress = ttk.Progressbar(
            self.content, mode="indeterminate", style="Accent.Horizontal.TProgressbar"
        )
        self.progress.pack(fill="x", pady=(0, 8))

        # --- Log con visualizzatore (Canvas: animazione di sfondo + testo sopra) ---
        log_frame = tk.Frame(self.content, bg=VIZ_BG, highlightthickness=2,
                             highlightbackground="#808080")
        log_frame.pack(fill="both", expand=True)
        self.log_canvas = tk.Canvas(log_frame, bg=VIZ_BG, highlightthickness=0)
        self.log_canvas.pack(fill="both", expand=True)
        self.log_canvas.bind("<Configure>", lambda e: self._redraw_log_text())
        self._log_lines = []
        self._viz_t = 0
        self.log("Pronto. Seleziona un video e premi GENERA.")
        self._viz_step()

        # Tab YouTube
        self._build_youtube_tab(yt_tab)
        self._build_settings_tab(settings_tab)

        # Chat aperta di default (mostra il pannello + saluto, senza ridimensionare)
        self.assistant_panel.pack(side="right", fill="y", padx=(0, 12), pady=(4, 12))
        self.assistant_visible = True
        self._chat_append(self._asst_name, self.assistant.greeting(), "bot")
        self._assistant_greeted = True
        self._reset_sleep_timer()
        self._apply_music()  # avvia la musica se abilitata nelle impostazioni

    # --------------------------------------------------------------- helpers
    def open_output_folder(self):
        from clipper import OUTPUT_DIR, ensure_dirs
        ensure_dirs()
        try:
            os.startfile(str(OUTPUT_DIR))  # Windows
        except AttributeError:
            import subprocess, sys
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(OUTPUT_DIR)])

    # ============================================================ ASSISTENTE
    def _build_assistant_panel(self, parent) -> tk.Frame:
        from clipper.assistant import Assistant
        self.assistant = Assistant(self._lang)
        self.chat_input_var = tk.StringVar()

        panel = tk.Frame(parent, bg=CARD, width=320, highlightthickness=1,
                         highlightbackground="#2e2e40")
        panel.pack_propagate(False)  # mantiene la larghezza fissa

        head = tk.Frame(panel, bg=CARD)
        head.pack(fill="x", padx=12, pady=(10, 2))
        self._asst_header_lbl = tk.Label(head, text=self._asst_name, bg=CARD, fg=ACCENT,
                                         font=F_SECTION, anchor="w")
        self._asst_header_lbl.pack(side="left")

        # Livello di chill: cresce col tempo passato nella finestra (~1/ora)
        chill = tk.Frame(panel, bg=CARD)
        chill.pack(fill="x", padx=12, pady=(0, 4))
        self._chill_label = tk.Label(chill, text="Livello di chill: 0", bg=CARD, fg=MUTED,
                                     font=("Tahoma", 7))
        self._chill_label.pack(side="left")
        self._chill_bar = ttk.Progressbar(chill, mode="determinate", maximum=100,
                                          style="Accent.Horizontal.TProgressbar", length=110)
        self._chill_bar.pack(side="right")
        self._chill_base = float(self.settings.get("chill_seconds", 0) or 0)
        self._session_start = time.time()
        self._update_chill()

        # Avatar in cima alla chat (gif idle, va a dormire dopo inattivita')
        self._setup_avatar(panel)

        self.chat_box = tk.Text(panel, bg=LOG_BG, fg=FG, font=("Tahoma", 9),
                                wrap="word", state="disabled", padx=10, pady=8,
                                relief="flat", highlightthickness=0)
        self.chat_box.pack(fill="both", expand=True, padx=10)
        self.chat_box.tag_configure("me", foreground=ACCENT, font=("Tahoma", 9, "bold"))
        self.chat_box.tag_configure("bot", foreground="#006400", font=("Tahoma", 9, "bold"))

        inrow = tk.Frame(panel, bg=CARD)
        inrow.pack(fill="x", padx=10, pady=10)
        entry = self._entry(inrow, self.chat_input_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self._chat_send())
        self._btn(inrow, "Invia", self._chat_send, click_sound=False).pack(side="left", padx=(6, 0))
        return panel

    # --- Avatar dell'assistente: idle -> (inattivita') -> gotosleep -> sleep ---
    def _setup_avatar(self, panel):
        self._avatar_label = tk.Label(panel, bg=CARD)
        self._avatar_label.pack(pady=(2, 6))
        self._anim_token = 0
        self._sleep_after = None
        self._sleeping = False
        self._reload_avatar_media()
        self._avatar_idle()

    def _resolve_asset(self, name):
        from clipper import PROJECT_ROOT
        if not name:
            return None
        p = name if os.path.isabs(name) else str(PROJECT_ROOT / name)
        return p if os.path.exists(p) else None

    def _load_frames(self, name, maxw=240):
        """Carica frame+durate da gif/png. Ritorna (frames, delays) o None."""
        p = self._resolve_asset(name)
        if not p:
            return None
        try:
            from PIL import Image, ImageTk, ImageSequence
            img = Image.open(p)
            frames, delays = [], []
            for fr in ImageSequence.Iterator(img):
                f = fr.convert("RGBA")
                if f.width > maxw:
                    r = maxw / f.width
                    f = f.resize((maxw, max(1, int(f.height * r))))
                frames.append(ImageTk.PhotoImage(f))
                delays.append(fr.info.get("duration", 90) or 90)
            return (frames, delays) if frames else None
        except Exception:
            return None

    def _reload_avatar_media(self):
        s = self.settings
        self._idle_media = self._load_frames(s.get("idle_gif", "assistant.gif"))
        self._sleep_anim = self._load_frames(s.get("gotosleep_gif", "gotosleep.gif"))
        self._sleep_img = self._load_frames(s.get("sleep_png", "sleep.png"))

    def _avatar_animate(self, media, loop, on_end=None):
        self._anim_token += 1
        token = self._anim_token
        if not media or not self._avatar_label.winfo_exists():
            if on_end:
                on_end()
            return
        frames, delays = media

        def step(i):
            if token != self._anim_token or not self._avatar_label.winfo_exists():
                return
            self._avatar_label.config(image=frames[i])
            nxt = i + 1
            if nxt < len(frames):
                self.root.after(delays[i], step, nxt)
            elif loop:
                self.root.after(delays[i], step, 0)
            elif on_end:
                self.root.after(delays[i], on_end)

        step(0)

    def _avatar_idle(self):
        if self._idle_media:
            self._avatar_animate(self._idle_media, loop=True)

    def _avatar_go_sleep(self):
        self._sleep_after = None
        self._sleeping = True
        # messaggio simpatico di buonanotte in chat
        try:
            self._chat_append(self._asst_name, self.assistant.sleep_message(), "bot")
        except Exception:
            pass
        # va a dormire in silenzio (nessun suono)
        if self._sleep_anim:
            self._avatar_animate(self._sleep_anim, loop=False, on_end=self._avatar_sleeping)
        else:
            self._avatar_sleeping()

    def _avatar_sleeping(self):
        self._anim_token += 1  # ferma eventuali animazioni in corso
        if self._sleep_img and self._avatar_label.winfo_exists():
            self._avatar_label.config(image=self._sleep_img[0][0])

    def _avatar_wake(self):
        if self._sleeping:
            self._play_sound("wake")
            self._sleeping = False
        self._avatar_idle()

    def _reset_sleep_timer(self):
        if self._sleep_after:
            try:
                self.root.after_cancel(self._sleep_after)
            except Exception:
                pass
            self._sleep_after = None
        try:
            t = int(self.settings.get("sleep_timeout", 10))
        except (TypeError, ValueError):
            t = 10
        if t > 0:
            self._sleep_after = self.root.after(t * 1000, self._avatar_go_sleep)

    def _update_chill(self):
        """Livello di chill in base al tempo totale nella finestra. Persistente.

        Sale di 1 ogni CHILL_LEVEL_SECONDS (10 min). La barra mostra quanto manca
        al prossimo livello.
        """
        if not self._chill_label.winfo_exists():
            return
        total = self._chill_base + (time.time() - self._session_start)
        level = int(total // CHILL_LEVEL_SECONDS)
        progress = (total % CHILL_LEVEL_SECONDS) / CHILL_LEVEL_SECONDS * 100
        self._chill_label.config(text=f"{self._L('Livello di chill', 'Chill level')}: {level}")
        self._chill_bar["value"] = progress
        # Persisti il totale (cosi' riaprendo riparti dal tuo livello)
        self.settings["chill_seconds"] = total
        try:
            save_settings(self.settings)
        except Exception:
            pass
        self.root.after(10000, self._update_chill)  # aggiorna ogni 10s

    def _toggle_assistant(self):
        if self.assistant_visible:
            self.assistant_panel.pack_forget()
            self.assistant_visible = False
        else:
            if self.root.winfo_width() < 1100:
                self.root.geometry(f"1140x{max(self.root.winfo_height(), 820)}")
            self.assistant_panel.pack(side="right", fill="y", padx=(0, 12), pady=(4, 12))
            self.assistant_visible = True
            if not self._assistant_greeted:
                self._chat_append(self._asst_name, self.assistant.greeting(), "bot")
                self._assistant_greeted = True

    def _chat_append(self, who: str, text: str, tag: str = "me"):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{who}\n", tag)
        self.chat_box.insert("end", f"{text}\n\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def _chat_send(self):
        msg = self.chat_input_var.get().strip()
        if not msg:
            return
        self._avatar_wake()       # attivita': sveglia il criceto
        self._reset_sleep_timer()
        self._play_sound("send")
        self._chat_append("Tu", msg, "me")
        self.chat_input_var.set("")

        def _reply():
            self._chat_append(self._asst_name, self.assistant.answer(msg), "bot")
            self._play_sound("reply")
        self.root.after(280, _reply)

    def _play_sound(self, kind):
        if not self.settings.get("sounds_enabled", True):
            return
        from clipper.music import default_sound
        override = {"send": self.settings.get("sound_send"),
                    "reply": self.settings.get("sound_reply")}.get(kind)
        f = override or default_sound(kind)
        self.sounds.play(f, volume=0.6)

    def log(self, message: str):
        self._progress_active = False  # una riga normale chiude la barra in corso
        self._log_lines.append(message)
        if len(self._log_lines) > 400:
            self._log_lines = self._log_lines[-400:]
        self._redraw_log_text()

    def log_progress(self, text: str):
        """Aggiorna in place l'ultima riga del log (barra di avanzamento)."""
        if getattr(self, "_progress_active", False) and self._log_lines:
            self._log_lines[-1] = text
        else:
            self._log_lines.append(text)
            self._progress_active = True
            if len(self._log_lines) > 400:
                self._log_lines = self._log_lines[-400:]
        self._redraw_log_text()

    def _redraw_log_text(self):
        c = self.log_canvas
        if not c.winfo_exists():
            return
        c.delete("logtxt")
        h = c.winfo_height() or 200
        lh = 15
        count = max(1, (h - 12) // lh)
        y = 8
        for line in self._log_lines[-count:]:
            # ombra nera + testo bianco -> leggibile sopra qualunque animazione
            c.create_text(9, y + 1, anchor="nw", text=line, fill="#000000", font=F_MONO, tags="logtxt")
            c.create_text(8, y, anchor="nw", text=line, fill="#ffffff", font=F_MONO, tags="logtxt")
            y += lh
        c.tag_raise("logtxt")

    @staticmethod
    def _hsv(h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    def _viz_step(self):
        """Visualizzatore stile Windows Media Player: barre + onda animate dietro al log."""
        c = self.log_canvas
        if not c.winfo_exists():
            return
        c.delete("viz")
        if self.settings.get("viz_enabled", True):
            w = c.winfo_width() or 400
            h = c.winfo_height() or 200
            self._viz_t += 1
            t = self._viz_t
            nbars = 28

            # Target delle barre: reattivo alla musica se disponibile, altrimenti onda finta
            pos = self.music.position_ms() if (
                self.settings.get("music_enabled") and not self._music_muted) else -1
            spec = self._spectrum
            if spec is not None and pos >= 0:
                idx = int(pos / 1000.0 * self._spectrum_fps) % len(spec)
                row = spec[idx]
                targets = [float(row[i]) if i < len(row) else 0.0 for i in range(nbars)]
            else:
                targets = [(math.sin(t * 0.15 + i * 0.5) * 0.5 + 0.5)
                           * (math.sin(t * 0.07 + i * 0.3) * 0.4 + 0.6) for i in range(nbars)]

            # Sensibilita' moderata (barre piu' basse)
            targets = [min(1.0, (v ** 0.7) * 1.25) for v in targets]
            for i in range(nbars):
                self._bar_levels[i] += (targets[i] - self._bar_levels[i]) * 0.45

            bw = w / nbars
            for i in range(nbars):
                bh = self._bar_levels[i] * h * 0.72
                col = self._hsv(i / nbars + t * 0.004, 0.85, 0.55)
                c.create_rectangle(i * bw + 1, h - bh, (i + 1) * bw - 1, h,
                                   fill=col, outline="", tags="viz")

            # Onda viaggiante che ALTERNA forma (sine/quadra/sega/triangolo),
            # con velocita' variabile e ampiezza modulata dalla musica.
            energy = sum(self._bar_levels) / nbars
            shape = ("sine", "square", "saw", "triangle")[(t // 150) % 4]
            self._wave_phase += 0.10 + 0.10 * (0.5 + 0.5 * math.sin(t * 0.012))
            amp = h * 0.12 * (0.35 + 1.2 * energy) * (0.7 + 0.3 * math.sin(t * 0.03))
            sf = 0.045
            tau = 2 * math.pi

            def _wv(u):
                if shape == "sine":
                    return math.sin(u)
                if shape == "square":
                    return 1.0 if math.sin(u) >= 0 else -1.0
                if shape == "saw":
                    return ((u / tau) % 1.0) * 2 - 1
                fr = (u / tau) % 1.0  # triangle
                return 2 * abs(2 * fr - 1) - 1

            pts = []
            for x in range(0, int(w) + 6, 6):
                yy = h * 0.5 + _wv(x * sf + self._wave_phase) * amp
                pts += [x, max(2, min(h - 2, yy))]
            if len(pts) >= 4:
                c.create_line(*pts, fill=self._hsv(t * 0.01 + energy, 0.7, 0.7), width=2,
                              smooth=(shape in ("sine", "triangle")), tags="viz")
            c.tag_lower("viz")
            c.tag_raise("logtxt")
        self.root.after(80, self._viz_step)

    def _ensure_dep(self, key: str, var: tk.BooleanVar):
        """Se l'utente attiva una funzione opzionale, propone di installarne la dipendenza."""
        from clipper import deps

        if not var.get() or deps.is_installed(key):
            return
        label = deps.OPTIONAL[key]["label"]
        if not messagebox.askyesno(
            "Dipendenza richiesta",
            f"{label} non è installato.\n\nVuoi scaricarlo e installarlo ora?",
        ):
            var.set(False)
            return

        self._set_busy(True)
        self.log(f"[deps] Installazione di {label}...")

        def worker():
            ok = deps.install(key, log=lambda m: self.root.after(0, self.log, m))
            self.root.after(0, self._after_install, key, var, ok)

        threading.Thread(target=worker, daemon=True).start()

    def _after_install(self, key, var, ok):
        self._set_busy(False)
        if ok:
            messagebox.showinfo("Fatto", "Dipendenza installata correttamente.")
        else:
            var.set(False)
            messagebox.showerror("Installazione", "Installazione fallita. Controlla il log.")

    def _on_tracking_change(self):
        """OpenCV serve per le modalita' 'opencv' e 'longplay'; le YOUTUBER FACE no."""
        if self.tracking_enabled_var.get() and \
                _track_id(self.tracking_mode_var.get()) in ("opencv", "longplay"):
            self._ensure_dep("opencv", self.tracking_enabled_var)

    def _ensure_gpu(self):
        """Attivando la GPU: verifica la presenza di una NVIDIA e installa le librerie CUDA."""
        from clipper import deps

        if not self.gpu_var.get():
            return
        if not deps.has_nvidia_gpu():
            messagebox.showwarning(
                "GPU non disponibile",
                "Nessuna GPU NVIDIA rilevata su questo PC.\nVerrà usata la CPU.",
            )
            self.gpu_var.set(False)
            return
        if deps.gpu_libs_installed():
            return
        if not messagebox.askyesno(
            "Librerie GPU",
            "Per usare la GPU servono le librerie CUDA (~1 GB).\nVuoi scaricarle e installarle ora?",
        ):
            self.gpu_var.set(False)
            return

        self._set_busy(True)
        self.log("[deps] Installazione librerie GPU (CUDA)...")

        def worker():
            ok = deps.install_gpu(log=lambda m: self.root.after(0, self.log, m))
            self.root.after(0, self._after_install, "gpu", self.gpu_var, ok)

        threading.Thread(target=worker, daemon=True).start()

    def _on_gpu_toggle(self):
        self._ensure_gpu()
        self._update_gpu_hint()

    def _update_gpu_hint(self):
        """Aggiorna la riga con GPU rilevata, modello consigliato ed eventuale avviso VRAM."""
        if not self.gpu:
            self.gpu_info_label.config(
                text=self._L("Nessuna GPU NVIDIA rilevata, i sottotitoli useranno la CPU.",
                             "No NVIDIA GPU detected, subtitles will use the CPU."), fg=MUTED)
            return
        vram_gb = self.gpu["total_mb"] / 1024
        rec = _recommended_model(vram_gb)
        rec_lbl = self._L("consigliato", "recommended")
        base_txt = f"GPU: {self.gpu['name']} · {vram_gb:.0f} GB · {rec_lbl}: {rec}"
        if self.gpu_var.get():
            model = _model_id(self.whisper_model_var.get())
            need = MODEL_VRAM.get(model, 0)
            if need > vram_gb * 0.9:
                warn = self._L(
                    f"\n(!) Il modello '{model}' (~{need} GB) puo' eccedere la VRAM: "
                    "se non basta, passa automaticamente alla CPU.",
                    f"\n(!) The '{model}' model (~{need} GB) may exceed VRAM: "
                    "if not enough, it falls back to CPU automatically.")
                self.gpu_info_label.config(text=base_txt + warn, fg="#f59e0b")
                return
        self.gpu_info_label.config(text=base_txt, fg=MUTED)

    def choose_color(self):
        color = colorchooser.askcolor(title="Colore sottotitoli")
        if color[1]:
            hex_color = color[1].upper()
            self.subtitle_color_var.set(hex_color)
            self.color_swatch.config(bg=hex_color)

    def _open_subtitle_editor(self):
        """Editor stile sottotitoli con anteprima in tempo reale (Pillow)."""
        from clipper import FONTS_DIR
        from clipper.textrender import render_text
        from PIL import Image, ImageTk

        win = tk.Toplevel(self.root)
        win.title("Stile sottotitoli")
        win.configure(bg=BG)
        win.geometry("560x560")
        win.transient(self.root)

        def render_preview(*_):
            try:
                font_path = str(FONTS_DIR / _font_file(self.font_var.get()))
                size = max(10, int(self.fontsize_var.get()))
                stroke = max(0, int(self.stroke_var.get()))
                arr = render_text(
                    "Perché è così! àòù", font_path, size,
                    fill=self.subtitle_color_var.get(), stroke_color="#000000", stroke_width=stroke,
                )
                img = Image.fromarray(arr)
                bg = Image.new("RGBA", img.size, (35, 55, 85, 255))
                bg.alpha_composite(img)
                maxw = 500
                if bg.width > maxw:
                    r = maxw / bg.width
                    bg = bg.resize((maxw, max(1, int(bg.height * r))))
                self._preview_imgtk = ImageTk.PhotoImage(bg)
                preview.config(image=self._preview_imgtk, text="")
            except Exception as exc:  # noqa: BLE001
                preview.config(image="", text=f"Anteprima non disponibile: {exc}", fg=MUTED)

        pad = {"padx": 16, "pady": (8, 0)}
        tk.Label(win, text="Font", bg=BG, fg=FG, font=F_LABEL, anchor="w").pack(fill="x", **pad)
        fc = self._combo(win, self.font_var, FONT_LABELS, width=22)
        fc.pack(fill="x", padx=16)
        fc.bind("<<ComboboxSelected>>", render_preview)

        tk.Label(win, text="Dimensione", bg=BG, fg=FG, font=F_LABEL, anchor="w").pack(fill="x", **pad)
        tk.Scale(win, from_=40, to=160, orient="horizontal", variable=self.fontsize_var,
                 command=render_preview, bg=BG, fg=FG, troughcolor=CARD, highlightthickness=0,
                 activebackground=ACCENT, bd=0).pack(fill="x", padx=16)

        tk.Label(win, text="Spessore contorno", bg=BG, fg=FG, font=F_LABEL, anchor="w").pack(fill="x", **pad)
        tk.Scale(win, from_=0, to=20, orient="horizontal", variable=self.stroke_var,
                 command=render_preview, bg=BG, fg=FG, troughcolor=CARD, highlightthickness=0,
                 activebackground=ACCENT, bd=0).pack(fill="x", padx=16)

        def pick_color():
            self.choose_color()
            render_preview()
        self._btn(win, "Colore testo", pick_color).pack(anchor="w", padx=16, pady=10)

        tk.Label(win, text="Anteprima:", bg=BG, fg=MUTED, font=F_LABEL, anchor="w").pack(fill="x", padx=16)
        preview = tk.Label(win, bg="#23375a", bd=0)
        preview.pack(fill="x", padx=16, pady=(4, 10))

        self._btn(win, "Chiudi", win.destroy, primary=True).pack(fill="x", padx=16, pady=(0, 12))
        render_preview()

    def select_video(self):
        path = filedialog.askopenfilename(
            title="Seleziona video",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv")],
        )
        if not path:
            return
        try:
            with VideoFileClip(path) as clip:
                duration = clip.duration
        except Exception as exc:
            messagebox.showerror("Errore", f"Impossibile aprire il video:\n{exc}")
            return
        if duration < 30:
            messagebox.showwarning("Attenzione", "Video troppo corto (<30s) per essere spezzato.")
            return
        self.video_path = path
        self.video_path_var.set(path)
        self.path_label.config(fg=FG)
        # Nuovo video: il rilevamento precedente non vale piu'
        self._detection = None
        self.preview_btn.config(state="disabled")

    # ------------------------------------------------------------ generation
    def _collect_settings(self) -> dict:
        self.settings.update({
            "n_clips": int(self.clips_var.get()),
            "clip_duration": int(self.duration_var.get()),
            "highlight_mode": _mode_id(self.highlight_mode_var.get()),
            "tracking_enabled": self.tracking_enabled_var.get(),
            "tracking_mode": _track_id(self.tracking_mode_var.get()),
            "watermark": self.watermark_var.get(),
            "watermark_text": self.watermark_text_var.get(),
            "subtitles_enabled": self.subtitles_var.get(),
            "subtitles_color": self.subtitle_color_var.get(),
            "subtitle_font": _font_file(self.font_var.get()),
            "subtitle_fontsize": int(self.fontsize_var.get()),
            "subtitle_stroke": int(self.stroke_var.get()),
            "whisper_language": self.whisper_language_var.get(),
            "whisper_model": _model_id(self.whisper_model_var.get()),
            "whisper_device": "cuda" if self.gpu_var.get() else "cpu",
        })
        save_settings(self.settings)
        return self.settings

    def start_generation(self):
        if self._busy:
            return
        if not self.video_path:
            messagebox.showwarning("Attenzione", "Seleziona prima un video.")
            return
        try:
            n_clips = int(self.clips_var.get())
            duration = int(self.duration_var.get())
            if n_clips < 1 or duration < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Errore", "Numero di short e durata devono essere interi positivi.")
            return

        settings = self._collect_settings()
        self._cancel_event.clear()
        self._set_busy(True, phase="detect")
        threading.Thread(
            target=self._detect_thread,
            args=(self.video_path, n_clips, duration, settings), daemon=True,
        ).start()

    def _detect_thread(self, path, n_clips, duration, settings):
        try:
            det = detect_clips(
                path, n_clips, duration, settings,
                progress_cb=lambda m: self.root.after(0, self.log, m),
                bar_cb=lambda m: self.root.after(0, self.log_progress, m),
            )
            self.root.after(0, self._on_detected, path, det, settings, None)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, self._on_detected, path, None, settings, exc)

    def _on_detected(self, path, det, settings, error):
        self._set_busy(False)
        if error is not None:
            self.log(f"[ERRORE] {error}")
            messagebox.showerror("Errore", str(error))
            return
        clips = det.get("clips") if det else []
        if not clips:
            self._detection = None
            self.preview_btn.config(state="disabled")
            messagebox.showwarning(
                "Nessun highlight",
                "Nessun momento rilevato (video troppo corto o senza parlato?).")
            return
        self._detection = {
            "path": path, "clips": clips, "transcript": det.get("transcript"),
            "duration": det.get("duration"), "settings": settings,
        }
        self.preview_btn.config(state="normal")
        self.log(f"[+] {len(clips)} clip individuate. Apri l'Anteprima per rivederle e confermare.")
        self._open_preview()

    def _open_preview(self):
        if self._busy:
            return
        d = self._detection
        if not d:
            messagebox.showinfo("Anteprima",
                                "Prima premi GENERA SHORT per individuare i momenti.")
            return
        from clipper.preview import PreviewEditor
        colors = {"BG": BG, "CARD": CARD, "FG": FG, "MUTED": MUTED, "ACCENT": ACCENT,
                  "INPUT_BG": INPUT_BG, "SUCCESS_HOVER": SUCCESS_HOVER}
        PreviewEditor(self.root, d["path"], d["clips"], d["duration"],
                      on_confirm=self._confirm_render, colors=colors, title_font=F_SECTION,
                      default_dur=d["settings"].get("clip_duration", 15),
                      music_pause=self.music.stop, music_resume=self._resume_music_if_on,
                      lang=self._lang)

    def _resume_music_if_on(self):
        """Riprende la musica di sottofondo (usato quando l'anteprima la rilascia)."""
        if self.settings.get("music_enabled"):
            self._start_music()

    def _confirm_render(self, clips):
        d = self._detection
        if not d:
            return
        d["clips"] = clips  # tieni le clip ritoccate per eventuali riaperture
        self._cancel_event.clear()
        self._set_busy(True, phase="render")
        threading.Thread(
            target=self._render_thread,
            args=(d["path"], clips, d["settings"], d["transcript"]), daemon=True,
        ).start()

    def _stop_generation(self):
        if self._busy:
            self._cancel_event.set()
            self.stop_btn.config(state="disabled")
            self.log("[!] Interruzione richiesta: mi fermo dopo lo short in corso...")

    def _render_thread(self, path, clips, settings, transcript):
        try:
            outputs = render_clips(
                path, clips, settings, transcript,
                progress_cb=lambda m: self.root.after(0, self.log, m),
                should_cancel=self._cancel_event.is_set,
            )
            self.root.after(0, self._on_done, outputs, None)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, self._on_done, None, exc)

    def _on_done(self, outputs, error):
        cancelled = self._cancel_event.is_set()
        self._set_busy(False)
        if error is not None:
            self.log(f"[ERRORE] {error}")
            messagebox.showerror("Errore", str(error))
        elif cancelled:
            messagebox.showinfo("Interrotto", f"Generazione interrotta. Short prodotti: {len(outputs or [])}.")
        elif outputs:
            messagebox.showinfo("Fatto", f"Generati {len(outputs)} short in:\n{OUTPUT_DIR}")
        else:
            messagebox.showwarning("Nessun output", "Nessuno short generato (video troppo corto?).")

    def _set_busy(self, busy: bool, phase: str = "render"):
        self._busy = busy
        if busy:
            txt = "RILEVAMENTO..." if phase == "detect" else "GENERAZIONE IN CORSO..."
        else:
            txt = "GENERA SHORT"
        self.generate_btn.config(state="disabled" if busy else "normal", text=txt)
        self.stop_btn.config(state="normal" if busy else "disabled")
        # Anteprima: spenta mentre lavora; riaccesa a fine se c'e' un rilevamento valido
        if busy:
            self.preview_btn.config(state="disabled")
        else:
            self.preview_btn.config(
                state="normal" if getattr(self, "_detection", None) else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    # ============================================================ YOUTUBE TAB
    def _build_youtube_tab(self, parent):
        from clipper import youtube_uploader as yt
        self.yt = yt
        self.yt_plan = []        # [(path, datetime)]
        self.yt_outputs = []
        self.yt_schedule = yt.load_schedule()

        inner = tk.Frame(parent, bg=BG)
        inner.pack(fill="both", expand=True, padx=12, pady=8)
        self.content = inner  # i _card() seguenti vanno in questa tab

        # --- Account ---
        c = self._card("ACCOUNT YOUTUBE")
        c.columnconfigure(0, weight=1)
        self.yt_status = tk.Label(c, text="...", bg=CARD, fg=MUTED, font=F_LABEL, anchor="w")
        self.yt_status.grid(row=0, column=0, sticky="we")
        self._btn(c, "Configura accesso...", self._yt_configure).grid(row=0, column=1)
        tk.Label(
            c, text="Serve un file client_secret.json (Google Cloud Console, YouTube Data API v3,\n"
                    "credenziali OAuth tipo «Desktop»). I video vengono caricati come privati e\n"
                    "pubblicati in automatico all'orario dello slot.",
            bg=CARD, fg=MUTED, font=("Tahoma", 9), anchor="w", justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        tk.Label(
            c, text=self._L(
                "Leggi le info sul repo di DOPAMINIC per configurare il client_secret di YouTube:",
                "Read the DOPAMINIC repo info to set up the YouTube client_secret:"),
            bg=CARD, fg=MUTED, font=("Tahoma", 9), anchor="w", justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._link(c, "github.com/AlessandroBonomo28/DOPAMINIC",
                   "https://github.com/AlessandroBonomo28/DOPAMINIC").grid(
            row=3, column=0, columnspan=2, sticky="w")

        # --- Slot settimanali ---
        c = self._card("SLOT SETTIMANALI")
        c.columnconfigure(0, weight=1)
        self.yt_slots_label = tk.Label(c, text="", bg=CARD, fg=FG, font=F_LABEL, anchor="w")
        self.yt_slots_label.grid(row=0, column=0, columnspan=4, sticky="we")
        self.slot_day_var = tk.StringVar(value=yt.WEEKDAYS_IT[0])
        self.slot_time_var = tk.StringVar(value="18:00")
        self._btn(c, "Azzera", self._yt_clear_slots).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._combo(c, self.slot_day_var, yt.WEEKDAYS_IT, width=6).grid(
            row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self._entry(c, self.slot_time_var, width=8).grid(row=1, column=2, sticky="w", padx=8, pady=(8, 0))
        self._btn(c, "+ slot", self._yt_add_slot).grid(row=1, column=3, sticky="w", pady=(8, 0))

        # --- Output -> pianificazione ---
        c = self._card("VIDEO IN OUTPUT -> PIANIFICAZIONE")
        c.columnconfigure(0, weight=1)
        self.yt_count_label = tk.Label(c, text="", bg=CARD, fg=MUTED, font=F_LABEL, anchor="w")
        self.yt_count_label.grid(row=0, column=0, sticky="w")
        self._btn(c, "Aggiorna", self._yt_refresh).grid(row=0, column=1)
        self._btn(c, "Auto-assegna", self._yt_autoassign).grid(row=0, column=2, padx=(8, 0))
        self.yt_plan_box = tk.Text(
            c, height=6, bg=LOG_BG, fg=FG, relief="sunken", bd=2, font=F_MONO,
            state="disabled", padx=10, pady=8, wrap="none",
        )
        self.yt_plan_box.grid(row=1, column=0, columnspan=3, sticky="we", pady=(8, 0))

        # --- Metadati predefiniti (titolo + descrizione, uguali per tutti gli short) ---
        self.yt_title_var = tk.StringVar(value=self.settings.get("yt_title", ""))
        c = self._card("METADATI PREDEFINITI")
        c.columnconfigure(0, weight=1)
        self._label(c, "Titolo (max 100 caratteri; vuoto = nome del file)").grid(
            row=0, column=0, sticky="w")
        self._entry(c, self.yt_title_var).grid(row=1, column=0, sticky="we", pady=(2, 6))
        self._label(c, "Descrizione (max 5000 caratteri)").grid(row=2, column=0, sticky="w")
        self.yt_desc_text = tk.Text(c, height=4, bg=INPUT_BG, fg=FG, insertbackground=FG,
                                    relief="sunken", bd=2, font=F_LABEL, wrap="word")
        self.yt_desc_text.grid(row=3, column=0, sticky="we", pady=(2, 0))
        self.yt_desc_text.insert("1.0", self.settings.get("yt_description", ""))

        # --- Upload ---
        self.yt_upload_btn = self._btn(
            inner, "Carica e programma su YouTube", self._yt_upload, primary=True
        )
        self.yt_upload_btn.pack(fill="x", pady=(4, 8))

        self._yt_refresh_status()
        self._yt_refresh()

    def _yt_write(self, text: str):
        self.yt_plan_box.config(state="normal")
        self.yt_plan_box.delete("1.0", "end")
        self.yt_plan_box.insert("end", text)
        self.yt_plan_box.config(state="disabled")

    def _yt_append(self, text: str):
        self.yt_plan_box.config(state="normal")
        self.yt_plan_box.insert("end", text + "\n")
        self.yt_plan_box.see("end")
        self.yt_plan_box.config(state="disabled")

    def _yt_render_slots(self):
        slots = self.yt_schedule.get("slots", [])
        if slots:
            txt = " · ".join(f"{self.yt.WEEKDAYS_IT[int(d)]} {t}" for d, t in sorted(slots))
        else:
            txt = self._L("(nessuno slot definito)", "(no slots set)")
        self.yt_slots_label.config(text=self._L("Slot: ", "Slots: ") + txt)

    def _yt_refresh_status(self):
        if not self.yt.available():
            self.yt_status.config(
                text=self._L("Librerie YouTube non installate, verranno scaricate alla configurazione.",
                             "YouTube libraries not installed, they will be downloaded on setup."),
                fg=MUTED)
        elif self.yt.is_authorized():
            name = self.yt.channel_title() or "(canale)"
            self.yt_status.config(text=self._L("Connesso: ", "Connected: ") + name, fg=ACCENT)
        else:
            self.yt_status.config(text=self._L("Non connesso.", "Not connected."), fg=MUTED)
        self._yt_render_slots()

    def _yt_add_slot(self):
        import re
        t = self.slot_time_var.get().strip()
        if not re.match(r"^\d{1,2}:\d{2}$", t):
            messagebox.showerror("Orario", "Formato orario non valido. Usa HH:MM (es. 18:30).")
            return
        day = self.yt.WEEKDAYS_IT.index(self.slot_day_var.get())
        slots = self.yt_schedule.setdefault("slots", [])
        if [day, t] not in slots:
            slots.append([day, t])
            self.yt.save_schedule(self.yt_schedule)
        self._yt_render_slots()

    def _yt_clear_slots(self):
        self.yt_schedule["slots"] = []
        self.yt.save_schedule(self.yt_schedule)
        self._yt_render_slots()

    def _yt_refresh(self):
        import glob
        from clipper import OUTPUT_DIR
        self.yt_outputs = sorted(glob.glob(os.path.join(str(OUTPUT_DIR), "*.mp4")))
        self.yt_count_label.config(
            text=f"{len(self.yt_outputs)} " + self._L("video in output", "videos in output"))

    def _yt_autoassign(self):
        self._yt_refresh()
        slots = [(int(d), t) for d, t in self.yt_schedule.get("slots", [])]
        if not self.yt_outputs:
            self._yt_write("Nessun video nella cartella output.")
            return
        if not slots:
            messagebox.showwarning("Slot", "Definisci almeno uno slot settimanale.")
            return
        self.yt_plan = self.yt.assign_to_slots(self.yt_outputs, slots)
        lines = [
            f"{self.yt.WEEKDAYS_IT[dt.weekday()]} {dt:%d/%m %H:%M}   {os.path.basename(p)}"
            for p, dt in self.yt_plan
        ]
        cap = self.yt.MAX_UPLOADS_PER_DAY
        note = "" if len(self.yt_plan) <= cap else (
            f"\n\n(!) Verranno caricati i primi {cap} (limite quota YouTube/giorno). "
            "Gli altri al prossimo giorno.")
        self._yt_write("\n".join(lines) + note)

    def _yt_configure(self):
        from clipper import deps
        if not deps.is_installed("youtube"):
            if not messagebox.askyesno(
                "Librerie YouTube",
                "Servono le librerie Google (~30 MB).\nVuoi scaricarle e installarle ora?",
            ):
                return
            self.yt_upload_btn.config(state="disabled")
            self._yt_append("[deps] Installazione librerie YouTube...")

            def worker():
                ok = deps.install("youtube", log=lambda m: self.root.after(0, self._yt_append, m))
                self.root.after(0, self._yt_after_deps, ok)
            threading.Thread(target=worker, daemon=True).start()
        else:
            self._yt_pick_and_authorize()

    def _yt_after_deps(self, ok):
        self.yt_upload_btn.config(state="normal")
        self._yt_refresh_status()
        if ok:
            self._yt_pick_and_authorize()
        else:
            messagebox.showerror("Installazione", "Installazione librerie fallita. Vedi il log.")

    def _yt_pick_and_authorize(self):
        path = filedialog.askopenfilename(
            title="Seleziona client_secret.json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        self.yt_upload_btn.config(state="disabled")
        self._yt_append("[yt] Apertura browser per autorizzazione...")

        def worker():
            try:
                name = self.yt.authorize(path)
                self.root.after(0, self._yt_auth_done, name, None)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, self._yt_auth_done, None, exc)
        threading.Thread(target=worker, daemon=True).start()

    def _yt_auth_done(self, name, error):
        self.yt_upload_btn.config(state="normal")
        self._yt_refresh_status()
        if error:
            messagebox.showerror("Autorizzazione", f"Errore: {error}")
        else:
            messagebox.showinfo("YouTube", f"Connesso al canale: {name}")

    def _yt_upload(self):
        if not self.yt.available() or not self.yt.is_authorized():
            messagebox.showwarning("YouTube", "Configura prima l'accesso al canale (Configura accesso...).")
            return
        if not self.yt_plan:
            messagebox.showwarning("Pianificazione", "Premi prima «Auto-assegna».")
            return
        # Metadati predefiniti (limiti YouTube: titolo 100, descrizione 5000)
        def_title = self.yt_title_var.get().strip()[:100]
        def_desc = self.yt_desc_text.get("1.0", "end").strip()[:5000]
        self.settings["yt_title"] = def_title
        self.settings["yt_description"] = def_desc
        save_settings(self.settings)
        cap = self.yt.MAX_UPLOADS_PER_DAY
        batch = self.yt_plan[:cap]
        if not messagebox.askyesno(
            "Conferma upload",
            f"Carico {len(batch)} video su YouTube come privati, con pubblicazione programmata?",
        ):
            return
        self.yt_upload_btn.config(state="disabled")
        self._yt_append(f"\n[yt] Carico {len(batch)} video...")

        def worker():
            done = 0
            for path, dt in batch:
                title = def_title or os.path.splitext(os.path.basename(path))[0]
                try:
                    vid = self.yt.upload(path, title=title, description=def_desc, publish_at=dt)
                    done += 1
                    self.root.after(0, self._yt_append,
                                    f"  ok {os.path.basename(path)} -> {dt:%d/%m %H:%M} (id {vid})")
                except Exception as exc:  # noqa: BLE001
                    self.root.after(0, self._yt_append, f"  ERRORE {os.path.basename(path)}: {exc}")
            self.root.after(0, self._yt_upload_done, done, len(batch))
        threading.Thread(target=worker, daemon=True).start()

    def _yt_upload_done(self, done, total):
        self.yt_upload_btn.config(state="normal")
        self._yt_append(f"[yt] Completato: {done}/{total} caricati.")
        messagebox.showinfo("YouTube", f"Caricati {done}/{total} video (programmati).")

    # ============================================================ IMPOSTAZIONI
    def _build_settings_tab(self, parent):
        s = self.settings
        inner = tk.Frame(parent, bg=BG)
        inner.pack(fill="both", expand=True, padx=12, pady=8)
        self.content = inner

        self.music_enabled_var = tk.BooleanVar(value=s.get("music_enabled", False))
        self.music_volume_var = tk.IntVar(value=int(s.get("music_volume", 50)))
        self.sleep_timeout_var = tk.StringVar(value=str(s.get("sleep_timeout", 30)))
        self.music_file_path = s.get("music_file", "")
        self.avatar_paths = {
            "idle": s.get("idle_gif", "assistant.gif"),
            "gotosleep": s.get("gotosleep_gif", "gotosleep.gif"),
            "sleep": s.get("sleep_png", "sleep.png"),
        }
        self.avatar_labels = {}

        # --- Musica ---
        c = self._card("MUSICA DI SOTTOFONDO")
        c.columnconfigure(1, weight=1)
        self._check(c, "Musica in loop", self.music_enabled_var).grid(
            row=0, column=0, columnspan=3, sticky="w")
        self._label(c, "Volume").grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Scale(c, from_=0, to=100, orient="horizontal", variable=self.music_volume_var,
                 command=lambda v: self.music.set_volume(int(float(v))),
                 bg=CARD, fg=FG, troughcolor="white", highlightthickness=0, bd=1).grid(
            row=1, column=1, columnspan=2, sticky="we", padx=(8, 0), pady=(8, 0))
        self._label(c, "Brano").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.music_file_label = tk.Label(c, text=self._music_display(), bg=CARD, fg=MUTED,
                                         font=F_LABEL, anchor="w")
        self.music_file_label.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        mbtns = tk.Frame(c, bg=CARD)
        mbtns.grid(row=2, column=2, sticky="e", pady=(8, 0))
        self._btn(mbtns, "Scegli MP3...", self._pick_music).pack(side="left")
        self._btn(mbtns, "Default", self._music_default).pack(side="left", padx=(6, 0))

        # --- Assistente / criceto ---
        self.asst_name_var = tk.StringVar(value=s.get("assistant_name", "CRI il criceto"))
        c = self._card("ASSISTENTE (CRICETO)")
        c.columnconfigure(1, weight=1)
        self._label(c, "Nome dell'assistente").grid(row=0, column=0, sticky="w")
        self._entry(c, self.asst_name_var).grid(
            row=0, column=1, columnspan=2, sticky="we", padx=(8, 0))
        self._label(c, "Va a dormire dopo (secondi, 0 = mai)").grid(
            row=1, column=0, sticky="w", pady=(8, 0))
        self._entry(c, self.sleep_timeout_var, width=6).grid(
            row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self._avatar_file_row(c, 2, "Gif da sveglio (idle)", "idle")
        self._avatar_file_row(c, 3, "Gif addormentamento", "gotosleep")
        self._avatar_file_row(c, 4, "Immagine che dorme (PNG)", "sleep")

        # --- Suoni (stile MSN) ---
        self.sounds_enabled_var = tk.BooleanVar(value=s.get("sounds_enabled", True))
        self.sound_paths = {"send": s.get("sound_send", ""), "reply": s.get("sound_reply", "")}
        self.sound_labels = {}
        c = self._card("SUONI (STILE MSN)")
        c.columnconfigure(1, weight=1)
        self._check(c, "Effetti sonori (invio e risposta)", self.sounds_enabled_var,
                    command=self._on_sounds_toggle).grid(
            row=0, column=0, columnspan=3, sticky="w")
        self._sound_file_row(c, 1, "Suono invio", "send")
        self._sound_file_row(c, 2, "Suono risposta", "reply")

        # --- Animazioni ---
        self.viz_enabled_var = tk.BooleanVar(value=s.get("viz_enabled", True))
        c = self._card("ANIMAZIONI")
        self._check(c, "Visualizzatore stile Media Player dietro al log",
                    self.viz_enabled_var, command=self._on_viz_toggle).grid(
            row=0, column=0, sticky="w")

        # --- About ---
        c = self._card("ABOUT")
        tk.Label(c, text=self._L("Questo software è libero da multinazionali",
                                 "This software is free to use, benefit from it."),
                 bg=CARD, fg=FG, font=F_LABEL, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(c, text=self._L("Autore: goodman", "Author: goodman"),
                 bg=CARD, fg=MUTED, font=F_LABEL, anchor="w").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._link(c, "github",
                   "https://github.com/AlessandroBonomo28/DOPAMINIC").grid(row=2, column=0, sticky="w")
        self._link(c, "Buy Me a Coffee",
                   "https://buymeacoffee.com/servizibon0").grid(row=3, column=0, sticky="w", pady=(2, 0))

        self._btn(inner, "Applica impostazioni", self._settings_apply, primary=True).pack(
            fill="x", pady=(4, 8))

    def _on_viz_toggle(self):
        self.settings["viz_enabled"] = self.viz_enabled_var.get()
        save_settings(self.settings)
        if not self.viz_enabled_var.get():
            self.log_canvas.delete("viz")  # pulisci subito

    def _sound_file_row(self, parent, row, text, kind):
        self._label(parent, text).grid(row=row, column=0, sticky="w", pady=(8, 0))
        lbl = tk.Label(parent, text=os.path.basename(self.sound_paths[kind]) or "(default)",
                       bg=CARD, fg=MUTED, font=F_LABEL, anchor="w")
        lbl.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self.sound_labels[kind] = lbl
        bf = tk.Frame(parent, bg=CARD)
        bf.grid(row=row, column=2, sticky="e", pady=(8, 0))
        self._btn(bf, "Scegli...", lambda k=kind: self._pick_sound(k)).pack(side="left")
        self._btn(bf, "Prova", lambda k=kind: self._preview_sound(k),
                  click_sound=False).pack(side="left", padx=(4, 0))
        self._btn(bf, "Default", lambda k=kind: self._sound_default(k)).pack(side="left", padx=(4, 0))

    def _pick_sound(self, kind):
        path = filedialog.askopenfilename(
            title="Scegli suono", filetypes=[("Audio", "*.wav *.ogg *.mp3")])
        if not path:
            return
        if os.path.splitext(path)[1].lower() not in (".wav", ".ogg", ".mp3"):
            messagebox.showerror("Formato", "Usa un file wav, ogg o mp3.")
            return
        self.sound_paths[kind] = path
        self.sound_labels[kind].config(text=os.path.basename(path))

    def _sound_default(self, kind):
        self.sound_paths[kind] = ""
        self.sound_labels[kind].config(text="(default)")

    def _on_sounds_toggle(self):
        if self.sounds_enabled_var.get():
            self._ensure_audio()

    def _ensure_audio(self):
        """Assicura pygame (serve a musica e suoni). Lo propone se manca."""
        from clipper import deps
        if deps.is_installed("music"):
            return
        if not messagebox.askyesno(
            "Audio", "Per musica ed effetti sonori serve 'pygame' (~10 MB).\nInstallarlo ora?"):
            return
        threading.Thread(target=lambda: deps.install("music"), daemon=True).start()

    def _preview_sound(self, kind):
        from clipper import deps
        if not deps.is_installed("music"):
            self._ensure_audio()
            return
        from clipper.music import default_sound
        f = self.sound_paths.get(kind) or default_sound(kind)
        self.sounds.play(f, 0.7)

    def _avatar_file_row(self, parent, row, text, kind):
        self._label(parent, text).grid(row=row, column=0, sticky="w", pady=(8, 0))
        lbl = tk.Label(parent, text=os.path.basename(self.avatar_paths[kind]) or "(nessuno)",
                       bg=CARD, fg=MUTED, font=F_LABEL, anchor="w")
        lbl.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        self.avatar_labels[kind] = lbl
        self._btn(parent, "Scegli...", lambda k=kind: self._pick_avatar(k)).grid(
            row=row, column=2, sticky="e", pady=(8, 0))

    def _music_display(self):
        if self.music_file_path:
            return os.path.basename(self.music_file_path)
        from clipper.music import MUSIC_CREDIT
        return f"{MUSIC_CREDIT} ({self._L('predefinito', 'default')})"

    def _pick_music(self):
        path = filedialog.askopenfilename(
            title="Scegli brano", filetypes=[("Audio", "*.mp3 *.ogg *.wav")])
        if not path:
            return
        if os.path.splitext(path)[1].lower() not in (".mp3", ".ogg", ".wav"):
            messagebox.showerror("Formato", "Usa un file mp3, ogg o wav.")
            return
        self.music_file_path = path
        self.music_file_label.config(text=self._music_display())

    def _music_default(self):
        self.music_file_path = ""
        self.music_file_label.config(text=self._music_display())

    def _pick_avatar(self, kind):
        exts = [("PNG", "*.png")] if kind == "sleep" else [("GIF", "*.gif")]
        path = filedialog.askopenfilename(title="Scegli file", filetypes=exts)
        if not path:
            return
        try:
            from PIL import Image
            Image.open(path).verify()
        except Exception:
            messagebox.showerror("Formato", "File non valido o non supportato.")
            return
        self.avatar_paths[kind] = path
        self.avatar_labels[kind].config(text=os.path.basename(path))

    def _settings_apply(self):
        try:
            timeout = int(self.sleep_timeout_var.get())
            if timeout < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Timeout", "Inserisci i secondi come numero intero (>= 0).")
            return
        name = self.asst_name_var.get().strip() or "CRI il criceto"
        self.settings.update({
            "sleep_timeout": timeout,
            "assistant_name": name,
            "idle_gif": self.avatar_paths["idle"],
            "gotosleep_gif": self.avatar_paths["gotosleep"],
            "sleep_png": self.avatar_paths["sleep"],
            "music_enabled": self.music_enabled_var.get(),
            "music_volume": int(self.music_volume_var.get()),
            "music_file": self.music_file_path,
            "sounds_enabled": self.sounds_enabled_var.get(),
            "sound_send": self.sound_paths["send"],
            "sound_reply": self.sound_paths["reply"],
            "viz_enabled": self.viz_enabled_var.get(),
        })
        save_settings(self.settings)
        # Applica il nome dell'assistente
        self._asst_name = name
        self._asst_header_lbl.config(text=name)
        self._asst_toggle_btn.config(text=f"{name} :)")
        self._reload_avatar_media()
        self._avatar_idle()
        self._reset_sleep_timer()
        self._apply_music()
        messagebox.showinfo("Impostazioni", "Impostazioni applicate.")

    def _apply_music(self):
        from clipper import deps
        if not self.settings.get("music_enabled"):
            self.music.stop()
            return
        if not deps.is_installed("music"):
            if not messagebox.askyesno(
                "Musica", "Per la musica serve 'pygame' (~10 MB).\nInstallarlo ora?"):
                self.music_enabled_var.set(False)
                self.settings["music_enabled"] = False
                return

            def worker():
                ok = deps.install("music")
                if ok:
                    self.root.after(0, self._start_music)
            threading.Thread(target=worker, daemon=True).start()
            return
        self._start_music()

    def _start_music(self):
        from clipper.music import ensure_default_music
        f = self.settings.get("music_file") or ensure_default_music()
        vol = 0 if self._music_muted else int(self.settings.get("music_volume", 50))
        self.music.play(f, vol)
        # Analizza lo spettro del brano (in background) per il visualizzatore reattivo
        self._spectrum = None

        def _analyze():
            from clipper.music import analyze
            res = analyze(f)
            if res:
                self._spectrum, self._spectrum_fps = res
        threading.Thread(target=_analyze, daemon=True).start()

    def _toggle_mute(self):
        self._music_muted = not self._music_muted
        if self._music_muted:
            self.music.set_volume(0)
            self._mute_btn.config(text="Musica: MUTO")
        else:
            self.music.set_volume(int(self.settings.get("music_volume", 50)))
            self._mute_btn.config(text="Musica: ON")

    def _L(self, it, en):
        """Ritorna la stringa nella lingua corrente."""
        return en if self._lang == "en" else it

    def _toggle_language(self):
        self._set_language("en" if self._lang == "it" else "it")

    def _set_language(self, target):
        if target == self._lang:
            return
        fwd = UI_TRANS if target == "en" else {v: k for k, v in UI_TRANS.items()}
        self._lang = target
        self.settings["language"] = target
        try:
            save_settings(self.settings)
        except Exception:
            pass

        def walk(w):
            try:
                cur = w.cget("text")
            except Exception:
                cur = None
            if cur:
                s = cur.strip()
                if cur in fwd:
                    try:
                        w.configure(text=fwd[cur])
                    except Exception:
                        pass
                elif s in fwd:  # titoli card con spazi attorno: " SORGENTE "
                    try:
                        w.configure(text=cur.replace(s, fwd[s], 1))
                    except Exception:
                        pass
            for ch in w.winfo_children():
                walk(ch)

        walk(self.root)
        # tab del notebook
        for i in range(len(self._notebook.tabs())):
            cur = self._notebook.tab(i, "text")
            if cur in fwd:
                self._notebook.tab(i, text=fwd[cur])
        self._lang_btn.config(text="Lingua: IT" if target == "it" else "Language: EN")
        # log esistente + placeholder file
        self._log_lines = [fwd.get(line, line) for line in self._log_lines]
        self._redraw_log_text()
        if not self.video_path:
            self.video_path_var.set(self._L("Nessun file selezionato", "No file selected"))
        # etichette generate dinamicamente
        self._update_chill()
        self._update_gpu_hint()
        try:
            self._yt_render_slots()
            self._yt_refresh()
            self._yt_refresh_status()
            self.music_file_label.config(text=self._music_display())
        except Exception:
            pass
        # assistente bilingue
        try:
            self.assistant.set_lang(target)
        except Exception:
            pass

    def _toggle_theme(self):
        self._retheme("dark" if self._theme == "light" else "light")

    def _retheme(self, target):
        """Cambia tema (light/dark) ricolorando i widget esistenti, senza ricostruire."""
        old, new = PALETTES[self._theme], PALETTES[target]
        remap = {old[k].lower(): new[k] for k in old}
        self._theme = target
        self.settings["theme"] = target
        try:
            save_settings(self.settings)
        except Exception:
            pass
        apply_palette(new)
        opts = ("background", "foreground", "activebackground", "activeforeground",
                "selectcolor", "highlightbackground", "insertbackground", "troughcolor")

        def walk(w):
            for opt in opts:
                try:
                    cur = str(w.cget(opt)).lower()
                except Exception:
                    continue
                if cur in remap:
                    try:
                        w.configure(**{opt: remap[cur]})
                    except Exception:
                        pass
            for ch in w.winfo_children():
                walk(ch)

        walk(self.root)
        self.root.configure(bg=BG)
        self._init_style()  # ttk (combobox/notebook/progressbar/scrollbar)
        try:
            self.chat_box.tag_configure("me", foreground=ACCENT)
            self.chat_box.tag_configure("bot", foreground="#9fe0b0" if target == "dark" else "#006400")
        except Exception:
            pass
        # il color swatch deve mostrare il colore sottotitoli, non il tema
        try:
            self.color_swatch.config(bg=self.subtitle_color_var.get())
        except Exception:
            pass
        self._theme_btn.config(text="Tema: Scuro" if target == "light" else "Tema: Chiaro")
        self._redraw_log_text()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
