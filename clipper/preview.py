"""Editor/anteprima delle clip rilevate, prima di generare gli short.

Finestra in stile editor (CapCut-like, semplificato):
- anteprima a fotogrammi: trascini la testina sulla timeline e vedi il frame a
  quel punto; un tasto Play scorre i frame (senza audio, a risoluzione ridotta);
- timeline con tutte le clip; per la clip selezionata ritocchi inizio e fine
  trascinando le maniglie o con i tasti fini;
- poi Conferma (genera) oppure Annulla.

Nessuna dipendenza extra: i fotogrammi arrivano da moviepy (get_frame) e vengono
mostrati con Pillow (ImageTk).
"""
import tkinter as tk

from PIL import Image, ImageTk

_MIN_VISIBLE = 4.0      # finestra minima visibile in timeline quando si zooma (s)

DEFAULT_COLORS = {
    "BG": "#2d2d30", "CARD": "#2d2d30", "FG": "#e6e6e6", "MUTED": "#9a9a9a",
    "ACCENT": "#7aa2ff", "INPUT_BG": "#1e1e1e", "SUCCESS_HOVER": "#3e3e42",
}
_HANDLE_START = "#34c759"
_HANDLE_END = "#ff3b30"
_PLAYHEAD = "#ffd60a"
_MIN_DUR = 1.0          # durata minima di una clip (s)
_PREVIEW_W = 620        # larghezza max del fotogramma di anteprima


def _fmt(t: float) -> str:
    t = max(0.0, t)
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:04.1f}"


class PreviewEditor:
    """Finestra modale di anteprima/modifica. Chiama `on_confirm(clips)` su Conferma."""

    def __init__(self, parent, video_path, clips, duration, on_confirm,
                 colors=None, title_font=("Tahoma", 11, "bold"), default_dur=15.0,
                 music_pause=None, music_resume=None, lang="it"):
        self.parent = parent
        self.lang = lang
        self.video_path = video_path
        self.clips = [(float(s), float(e)) for s, e in clips]
        self.dur = float(duration)
        self.on_confirm = on_confirm
        self.default_dur = max(_MIN_DUR, float(default_dur))
        # Audio in anteprima: callback per mettere in pausa/riprendere la musica
        # di sottofondo dell'app (condividono lo stesso stream di pygame).
        self.music_pause = music_pause
        self.music_resume = music_resume
        self._audio_playing = False
        self._audio_base = 0.0      # tempo del video corrispondente all'inizio del segmento
        self._used_audio = False    # se abbiamo dirottato lo stream musica (da ripristinare)
        self.col = dict(DEFAULT_COLORS)
        if colors:
            self.col.update({k: v for k, v in colors.items() if v})
        self.title_font = title_font
        self.font = ("Tahoma", 10)
        self.font_small = ("Tahoma", 8, "bold")

        self.sel = 0
        self.playhead = self.clips[0][0] if self.clips else 0.0
        self.grab = None
        self._playing = False
        self._photo = None
        self._pending_t = self.playhead
        self._frame_scheduled = False
        self.zoom = 1.0          # 1.0 = tutto il video; >1 = zoomato
        self.view_start = 0.0    # secondo all'estremo sinistro della timeline visibile

        # Reader video aperto per tutta la sessione dell'editor.
        from moviepy.editor import VideoFileClip
        self.clip = VideoFileClip(video_path)
        self.fps = self.clip.fps or 25.0
        cw, ch = self.clip.w, self.clip.h
        self.disp_w = _PREVIEW_W
        self.disp_h = max(1, int(_PREVIEW_W * ch / cw))
        if self.disp_h > 360:
            self.disp_h = 360
            self.disp_w = max(1, int(360 * cw / ch))

        self._build_ui()
        self._refresh_list()
        if self.clips:
            self._select(0)
        else:
            self._update_labels()
            self._draw_timeline()

    def _L(self, it, en):
        """Ritorna la stringa nella lingua dell'editor (it/en)."""
        return en if self.lang == "en" else it

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        col = self.col
        self.win = tk.Toplevel(self.parent)
        self.win.title(self._L("Anteprima e modifica clip - DOPAMINIC",
                               "Preview and edit clips - DOPAMINIC"))
        self.win.configure(bg=col["BG"])
        self.win.geometry("980x880")
        self.win.minsize(840, 760)
        self.win.transient(self.parent)
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)

        # --- riga alta: lista clip + anteprima ---
        top = tk.Frame(self.win, bg=col["BG"])
        top.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        left = tk.Frame(top, bg=col["BG"])
        left.pack(side="left", fill="y", padx=(0, 10))
        tk.Label(left, text="CLIP", bg=col["BG"], fg=col["ACCENT"],
                 font=self.title_font).pack(anchor="w")
        self.listbox = tk.Listbox(
            left, width=26, height=12, bg=col["INPUT_BG"], fg=col["FG"],
            selectbackground=col["ACCENT"], selectforeground="#ffffff",
            highlightthickness=1, highlightbackground=col["MUTED"],
            relief="flat", font=("Consolas", 10), activestyle="none",
        )
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self._btn(left, self._L("+ Aggiungi clip (alla testina)", "+ Add clip (at playhead)"),
                  self._add_clip).pack(fill="x", pady=(8, 0))
        self._btn(left, self._L("Rimuovi clip selezionata", "Remove selected clip"),
                  self._remove).pack(fill="x", pady=(4, 0))

        right = tk.Frame(top, bg=col["BG"])
        right.pack(side="left", fill="both", expand=True)
        self.pv = tk.Canvas(right, width=self.disp_w, height=self.disp_h,
                            bg="#000000", highlightthickness=1,
                            highlightbackground=col["MUTED"])
        self.pv.pack()
        self.time_lbl = tk.Label(right, text="00:00.0", bg=col["BG"], fg=col["FG"],
                                 font=("Consolas", 11, "bold"))
        self.time_lbl.pack(pady=(4, 0))

        # --- istruzioni + regolazione fine della clip selezionata ---
        info = tk.Frame(self.win, bg=col["BG"])
        info.pack(fill="x", padx=10, pady=(2, 0))
        tk.Label(info, text=self._L("Trascina le maniglie sulla timeline qui sotto:  "
                                    "VERDE = inizio,  ROSSA = fine.",
                                    "Drag the handles on the timeline below:  "
                                    "GREEN = start,  RED = end."),
                 bg=col["BG"], fg=col["FG"], font=("Tahoma", 9, "bold"),
                 anchor="w").pack(anchor="w")
        tk.Label(info, text=self._L("Se col trascinamento non sei preciso, aggiusta la clip "
                                    "selezionata con i tasti:",
                                    "If dragging isn't precise, fine-tune the selected clip "
                                    "with the buttons:"),
                 bg=col["BG"], fg=col["MUTED"], font=("Tahoma", 9), anchor="w").pack(anchor="w")

        edit = tk.Frame(self.win, bg=col["BG"])
        edit.pack(fill="x", padx=10, pady=(4, 6))
        edit.columnconfigure(6, weight=1)
        # Riga INIZIO: pallino verde + valore + tasti -30/-1/+1/+30
        tk.Label(edit, text=self._L("● Inizio", "● Start"), bg=col["BG"], fg=_HANDLE_START,
                 font=("Tahoma", 10, "bold"), width=9, anchor="w").grid(row=0, column=0, sticky="w")
        self.start_val = tk.Label(edit, text="--:--", bg=col["BG"], fg=col["FG"],
                                  font=("Consolas", 11, "bold"), width=8, anchor="w")
        self.start_val.grid(row=0, column=1, padx=(0, 8))
        self._btn(edit, "-30s", lambda: self._nudge("start", -30)).grid(row=0, column=2, padx=2)
        self._btn(edit, "-1s", lambda: self._nudge("start", -1)).grid(row=0, column=3, padx=2)
        self._btn(edit, "+1s", lambda: self._nudge("start", 1)).grid(row=0, column=4, padx=2)
        self._btn(edit, "+30s", lambda: self._nudge("start", 30)).grid(row=0, column=5, padx=2)
        # Riga FINE: pallino rosso + valore + tasti
        tk.Label(edit, text=self._L("● Fine", "● End"), bg=col["BG"], fg=_HANDLE_END,
                 font=("Tahoma", 10, "bold"), width=9, anchor="w").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.end_val = tk.Label(edit, text="--:--", bg=col["BG"], fg=col["FG"],
                                font=("Consolas", 11, "bold"), width=8, anchor="w")
        self.end_val.grid(row=1, column=1, padx=(0, 8), pady=(5, 0))
        self._btn(edit, "-30s", lambda: self._nudge("end", -30)).grid(row=1, column=2, padx=2, pady=(5, 0))
        self._btn(edit, "-1s", lambda: self._nudge("end", -1)).grid(row=1, column=3, padx=2, pady=(5, 0))
        self._btn(edit, "+1s", lambda: self._nudge("end", 1)).grid(row=1, column=4, padx=2, pady=(5, 0))
        self._btn(edit, "+30s", lambda: self._nudge("end", 30)).grid(row=1, column=5, padx=2, pady=(5, 0))
        # Durata / indice clip
        self.dur_lbl = tk.Label(edit, text="", bg=col["BG"], fg=col["MUTED"], font=self.font)
        self.dur_lbl.grid(row=0, column=6, rowspan=2, sticky="e")

        # --- controlli zoom timeline ---
        zrow = tk.Frame(self.win, bg=col["BG"])
        zrow.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(zrow, text=self._L("Zoom timeline:", "Timeline zoom:"), bg=col["BG"],
                 fg=col["FG"], font=("Tahoma", 9, "bold")).pack(side="left")
        self._btn(zrow, "  -  ", lambda: self._set_zoom(self.zoom / 1.5)).pack(side="left", padx=(6, 2))
        self._btn(zrow, "  +  ", lambda: self._set_zoom(self.zoom * 1.5)).pack(side="left", padx=2)
        self._btn(zrow, self._L("Tutto", "All"), lambda: self._set_zoom(1.0)).pack(side="left", padx=(2, 8))
        self.zoom_lbl = tk.Label(zrow, text="", bg=col["BG"], fg=col["MUTED"], font=("Tahoma", 8))
        self.zoom_lbl.pack(side="left")

        # --- timeline ---
        self.tl_m = 14
        self.tl_h = 72
        self.tl = tk.Canvas(self.win, height=self.tl_h, bg=col["CARD"],
                            highlightthickness=1, highlightbackground=col["MUTED"])
        self.tl.pack(fill="x", padx=10, pady=(2, 0))
        self.tl.bind("<Configure>", lambda e: self._draw_timeline())
        self.tl.bind("<Button-1>", self._on_press)
        self.tl.bind("<B1-Motion>", self._on_drag)
        self.tl.bind("<ButtonRelease-1>", self._on_release)
        self.tl.bind("<MouseWheel>", self._on_wheel)        # rotella = zoom centrato sul cursore
        # Scrollbar orizzontale: per scorrere quando si e' zoomati.
        self.hbar = tk.Scrollbar(self.win, orient="horizontal", command=self._on_scroll,
                                 bg=col["SUCCESS_HOVER"], troughcolor=col["INPUT_BG"],
                                 activebackground=col["ACCENT"], bd=0, highlightthickness=0)
        self.hbar.pack(fill="x", padx=10, pady=(0, 2))
        tk.Label(self.win, text=self._L(
                     "Clicca sulla barra per spostare la testina (gialla). Rotella o "
                     "tasti +/- per zoomare, trascina la barra sotto per scorrere.",
                     "Click the bar to move the playhead (yellow). Wheel or +/- buttons "
                     "to zoom, drag the bar below to scroll."),
                 bg=col["BG"], fg=col["MUTED"], font=("Tahoma", 8)).pack(anchor="w", padx=12)

        # --- controlli play + conferma/annulla ---
        bar = tk.Frame(self.win, bg=col["BG"])
        bar.pack(fill="x", padx=10, pady=(6, 10))
        self._btn(bar, self._L("|< Prec", "|< Prev"), lambda: self._step_sel(-1)).pack(side="left")
        self.play_btn = self._btn(bar, "Play", self._toggle_play)
        self.play_btn.pack(side="left", padx=4)
        self._btn(bar, self._L("Succ >|", "Next >|"), lambda: self._step_sel(1)).pack(side="left")
        self.confirm_btn = self._btn(bar, self._L("Conferma e genera", "Confirm and generate"),
                                     self._confirm, primary=True)
        self.confirm_btn.pack(side="right")
        self._btn(bar, self._L("Annulla", "Cancel"), self._cancel).pack(side="right", padx=(0, 6))

        self.win.update_idletasks()
        self.tl_w = self.tl.winfo_width() or 800

    def _btn(self, parent, text, cmd, primary=False):
        col = self.col
        return tk.Button(
            parent, text=text, command=cmd,
            bg=col["ACCENT"] if primary else col["SUCCESS_HOVER"],
            fg="#ffffff" if primary else col["FG"],
            activebackground=col["ACCENT"], activeforeground="#ffffff",
            relief="raised", bd=2, font=("Tahoma", 9, "bold" if primary else "normal"),
            padx=8, pady=3, cursor="hand2",
        )

    # ------------------------------------------------------- coordinate <-> tempo
    def _visible_dur(self):
        return self.dur / self.zoom

    def _t_to_x(self, t):
        usable = max(1, self.tl_w - 2 * self.tl_m)
        vd = self._visible_dur()
        return self.tl_m + ((t - self.view_start) / vd) * usable

    def _x_to_t(self, x):
        usable = max(1, self.tl_w - 2 * self.tl_m)
        vd = self._visible_dur()
        t = self.view_start + (x - self.tl_m) / usable * vd
        return max(0.0, min(self.dur, t))

    def _max_zoom(self):
        return max(1.0, self.dur / _MIN_VISIBLE)

    def _clamp_view(self):
        vd = self._visible_dur()
        self.view_start = max(0.0, min(self.view_start, max(0.0, self.dur - vd)))

    def _ensure_visible(self, t):
        vd = self._visible_dur()
        if t < self.view_start or t > self.view_start + vd:
            self.view_start = t - vd / 2
            self._clamp_view()

    def _set_zoom(self, z, center=None):
        self.zoom = max(1.0, min(z, self._max_zoom()))
        c = self.playhead if center is None else center
        self.view_start = c - self._visible_dur() / 2
        self._clamp_view()
        self._draw_timeline()

    def _on_wheel(self, ev):
        # rotella su = zoom in, centrato sul tempo sotto il cursore
        t = self._x_to_t(ev.x)
        self._set_zoom(self.zoom * (1.25 if ev.delta > 0 else 0.8), center=t)

    def _on_scroll(self, *args):
        if not args:
            return
        op = args[0]
        vd = self._visible_dur()
        if op == "moveto":
            self.view_start = float(args[1]) * self.dur
        elif op == "scroll":
            n = int(args[1])
            step = vd * (0.9 if (len(args) > 2 and args[2] == "pages") else 0.1)
            self.view_start += n * step
        self._clamp_view()
        self._draw_timeline()

    def _sync_scroll(self):
        vd = self._visible_dur()
        try:
            self.hbar.set(self.view_start / self.dur,
                          min(1.0, (self.view_start + vd) / self.dur))
        except Exception:
            pass

    # ------------------------------------------------------------------ rendering
    def _draw_timeline(self):
        c = self.tl
        w = self.tl.winfo_width()
        if w > 1:                      # 1 = canvas non ancora mappato: tieni il valore noto
            self.tl_w = w
        c.delete("all")
        W, H, m = self.tl_w, self.tl_h, self.tl_m
        y0, y1 = 10, H - 18
        vs = self.view_start
        ve = self.view_start + self._visible_dur()
        c.create_rectangle(m, y0, W - m, y1, fill=self.col["INPUT_BG"],
                           outline=self.col["MUTED"])
        for i, (s, e) in enumerate(self.clips):
            if e < vs or s > ve:        # clip fuori dalla finestra visibile
                continue
            x0 = max(m, self._t_to_x(s))
            x1 = min(W - m, self._t_to_x(e))
            sel = (i == self.sel)
            c.create_rectangle(x0, y0 + 2, x1, y1 - 2,
                               fill=self.col["ACCENT"] if sel else self.col["SUCCESS_HOVER"],
                               outline=self.col["FG"] if sel else self.col["MUTED"],
                               width=2 if sel else 1)
            if x1 - x0 > 12:
                c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(i + 1),
                              fill="#ffffff" if sel else self.col["FG"], font=self.font_small)
        if 0 <= self.sel < len(self.clips):
            s, e = self.clips[self.sel]
            for t, color in ((s, _HANDLE_START), (e, _HANDLE_END)):
                if vs <= t <= ve:
                    x = self._t_to_x(t)
                    c.create_line(x, y0 - 4, x, y1 + 4, fill=color, width=3)
        if vs <= self.playhead <= ve:
            xph = self._t_to_x(self.playhead)
            c.create_line(xph, 2, xph, H - 2, fill=_PLAYHEAD, width=2)
        # etichette tempo agli estremi della finestra visibile
        c.create_text(m, H - 8, text=_fmt(vs), anchor="w", fill=self.col["MUTED"],
                      font=("Tahoma", 7))
        c.create_text(W - m, H - 8, text=_fmt(ve), anchor="e",
                      fill=self.col["MUTED"], font=("Tahoma", 7))
        if hasattr(self, "zoom_lbl"):
            self.zoom_lbl.config(text=self._L(
                f"finestra visibile {_fmt(self._visible_dur())}  (zoom {self.zoom:.1f}x)",
                f"visible window {_fmt(self._visible_dur())}  (zoom {self.zoom:.1f}x)"))
        self._sync_scroll()

    def _request_frame(self, t):
        self._pending_t = max(0.0, min(self.dur - 1.0 / self.fps, t))
        if not self._frame_scheduled:
            self._frame_scheduled = True
            self.win.after(15, self._do_frame)

    def _do_frame(self):
        self._frame_scheduled = False
        t = self._pending_t
        try:
            frame = self.clip.get_frame(t)
        except Exception:
            return
        img = Image.fromarray(frame)
        img.thumbnail((self.disp_w, self.disp_h))
        self._photo = ImageTk.PhotoImage(img)
        self.pv.delete("frame")
        self.pv.create_image(self.disp_w // 2, self.disp_h // 2,
                             image=self._photo, anchor="center", tags="frame")
        self.time_lbl.config(text=_fmt(t))

    # ------------------------------------------------------------------ selezione
    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for i, (s, e) in enumerate(self.clips):
            self.listbox.insert("end", f"{i + 1:>2}  {_fmt(s)} - {_fmt(e)}  ({e - s:.1f}s)")

    def _refresh_list_item(self):
        if 0 <= self.sel < len(self.clips):
            s, e = self.clips[self.sel]
            self.listbox.delete(self.sel)
            self.listbox.insert(self.sel, f"{self.sel + 1:>2}  {_fmt(s)} - {_fmt(e)}  ({e - s:.1f}s)")
            self.listbox.selection_set(self.sel)

    def _on_list_select(self, _ev):
        sel = self.listbox.curselection()
        if sel:
            self._select(sel[0])

    def _select(self, i):
        if not (0 <= i < len(self.clips)):
            return
        self._stop_play()   # cambiare clip ferma la riproduzione (evita desync audio)
        self.sel = i
        s, _e = self.clips[i]
        self.playhead = s
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(i)
        self._request_frame(s)
        self._update_labels()
        self._ensure_visible(s)
        self._draw_timeline()

    def _step_sel(self, delta):
        if self.clips:
            self._select((self.sel + delta) % len(self.clips))

    def _update_labels(self):
        if 0 <= self.sel < len(self.clips):
            s, e = self.clips[self.sel]
            self.start_val.config(text=_fmt(s))
            self.end_val.config(text=_fmt(e))
            self.dur_lbl.config(text=self._L(
                f"Clip {self.sel + 1}/{len(self.clips)}  -  durata {e - s:.1f}s",
                f"Clip {self.sel + 1}/{len(self.clips)}  -  length {e - s:.1f}s"))
        else:
            self.start_val.config(text="--:--")
            self.end_val.config(text="--:--")
            self.dur_lbl.config(text=self._L("Nessuna clip", "No clip"))

    # ------------------------------------------------------------------ modifiche
    def _nudge(self, edge, delta):
        if not (0 <= self.sel < len(self.clips)):
            return
        self._stop_play()
        s, e = self.clips[self.sel]
        if edge == "start":
            s = max(0.0, min(s + delta, e - _MIN_DUR))
            self.playhead = s
        else:
            e = min(self.dur, max(e + delta, s + _MIN_DUR))
            self.playhead = e
        self.clips[self.sel] = (s, e)
        self._apply_edit()

    def _add_clip(self):
        """Crea una nuova clip alla testina (durata predefinita), poi la seleziona."""
        s = max(0.0, self.playhead)
        e = min(self.dur, s + self.default_dur)
        if e - s < _MIN_DUR:                 # vicino alla fine: indietreggia l'inizio
            s = max(0.0, e - self.default_dur)
        if e - s < _MIN_DUR:
            return
        new = (s, e)
        self.clips.append(new)
        self.clips.sort()
        self.sel = self.clips.index(new)
        self._refresh_list()
        self._select(self.sel)
        self.confirm_btn.config(state="normal")

    def _apply_edit(self):
        self._request_frame(self.playhead)
        self._refresh_list_item()
        self._update_labels()
        self._draw_timeline()

    def _remove(self):
        if not (0 <= self.sel < len(self.clips)):
            return
        del self.clips[self.sel]
        if self.sel >= len(self.clips):
            self.sel = len(self.clips) - 1
        self._refresh_list()
        if self.clips:
            self._select(self.sel)
            self.confirm_btn.config(state="normal")
        else:
            self._update_labels()
            self._draw_timeline()
            self.confirm_btn.config(state="disabled")

    # ------------------------------------------------------------------ mouse timeline
    def _on_press(self, ev):
        self._stop_play()   # interagire con la timeline ferma la riproduzione
        t = self._x_to_t(ev.x)
        self.grab = None
        if 0 <= self.sel < len(self.clips):
            s, e = self.clips[self.sel]
            if abs(self._t_to_x(s) - ev.x) <= 8:
                self.grab = "start"
            elif abs(self._t_to_x(e) - ev.x) <= 8:
                self.grab = "end"
        if self.grab is None:
            for i, (s, e) in enumerate(self.clips):
                if s <= t <= e:
                    self._select(i)
                    break
            self.grab = "playhead"
            self.playhead = t
            self._request_frame(t)
            self._draw_timeline()

    def _on_drag(self, ev):
        t = self._x_to_t(ev.x)
        if self.grab == "playhead":
            self.playhead = t
            self._request_frame(t)
            self._draw_timeline()
        elif self.grab in ("start", "end") and 0 <= self.sel < len(self.clips):
            s, e = self.clips[self.sel]
            if self.grab == "start":
                s = max(0.0, min(t, e - _MIN_DUR))
                self.playhead = s
            else:
                e = min(self.dur, max(t, s + _MIN_DUR))
                self.playhead = e
            self.clips[self.sel] = (s, e)
            self._apply_edit()

    def _on_release(self, _ev):
        self.grab = None

    # ------------------------------------------------------------------ playback
    def _toggle_play(self):
        if self._playing:
            self._stop_play()
            return
        if not (0 <= self.sel < len(self.clips)):
            return
        s, e = self.clips[self.sel]
        if not (s <= self.playhead < e):
            self.playhead = s
        self._playing = True
        self.play_btn.config(text=self._L("Pausa", "Pause"))
        self._start_audio(self.playhead)   # riproduce anche l'audio (se disponibile)
        self._play_step()

    def _stop_play(self):
        if self._playing:
            self._playing = False
            self.play_btn.config(text="Play")
        self._stop_audio()

    def _start_audio(self, t):
        """Estrae il segmento [t, fine clip] in un WAV e lo riproduce con pygame."""
        if not (0 <= self.sel < len(self.clips)):
            return
        _s, e = self.clips[self.sel]
        if self.clip.audio is None or t >= e - 0.05:
            self._audio_playing = False
            return
        try:
            from . import TEMP_DIR
            import pygame
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            seg = str(TEMP_DIR / "preview_seg.wav")
            self.clip.audio.subclip(t, min(e, self.dur)).write_audiofile(
                seg, fps=44100, nbytes=2, logger=None)
            if self.music_pause:           # ferma la musica di sottofondo dell'app
                self.music_pause()
            self._used_audio = True
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(seg)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()       # il segmento parte gia' da t
            self._audio_base = t
            self._audio_playing = True
        except Exception:
            self._audio_playing = False     # niente audio: si scorre solo i frame

    def _stop_audio(self):
        self._audio_playing = False
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass

    def _play_step(self):
        if not self._playing or not (0 <= self.sel < len(self.clips)):
            self._playing = False
            return
        _s, e = self.clips[self.sel]
        if self._audio_playing:
            # l'audio fa da metronomo: la posizione la dà get_pos (ms dall'avvio)
            try:
                import pygame
                pos = pygame.mixer.music.get_pos()
            except Exception:
                pos = -1
            self.playhead = e if pos < 0 else self._audio_base + pos / 1000.0
        else:
            self.playhead += 0.08
        if self.playhead >= e:
            self.playhead = e
            self._stop_play()
            self._request_frame(self.playhead)
            self._ensure_visible(self.playhead)
            self._draw_timeline()
            return
        self._request_frame(self.playhead)
        self._ensure_visible(self.playhead)
        self._draw_timeline()
        self.win.after(40, self._play_step)

    # ------------------------------------------------------------------ chiusura
    def _cleanup(self):
        self._playing = False
        self._stop_audio()
        # Ripristina la musica di sottofondo se l'avevamo interrotta per l'anteprima.
        if self._used_audio and self.music_resume:
            try:
                self.music_resume()
            except Exception:
                pass
        try:
            self.clip.close()
        except Exception:
            pass

    def _confirm(self):
        clips = sorted((float(s), float(e)) for s, e in self.clips if e - s >= _MIN_DUR)
        self._cleanup()
        self.win.destroy()
        if clips and self.on_confirm:
            self.on_confirm(clips)

    def _cancel(self):
        self._cleanup()
        self.win.destroy()
