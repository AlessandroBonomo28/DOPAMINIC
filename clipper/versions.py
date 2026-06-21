"""Finestra 'Versioni': elenca le release di GitHub con il changelog e permette
di installare qualsiasi versione (upgrade o downgrade, utile per verificare)."""
import threading
import tkinter as tk
from tkinter import messagebox

from . import updater

DEFAULT_COLORS = {
    "BG": "#2d2d30", "CARD": "#2d2d30", "FG": "#e6e6e6", "MUTED": "#9a9a9a",
    "ACCENT": "#7aa2ff", "INPUT_BG": "#1e1e1e", "SUCCESS_HOVER": "#3e3e42",
}


class VersionsWindow:
    """on_install(url, version) viene chiamato quando l'utente sceglie di installare."""

    def __init__(self, parent, colors=None, lang="it", current_version="", on_install=None):
        self.parent = parent
        self.lang = lang
        self.current = str(current_version)
        self.on_install = on_install
        self.col = dict(DEFAULT_COLORS)
        if colors:
            self.col.update({k: v for k, v in colors.items() if v})
        self.releases = []
        self._build()
        threading.Thread(target=self._fetch, daemon=True).start()

    def _L(self, it, en):
        return en if self.lang == "en" else it

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

    def _build(self):
        col = self.col
        self.win = tk.Toplevel(self.parent)
        self.win.title(self._L("Versioni di DOPAMINIC", "DOPAMINIC versions"))
        self.win.configure(bg=col["BG"])
        self.win.geometry("780x540")
        self.win.minsize(640, 440)
        self.win.transient(self.parent)

        tk.Label(self.win, text=self._L(
                     f"Versione installata: {self.current}",
                     f"Installed version: {self.current}"),
                 bg=col["BG"], fg=col["FG"], font=("Tahoma", 10, "bold")).pack(
            anchor="w", padx=12, pady=(10, 4))

        body = tk.Frame(self.win, bg=col["BG"])
        body.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        left = tk.Frame(body, bg=col["BG"])
        left.pack(side="left", fill="y", padx=(0, 10))
        tk.Label(left, text=self._L("Release", "Releases"), bg=col["BG"], fg=col["ACCENT"],
                 font=("Tahoma", 10, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(
            left, width=30, bg=col["INPUT_BG"], fg=col["FG"],
            selectbackground=col["ACCENT"], selectforeground="#ffffff",
            highlightthickness=1, highlightbackground=col["MUTED"],
            relief="flat", font=("Consolas", 10), activestyle="none")
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = tk.Frame(body, bg=col["BG"])
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="Changelog", bg=col["BG"], fg=col["ACCENT"],
                 font=("Tahoma", 10, "bold")).pack(anchor="w")
        self.notes = tk.Text(right, bg=col["INPUT_BG"], fg=col["FG"], wrap="word",
                             relief="flat", highlightthickness=1,
                             highlightbackground=col["MUTED"], font=("Tahoma", 9))
        self.notes.pack(fill="both", expand=True)
        self.notes.configure(state="disabled")

        bar = tk.Frame(self.win, bg=col["BG"])
        bar.pack(fill="x", padx=12, pady=(0, 10))
        self.install_btn = self._btn(bar, self._L("Installa questa versione", "Install this version"),
                                     self._install, primary=True)
        self.install_btn.pack(side="right")
        self.install_btn.config(state="disabled")
        self._btn(bar, self._L("Chiudi", "Close"), self.win.destroy).pack(side="right", padx=(0, 6))
        self.status = tk.Label(bar, text=self._L("Carico le release...", "Loading releases..."),
                               bg=col["BG"], fg=col["MUTED"], font=("Tahoma", 9))
        self.status.pack(side="left")

    # -------------------------------------------------------------- dati
    def _fetch(self):
        rels = updater.list_releases()
        try:
            self.win.after(0, self._populate, rels)
        except Exception:
            pass

    def _populate(self, rels):
        self.releases = rels
        self.listbox.delete(0, "end")
        if not rels:
            self.status.config(text=self._L(
                "Nessuna release trovata (repo non pubblico o senza release).",
                "No releases found (repo not public or no releases yet)."))
            return
        latest_done = False
        for r in rels:
            marks = []
            if r["version"] == self.current:
                marks.append(self._L("attuale", "current"))
            if not r["prerelease"] and not latest_done:
                marks.append(self._L("ultima", "latest"))
                latest_done = True
            if r["prerelease"]:
                marks.append("pre")
            suffix = f"  ({', '.join(marks)})" if marks else ""
            self.listbox.insert("end", f"{r['tag']}   {r['date']}{suffix}")
        self.status.config(text=self._L(f"{len(rels)} release trovate.",
                                        f"{len(rels)} releases found."))
        self.listbox.selection_set(0)
        self._on_select(None)

    def _on_select(self, _ev):
        sel = self.listbox.curselection()
        if not sel:
            return
        r = self.releases[sel[0]]
        self.notes.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.notes.insert("end", (r["name"] or r["tag"]) + "\n\n")
        self.notes.insert("end", r["body"] or self._L("(nessuna nota)", "(no notes)"))
        self.notes.configure(state="disabled")
        # abilita installa solo se la release ha un installer e non e' quella attuale
        same = (r["version"] == self.current)
        can = bool(r["url"]) and not same
        self.install_btn.config(state="normal" if can else "disabled")

    def _install(self):
        sel = self.listbox.curselection()
        if not sel or not self.on_install:
            return
        r = self.releases[sel[0]]
        if not r["url"]:
            return
        # Warning esplicito se si torna a una versione piu' vecchia (downgrade).
        if updater.is_newer(self.current, r["version"]):
            ok = messagebox.askyesno(
                self._L("Downgrade", "Downgrade"),
                self._L(
                    f"Stai per installare la {r['version']}, piu' VECCHIA di quella "
                    f"attuale ({self.current}).\n\nVuoi davvero fare il downgrade?",
                    f"You are about to install {r['version']}, which is OLDER than your "
                    f"current one ({self.current}).\n\nDo you really want to downgrade?"),
                icon="warning", parent=self.win)
        else:
            ok = messagebox.askyesno(
                self._L("Installa", "Install"),
                self._L(f"Installare la versione {r['version']}?",
                        f"Install version {r['version']}?"),
                parent=self.win)
        if not ok:
            return
        self.win.destroy()
        self.on_install(r["url"], r["version"])
