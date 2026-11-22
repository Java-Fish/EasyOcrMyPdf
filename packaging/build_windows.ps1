<#
.SYNOPSIS
    Baut "OCRmyPDF GUI.exe" und optional ein Installationsprogramm.

.DESCRIPTION
    Aufruf in der PowerShell aus dem Projektverzeichnis:

        .\packaging\build_windows.ps1                 # nur die .exe
        .\packaging\build_windows.ps1 -Vendor         # Tesseract/Ghostscript mitliefern
        .\packaging\build_windows.ps1 -Installer      # zusätzlich Setup.exe (Inno Setup)

    Das Ergebnis liegt unter dist\.
#>
[CmdletBinding()]
param(
    [switch]$Vendor,
    [switch]$Installer
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$AppName = "OCRmyPDF GUI"
$Venv = ".venv"

# --- Virtuelle Umgebung vorbereiten ---------------------------------------
if (-not (Test-Path $Venv)) {
    Write-Host "==> Creating virtual environment"
    python -m venv $Venv
}
$Python = Join-Path $Venv "Scripts\python.exe"

Write-Host "==> Installing dependencies"
& $Python -m pip install --quiet --upgrade pip
& $Python -m pip install --quiet -r requirements.txt -r requirements-build.txt

# --- Symbole erzeugen ------------------------------------------------------
Write-Host "==> Generating icons"
& $Python tools\make_icons.py

# --- Optional: Tesseract und Ghostscript mitliefern ------------------------
if ($Vendor) {
    Write-Host "==> Bundling Tesseract and Ghostscript"
    & $Python tools\vendor_windows.py
} else {
    # Ohne diese Variable bände die Spec einen aus einem früheren Lauf
    # übriggebliebenen vendor-Ordner stillschweigend mit ein.
    $env:OCRMYPDF_GUI_NO_VENDOR = "1"
}

# --- Bauen -----------------------------------------------------------------
Write-Host "==> Building the application"
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\$AppName") { Remove-Item -Recurse -Force "dist\$AppName" }
& $Python -m PyInstaller packaging\ocrmypdf_gui.spec --noconfirm --distpath dist --workpath build

$ExePath = "dist\$AppName\$AppName.exe"
if (-not (Test-Path $ExePath)) {
    throw "Build failed: $ExePath was not created"
}

# --- Optional: Installationsprogramm mit Inno Setup ------------------------
if ($Installer) {
    Write-Host "==> Creating the installer"
    $InnoCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    $Inno = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Inno) {
        Write-Warning ("Inno Setup was not found. Install it first:`n" +
                       "    winget install -e --id JRSoftware.InnoSetup")
    } else {
        & $Inno "packaging\installer.iss"
        Write-Host "    dist\OCRmyPDF-GUI-Setup.exe"
    }
}

# --- Prüfsummen ------------------------------------------------------------
Write-Host "==> Writing checksums"
& $Python tools\make_checksums.py | Out-Null
Write-Host "    dist\sha.txt"

$Size = "{0:N0} MB" -f ((Get-ChildItem "dist\$AppName" -Recurse -File |
        Measure-Object -Property Length -Sum).Sum / 1MB)
Write-Host ""
Write-Host "Done: $ExePath ($Size)"
Write-Host "Start it with a double-click, or build the installer with -Installer."
