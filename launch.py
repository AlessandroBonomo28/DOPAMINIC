"""Entry point dell'app con cattura degli errori di avvio.

L'app gira con pythonw.exe (senza console): se un import fallisce all'avvio,
il processo morirebbe in silenzio. Qui intercettiamo qualunque errore, lo
scriviamo in 'crash.log' e proviamo a mostrarlo in una finestra.
"""
import datetime
import os
import sys
import traceback


def _crash_log_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [here, os.path.join(os.path.expanduser("~"), "DOPAMINIC")]
    for base in candidates:
        try:
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, "crash.log")
        except Exception:
            continue
    return os.path.join(os.path.expanduser("~"), "lvs_crash.log")


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from app import main as app_main
        app_main()
    except Exception:
        tb = traceback.format_exc()
        try:
            with open(_crash_log_path(), "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now()} ---\n{tb}\n")
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror(
                "Errore di avvio",
                "L'app non e' riuscita a partire.\n\n"
                + tb[-1500:]
                + f"\n\nDettagli in:\n{_crash_log_path()}",
            )
            r.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
