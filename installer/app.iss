; Inno Setup script per "DOPAMINIC"
; Compila con build.ps1 (consigliato) oppure aprendo questo file in Inno Setup.

#define MyAppName "DOPAMINIC"
#define MyAppVersion "1.2"
#define MyAppPublisher "Goodman"

[Setup]
; AppId STABILE: ogni Setup con versione piu' alta aggiorna l'installazione
; esistente (upgrade sul posto) invece di affiancarne una seconda.
AppId={#MyAppName}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Installazione per-utente (niente admin): cartella scrivibile in LocalAppData
DefaultDirName={localappdata}\Programs\DOPAMINIC
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=DOPAMINIC-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un'icona sul desktop"; GroupDescription: "Icone aggiuntive:"

[Files]
; Tutto lo staging: runtime/ (Python) + app.py + clipper/ + data/ + fonts/
Source: "stage\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\launch.py"""; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\launch.py"""; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\launch.py"""; WorkingDir: "{app}"; Description: "Avvia {#MyAppName}"; Flags: nowait postinstall skipifsilent
