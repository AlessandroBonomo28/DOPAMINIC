"""Installazione on-demand delle dipendenze opzionali (pesanti).

Le dipendenze core (moviepy, numpy, pillow) sono sempre presenti. Quelle
opzionali si installano solo quando l'utente attiva la funzione relativa:
  - OpenCV  -> face-tracking nel crop verticale
  - Whisper -> sottotitoli locali

Richiede un Python reale con pip (e' il caso dell'installer Inno Setup, che
imbarca un Python con pip). In un exe "congelato" pip non sarebbe disponibile.
"""
import importlib
import shutil
import subprocess
import sys
from typing import Callable, List, Optional

OPTIONAL = {
    "opencv": {"module": "cv2", "package": "opencv-python", "label": "OpenCV (face-tracking)"},
    "whisper": {"module": "faster_whisper", "package": "faster-whisper", "label": "Whisper (sottotitoli)"},
    "youtube": {
        "module": "googleapiclient",
        "package": "google-api-python-client google-auth-oauthlib google-auth-httplib2",
        "label": "YouTube uploader (Google API)",
    },
    "music": {"module": "pygame", "package": "pygame", "label": "Musica di sottofondo (pygame)"},
}

# Librerie CUDA per la GPU (ctranslate2 4.x -> CUDA 12 + cuDNN 9).
# Si installano via pip: niente CUDA Toolkit di sistema.
GPU_PACKAGES = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]

LogFn = Optional[Callable[[str], None]]


def is_installed(key: str) -> bool:
    """True se la dipendenza opzionale e' gia' importabile."""
    try:
        importlib.import_module(OPTIONAL[key]["module"])
        return True
    except ImportError:
        return False


def _pip_install(packages: List[str], log: LogFn = None) -> bool:
    """Esegue `pip install <packages>` nell'interprete corrente, inoltrando l'output a `log`."""
    if getattr(sys, "frozen", False):
        if log:
            log("[deps] Build congelata: impossibile installare a runtime.")
        return False

    cmd = [sys.executable, "-m", "pip", "install", *packages]
    if log:
        log(f"[deps] Installazione di {' '.join(packages)} (puo' richiedere qualche minuto)...")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line and log:
                log(line)
        proc.wait()
        importlib.invalidate_caches()
        return proc.returncode == 0
    except Exception as exc:  # noqa: BLE001
        if log:
            log(f"[deps] Errore: {exc}")
        return False


def install(key: str, log: LogFn = None) -> bool:
    """Installa la dipendenza opzionale (opencv/whisper/youtube) via pip. Ritorna True se ok."""
    ok = _pip_install(OPTIONAL[key]["package"].split(), log) and is_installed(key)
    if log:
        log("[deps] Completato." if ok else "[deps] Installazione fallita.")
    return ok


# ---------------------------------------------------------------- GPU (CUDA) ---

def has_nvidia_gpu() -> bool:
    """True se c'e' un driver NVIDIA (presenza di nvidia-smi)."""
    return shutil.which("nvidia-smi") is not None


def gpu_info() -> Optional[dict]:
    """Nome e VRAM totale della prima GPU NVIDIA, via nvidia-smi.

    Returns {"name": str, "total_mb": int} oppure None se assente/non leggibile.
    Non richiede librerie CUDA: basta il driver.
    """
    if not has_nvidia_gpu():
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip().splitlines()
        if not out:
            return None
        name, mem = out[0].split(",")
        return {"name": name.strip(), "total_mb": int(mem.strip())}
    except Exception:
        return None


def gpu_libs_installed() -> bool:
    """True se le librerie CUDA (cuBLAS/cuDNN) sono installate via pip."""
    try:
        importlib.import_module("nvidia.cublas")
        importlib.import_module("nvidia.cudnn")
        return True
    except ImportError:
        return False


def install_gpu(log: LogFn = None) -> bool:
    """Installa Whisper (se manca) + le librerie CUDA per la GPU."""
    if not is_installed("whisper"):
        if not install("whisper", log):
            return False
    ok = _pip_install(GPU_PACKAGES, log) and gpu_libs_installed()
    if log:
        log("[deps] GPU pronta." if ok else "[deps] Installazione GPU fallita.")
    return ok
