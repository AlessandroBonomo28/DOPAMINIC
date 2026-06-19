# Costruisce il pacchetto distribuibile (Opzione A):
#   - scarica un Python 3.11 "embeddable" (relocabile)
#   - vi inietta tkinter (l'embeddable non lo include) e pip
#   - installa le dipendenze CORE (no opencv/whisper: si installano on-demand)
#   - copia l'app e compila l'installer con Inno Setup
#
# Requisiti per il BUILD (solo sulla TUA macchina, non per l'amico):
#   - connessione internet
#   - Python 3.11 completo installato (serve per copiare i file di tkinter)
#   - Inno Setup 6  (https://jrsoftware.org/isdl.php)
#
# Uso:  powershell -ExecutionPolicy Bypass -File installer\build.ps1

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $PSScriptRoot "stage"
$runtime = Join-Path $stage "runtime"
$pyver = "3.11.9"

Write-Host "== Pulizia staging ==" -ForegroundColor Cyan
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

Write-Host "== Download Python $pyver embeddable ==" -ForegroundColor Cyan
$zip = Join-Path $stage "pyembed.zip"
Invoke-WebRequest "https://www.python.org/ftp/python/$pyver/python-$pyver-embed-amd64.zip" -OutFile $zip
Expand-Archive $zip -DestinationPath $runtime -Force
Remove-Item $zip

Write-Host "== Abilita site-packages e import locali (._pth) ==" -ForegroundColor Cyan
$pth = Get-ChildItem $runtime -Filter "python*._pth" | Select-Object -First 1
$lines = Get-Content $pth.FullName
$lines = $lines -replace '^#\s*import site', 'import site'
if ($lines -notcontains ".") { $lines += "." }
Set-Content $pth.FullName $lines

Write-Host "== Bootstrap pip ==" -ForegroundColor Cyan
$getpip = Join-Path $stage "get-pip.py"
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip
& "$runtime\python.exe" $getpip --no-warn-script-location
Remove-Item $getpip

Write-Host "== Inietta tkinter (assente nell'embeddable) ==" -ForegroundColor Cyan
# Prende i file da un Python 3.11 completo (quello del venv del progetto va bene)
$basePy = & (Join-Path $proj "env\Scripts\python.exe") -c "import sys; print(sys.base_prefix)"
if (-not (Test-Path $basePy)) {
    $basePy = & python -c "import sys; print(sys.base_prefix)"
}
Write-Host "   Python base: $basePy"
Copy-Item "$basePy\DLLs\_tkinter.pyd" $runtime -Force
Copy-Item "$basePy\DLLs\tcl86t.dll"  $runtime -Force
Copy-Item "$basePy\DLLs\tk86t.dll"   $runtime -Force
Copy-Item "$basePy\Lib\tkinter" (Join-Path $runtime "tkinter") -Recurse -Force
Copy-Item "$basePy\tcl" (Join-Path $runtime "tcl") -Recurse -Force
# sitecustomize: indica a tkinter dove sono le librerie Tcl/Tk a runtime
$site = @'
import os, sys
_root = os.path.dirname(sys.executable)
os.environ.setdefault("TCL_LIBRARY", os.path.join(_root, "tcl", "tcl8.6"))
os.environ.setdefault("TK_LIBRARY", os.path.join(_root, "tcl", "tk8.6"))
'@
Set-Content (Join-Path $runtime "sitecustomize.py") $site -Encoding UTF8

Write-Host "== Installa dipendenze CORE ==" -ForegroundColor Cyan
& "$runtime\python.exe" -m pip install --no-warn-script-location -r (Join-Path $proj "requirements.txt")

Write-Host "== Includi il runtime C++ (msvcp140 ecc.) app-local ==" -ForegroundColor Cyan
# numpy/pillow/opencv dipendono da MSVCP140.dll (e altre): NON sono nell'embeddable
# ne' garantite su un PC pulito. Le copiamo accanto a python.exe -> caricamento
# locale, niente VC++ Redistributable da installare, niente permessi admin.
$sys32 = Join-Path $env:SystemRoot "System32"
$vcdlls = @("msvcp140.dll","msvcp140_1.dll","msvcp140_2.dll","vcruntime140.dll",
            "vcruntime140_1.dll","vcomp140.dll","concrt140.dll")
foreach ($d in $vcdlls) {
    $src = Join-Path $sys32 $d
    if (Test-Path $src) { Copy-Item $src $runtime -Force; Write-Host "   + $d" }
}

Write-Host "== Pre-scarica ffmpeg (cosi' e' offline nel pacchetto) ==" -ForegroundColor Cyan
# imageio-ffmpeg di norma scarica il binario al primo uso: lo facciamo ora,
# cosi' finisce dentro il runtime e l'app funziona senza internet.
& "$runtime\python.exe" -c "import imageio_ffmpeg,os; p=imageio_ffmpeg.get_ffmpeg_exe(); print('ffmpeg ->', p, round(os.path.getsize(p)/1e6,1),'MB')"

Write-Host "== Copia file applicazione ==" -ForegroundColor Cyan
Copy-Item (Join-Path $proj "app.py") $stage -Force
Copy-Item (Join-Path $proj "launch.py") $stage -Force
Copy-Item (Join-Path $proj "manual.md") $stage -Force
Copy-Item (Join-Path $proj "soul.md") $stage -Force
Copy-Item (Join-Path $proj "manual_en.md") $stage -Force
Copy-Item (Join-Path $proj "soul_en.md") $stage -Force
# Asset opzionali (inclusi se presenti): avatar assistente + musica
foreach ($g in @("assistant.gif", "criceto.gif", "vibe.gif", "gotosleep.gif",
                 "sleep.png", "musica.mp3")) {
    $gsrc = Join-Path $proj $g
    if (Test-Path $gsrc) { Copy-Item $gsrc $stage -Force }
}
# Audio di default generati (effetti + fallback musica): default_*.wav
Get-ChildItem $proj -Filter "default_*.wav" -ErrorAction SilentlyContinue |
    ForEach-Object { Copy-Item $_.FullName $stage -Force }

# Icona app: da sleep.png (fallback assistant.gif). Usata dallo shortcut.
$iconSrc = if (Test-Path (Join-Path $proj "sleep.png")) { Join-Path $proj "sleep.png" }
           elseif (Test-Path (Join-Path $proj "assistant.gif")) { Join-Path $proj "assistant.gif" }
           else { $null }
if ($iconSrc) {
    Write-Host "== Genero icona da $iconSrc ==" -ForegroundColor Cyan
    & "$runtime\python.exe" -c "from PIL import Image; im=Image.open(r'$iconSrc').convert('RGBA'); im.save(r'$stage\icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
}
Copy-Item (Join-Path $proj "clipper") (Join-Path $stage "clipper") -Recurse -Force
Copy-Item (Join-Path $proj "data") (Join-Path $stage "data") -Recurse -Force
Copy-Item (Join-Path $proj "fonts") (Join-Path $stage "fonts") -Recurse -Force
# Rimuovi cache python
Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

Write-Host "== Compila installer (Inno Setup) ==" -ForegroundColor Cyan
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
    & $iscc (Join-Path $PSScriptRoot "app.iss")
    Write-Host "FATTO -> installer in installer\Output\" -ForegroundColor Green
} else {
    Write-Warning "Inno Setup non trovato. Installalo da https://jrsoftware.org/isdl.php"
    Write-Warning "oppure apri installer\app.iss in Inno Setup e premi Compile."
}
