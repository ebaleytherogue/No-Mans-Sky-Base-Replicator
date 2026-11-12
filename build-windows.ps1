[CmdletBinding()]
param(
    [string]$Python,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('\Av?(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\z')]
    [string]$Version
)
$ErrorActionPreference = "Stop"

$releaseVersion = $Version -replace '^v', ''
$versionParts = $releaseVersion.Split('.')
foreach ($part in $versionParts) {
    if ([int]$part -gt [uint16]::MaxValue) {
        throw "Each version component must be between 0 and 65535."
    }
}
$windowsVersion = ($versionParts -join ', ') + ', 0'

Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not $PSBoundParameters.ContainsKey("Python")) {
        $Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
        if (!(Test-Path -LiteralPath $Python -PathType Leaf)) {
            throw "Repository Python was not found at '$Python'. From '$PSScriptRoot', run 'py -3.14 -m venv .venv', then install requirements-windows.txt, or pass a Windows x64 interpreter with -Python."
        }
    }
    if (!(Get-Command -Name $Python -CommandType Application -ErrorAction SilentlyContinue)) {
        throw "Python executable '$Python' could not be found. Pass a valid Windows x64 interpreter with -Python."
    }

    $pythonPlatform = & $Python -I -c "import sysconfig; print(sysconfig.get_platform())"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not check the target platform of '$Python' (exit code $LASTEXITCODE)."
    }
    if ([string]$pythonPlatform -ne "win-amd64") {
        throw "The Windows x64 portable build requires x64 Python. '$Python' reports '$pythonPlatform'. Pass a Windows x64 interpreter with -Python."
    }

    & $Python -I -c "import PyInstaller; import tkinter"
    if ($LASTEXITCODE -ne 0) {
        $requirements = Join-Path $PSScriptRoot "requirements-windows.txt"
        throw "Build dependencies are missing or could not be imported by '$Python' (exit code $LASTEXITCODE). In PowerShell, run: & '$Python' -m pip install -r '$requirements'"
    }

    $name = "NMS Base Replicator"
    New-Item -ItemType Directory -Path build -Force | Out-Null
    $versionFile = Join-Path $PSScriptRoot "build/$name-version.txt"
    @"
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=($windowsVersion),
        prodvers=($windowsVersion),
        mask=0x3F, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable('040904B0', [
                StringStruct('FileDescription', 'NMS Base Replicator'),
                StringStruct('FileVersion', '$releaseVersion'),
                StringStruct('ProductName', 'NMS Base Replicator'),
                StringStruct('ProductVersion', '$releaseVersion')
            ])
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)
"@ | Set-Content -LiteralPath $versionFile -Encoding ASCII

    & $Python -m PyInstaller --noconfirm --onedir --windowed --name $name --specpath build --version-file $versionFile wizard.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
    $bundle = "dist/$name"
    foreach ($required in @("$name.exe", "_internal/_tkinter.pyd", "_internal/_tcl_data/init.tcl", "_internal/_tk_data/tk.tcl")) {
        if (!(Test-Path -LiteralPath "$bundle/$required" -PathType Leaf)) {
            throw "Bundle is missing $required."
        }
    }
    $exeVersion = (Get-Item -LiteralPath "$bundle/$name.exe").VersionInfo
    if ($exeVersion.FileVersion -ne $releaseVersion -or $exeVersion.ProductVersion -ne $releaseVersion) {
        throw "The built EXE does not report the expected version '$releaseVersion'."
    }
    $guideFiles = @("Base_Replicator_Base_Templates.zip", "No-Mans-Sky-Base-Replicator_About_Mac_and_Linux.md")
    Copy-Item -LiteralPath (@("LICENSE") + $guideFiles) -Destination $bundle
    Copy-Item -LiteralPath README.md -Destination "$bundle/Windows-Quick-Start.md"
    Copy-Item -LiteralPath "Python Examples" -Destination $bundle -Recurse
    Copy-Item -LiteralPath (@("main.py", "replicator.py", "archive.py", "archive_ui.py", "wizard.py") + $guideFiles) -Destination "$bundle/Python Examples"
    Copy-Item -LiteralPath README.md -Destination "$bundle/Python Examples/README.md"
    Expand-Archive -LiteralPath Base_Replicator_Base_Templates.zip -DestinationPath "$bundle/Placeholder_Bases"
    & $Python -c "import sys; from pathlib import Path; from archive import discover_templates; discover_templates(Path(sys.argv[1]))" "$bundle/Placeholder_Bases"
    if ($LASTEXITCODE -ne 0) {
        throw "The bundled placeholder bases failed validation."
    }

    $zip = "dist/NMS-Base-Replicator-Windows-x64-Portable_v$releaseVersion.zip"
    Compress-Archive -LiteralPath $bundle -DestinationPath $zip -CompressionLevel Optimal -Force
    Write-Output (Get-Item -LiteralPath $zip).FullName
} finally {
    Pop-Location
}
