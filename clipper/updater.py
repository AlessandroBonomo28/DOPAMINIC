"""Controllo aggiornamenti via GitHub Releases (come fa Parabolic su Windows).

All'avvio l'app confronta APP_VERSION con l'ultima release del repo; se ce n'e'
una piu' nuova, scarica l'installer allegato alla release e lo lancia (upgrade
sul posto, grazie all'AppId fisso in app.iss). Tutto via HTTPS, niente git.
"""
import json
import os
import sys
import urllib.request

from . import APP_VERSION, TEMP_DIR, ensure_dirs

REPO = "AlessandroBonomo28/DOPAMINIC"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
_HEADERS = {"User-Agent": "DOPAMINIC-updater"}  # GitHub rifiuta richieste senza User-Agent


def _parse_version(s):
    """'v1.10.2' -> (1, 10, 2). Tollerante a prefissi e suffissi non numerici."""
    s = (s or "").strip().lstrip("vV")
    parts = []
    for chunk in s.split("."):
        num = ""
        for ch in chunk:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote, local) -> bool:
    return _parse_version(remote) > _parse_version(local)


def check_for_update(timeout=6):
    """Ritorna {version, url, page} se c'e' una release piu' nuova, altrimenti None.

    `url` e' il link diretto all'asset Setup.exe (None se la release non lo allega).
    Fallisce in silenzio (ritorna None) se offline, senza release o su errore.
    """
    try:
        req = urllib.request.Request(API_LATEST, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception:
        return None

    tag = data.get("tag_name") or data.get("name") or ""
    if not tag or not is_newer(tag, APP_VERSION):
        return None

    url = None
    for asset in data.get("assets", []):
        name = (asset.get("name") or "").lower()
        if name.endswith("setup.exe") or name.endswith(".exe"):
            url = asset.get("browser_download_url")
            break
    return {
        "version": tag.lstrip("vV"),
        "url": url,
        "page": data.get("html_url", RELEASES_PAGE),
    }


def list_releases(timeout=8, limit=30):
    """Elenco delle release (piu' recente prima) con changelog e asset .exe.

    Ogni voce: {version, tag, name, body, url, page, date, prerelease}.
    Ritorna [] se offline, repo privato o senza release.
    """
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases?per_page={limit}", headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception:
        return []
    out = []
    for rel in data:
        if rel.get("draft"):
            continue
        tag = rel.get("tag_name") or rel.get("name") or ""
        url = None
        for asset in rel.get("assets", []):
            name = (asset.get("name") or "").lower()
            if name.endswith("setup.exe") or name.endswith(".exe"):
                url = asset.get("browser_download_url")
                break
        out.append({
            "version": tag.lstrip("vV"),
            "tag": tag,
            "name": rel.get("name") or tag,
            "body": rel.get("body") or "",
            "url": url,
            "page": rel.get("html_url", RELEASES_PAGE),
            "date": (rel.get("published_at") or "")[:10],
            "prerelease": bool(rel.get("prerelease")),
        })
    return out


def download_path(version) -> str:
    ensure_dirs()
    safe = "".join(c for c in str(version) if c.isalnum() or c in "._-")
    return str(TEMP_DIR / f"DOPAMINIC-Setup-{safe}.exe")


def download(url, dest, progress=None, timeout=30) -> str:
    """Scarica `url` in `dest`. Chiama `progress(frazione 0..1)` durante. Ritorna dest."""
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if progress and total:
                    progress(min(1.0, got / total))
    return dest


def launch_installer(path) -> None:
    """Avvia l'installer scaricato (poi l'app si chiude per consentire l'upgrade)."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606  (Windows only)
    else:
        import subprocess
        subprocess.Popen([path])
