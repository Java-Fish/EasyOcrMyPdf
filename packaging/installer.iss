; Inno-Setup-Beschreibung für OCRmyPDF GUI.
;
; Erzeugt ein Installationsprogramm, das die Anwendung nach
; "Programme\OCRmyPDF GUI" legt, Verknüpfungen anlegt und sich über
; "Apps & Features" wieder entfernen lässt.
;
; Bauen:  ISCC.exe packaging\installer.iss
; (setzt voraus, dass build_windows.ps1 zuvor dist\OCRmyPDF GUI erzeugt hat)

#define AppName "OCRmyPDF GUI"
#define AppVersion "1.0.0"
#define AppPublisher "OCRmyPDF GUI"
#define AppExeName "OCRmyPDF GUI.exe"

[Setup]
AppId={{7B2F4C1E-9A3D-4E56-8C71-2D9F5A6B3E14}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=OCRmyPDF-GUI-Setup
SetupIconFile=..\resources\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Ohne Administratorrechte installierbar, wenn der Nutzer keine hat.
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Die Anwendung im "Öffnen mit"-Menü von PDF-Dateien anbieten.
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExeName}\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; \
    Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; \
    ValueType: string; ValueName: "Applications\{#AppExeName}"; ValueData: ""; \
    Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent
