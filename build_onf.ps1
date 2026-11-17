$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$root = (Resolve-Path .).Path
$buildRoot = Join-Path $root "build\onf_verify"
$stageDist = Join-Path $buildRoot "dist"
$stageWork = Join-Path $buildRoot "work"
$stageExe = Join-Path $stageDist "ONF.exe"
$targetExe = Join-Path $root "dist\ONF.exe"
$python = Join-Path $root ".venv-build\Scripts\python.exe"
$smokeProfile = Join-Path $buildRoot "profile"
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
$env:PYINSTALLER_CONFIG_DIR = Join-Path $buildRoot "pyinstaller-config"

if (-not (Test-Path $python)) {
    & python -m venv (Join-Path $root ".venv-build")
    if ($LASTEXITCODE -ne 0) { throw "Could not create isolated build environment." }
}

& $python -m pip install --disable-pip-version-check -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Could not install pinned build dependencies." }

& $python -c "import cv2, importlib.metadata as m; from PySide6 import QtCore; assert QtCore.qVersion() == '6.11.1'; assert m.version('opencv-contrib-python') == '4.11.0.86'; assert 'opencv-python' not in {d.metadata['Name'].lower() for d in m.distributions()}; print('Qt', QtCore.qVersion(), '| OpenCV', cv2.__version__)"
if ($LASTEXITCODE -ne 0) { throw "The isolated Qt/OpenCV import check failed." }

$pythonBase = (& $python -c "import sys; print(sys.base_prefix)").Trim()
$env:PATH = @(
    (Join-Path $root ".venv-build\Scripts"),
    $pythonBase,
    (Join-Path $env:SystemRoot "System32"),
    $env:SystemRoot,
    (Join-Path $env:SystemRoot "System32\Wbem"),
    (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0")
) -join [IO.Path]::PathSeparator

$active = Get-Process -Name ONF -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $targetExe }
if ($active) { throw "Close the running dist\ONF.exe before building." }

New-Item -ItemType Directory -Force -Path $stageDist, $stageWork, $smokeProfile | Out-Null
& $python -m PyInstaller --noconfirm --clean --workpath $stageWork --distpath $stageDist build_onf.spec
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $stageExe)) { throw "PyInstaller failed; the existing executable is unchanged." }

$stagedHash = (Get-FileHash -LiteralPath $stageExe -Algorithm SHA256).Hash
$previousLocalAppData = $env:LOCALAPPDATA
$env:LOCALAPPDATA = $smokeProfile
$started = $false
try {
    Start-Process -FilePath $stageExe -WorkingDirectory $stageDist -WindowStyle Minimized | Out-Null
    $started = $true
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    $windowFound = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        $matching = Get-Process -Name ONF -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $stageExe }
        $errorWindow = $matching | Where-Object { $_.MainWindowTitle -match "Unhandled exception in script" }
        if ($errorWindow) { throw "The staged executable showed a startup exception window." }
        $mainWindow = $matching | Where-Object { $_.MainWindowTitle -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
        if ($mainWindow) {
            $windowFound = $true
            break
        }
        if (-not $matching) { throw "The staged executable exited before creating its main window." }
        Start-Sleep -Milliseconds 500
    }
    if (-not $windowFound) { throw "The staged executable did not create the expected QML window within 90 seconds." }
    Write-Host "Startup smoke test passed: $($mainWindow.MainWindowTitle)"
}
finally {
    $env:LOCALAPPDATA = $previousLocalAppData
    if ($started) {
        $stageProcesses = Get-Process -Name ONF -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $stageExe }
        if ($stageProcesses) {
            $stageProcesses | Stop-Process -Force
            Start-Sleep -Seconds 2
        }
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path $targetExe) | Out-Null
$backupExe = Join-Path $buildRoot ("ONF.rollback." + [Guid]::NewGuid().ToString("N") + ".exe")
if (Test-Path $targetExe) {
    [System.IO.File]::Replace($stageExe, $targetExe, $backupExe, $true)
} else {
    [System.IO.File]::Move($stageExe, $targetExe)
}

$deployedHash = (Get-FileHash -LiteralPath $targetExe -Algorithm SHA256).Hash
if ($deployedHash -ne $stagedHash) {
    if (Test-Path $backupExe) {
        $failedExe = Join-Path $buildRoot ("ONF.failed." + [Guid]::NewGuid().ToString("N") + ".exe")
        [System.IO.File]::Replace($backupExe, $targetExe, $failedExe, $true)
        Remove-Item -LiteralPath $failedExe -Force
    }
    throw "The deployed executable hash differs from the tested build; rollback attempted."
}

if (Test-Path $backupExe) { Remove-Item -LiteralPath $backupExe -Force }
Write-Host "Deployed: $targetExe"
Write-Host "SHA-256:  $deployedHash"
