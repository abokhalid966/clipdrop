# ClipDrop installer: puts a private copy of Python and FFmpeg inside this
# folder (nothing is installed system-wide), adds shortcuts, and starts it.
# Safe to run again: it skips anything already done.
# The setup .exe runs this with -FromSetup (it makes the shortcuts itself).

param([switch]$FromSetup)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # makes downloads much faster
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$here    = $PSScriptRoot
$runtime = Join-Path $here 'runtime'
$pyDir   = Join-Path $runtime 'python'
$ffDir   = Join-Path $runtime 'ffmpeg'
$tmp     = Join-Path $runtime 'downloads'
$pyVer   = '3.12.10'

function Step($msg) { Write-Output ''; Write-Output "==> $msg" }

New-Item -ItemType Directory -Force -Path $runtime, $tmp | Out-Null

Write-Output 'ClipDrop setup: getting Python and FFmpeg (only the first time).'
Write-Output 'This takes a few minutes. Keep this window open.'

# ---- 1. Python (embedded, private to ClipDrop)
$py = Join-Path $pyDir 'python.exe'
if (-not (Test-Path $py)) {
    Step "Downloading Python $pyVer"
    $zip = Join-Path $tmp 'python.zip'
    Invoke-WebRequest "https://www.python.org/ftp/python/$pyVer/python-$pyVer-embed-amd64.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $pyDir -Force
    # let the embedded Python use installed packages
    $pth = Get-ChildItem $pyDir -Filter 'python*._pth' | Select-Object -First 1
    (Get-Content $pth.FullName) -replace '^#\s*import site', 'import site' | Set-Content $pth.FullName -Encoding ASCII
}

# ---- 2. pip + packages
$haveDeps = $false
if (Test-Path (Join-Path $pyDir 'Lib\site-packages\pystray')) {
    & $py -c "import soundcard, numpy, pystray, PIL" 2>$null
    $haveDeps = ($LASTEXITCODE -eq 0)
}
if (-not $haveDeps) {
    if (-not (Test-Path (Join-Path $pyDir 'Scripts\pip.exe'))) {
        Step 'Setting up pip'
        $gp = Join-Path $tmp 'get-pip.py'
        Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile $gp -UseBasicParsing
        & $py $gp --no-warn-script-location
        if ($LASTEXITCODE -ne 0) { throw 'Could not set up pip' }
    }
    Step 'Installing sound capture and tray icon packages'
    & $py -m pip install --no-warn-script-location --disable-pip-version-check --progress-bar off soundcard numpy pystray pillow
    if ($LASTEXITCODE -ne 0) { throw 'Could not install packages' }
}

# ---- 3. FFmpeg
if (-not (Test-Path (Join-Path $ffDir 'ffmpeg.exe'))) {
    Step 'Downloading FFmpeg (about 100 MB)'
    $zip = Join-Path $tmp 'ffmpeg.zip'
    Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $zip -UseBasicParsing
    $x = Join-Path $tmp 'ffmpeg'
    if (Test-Path $x) { Remove-Item $x -Recurse -Force }
    Expand-Archive $zip -DestinationPath $x -Force
    New-Item -ItemType Directory -Force -Path $ffDir | Out-Null
    Get-ChildItem $x -Recurse -Include 'ffmpeg.exe', 'ffprobe.exe' | Copy-Item -Destination $ffDir -Force
    if (-not (Test-Path (Join-Path $ffDir 'ffprobe.exe'))) { throw 'FFmpeg download looks broken' }
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
if ($FromSetup) { Write-Output ''; Write-Output 'Done.'; exit 0 }

# ---- 4. Shortcuts
Step 'Adding Start Menu and Desktop shortcuts'
$shell = New-Object -ComObject WScript.Shell
$targets = @(
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'ClipDrop.lnk'),
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'ClipDrop.lnk')
)
foreach ($t in $targets) {
    $lnk = $shell.CreateShortcut($t)
    $lnk.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
    $lnk.Arguments = '"' + (Join-Path $here 'ClipDrop.vbs') + '"'
    $lnk.WorkingDirectory = $here
    $lnk.IconLocation = (Join-Path $here 'web\icon.ico')
    $lnk.Description = 'ClipDrop game clipper'
    $lnk.Save()
}

# Explorer right-click > Send to > ClipDrop
$st = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('SendTo')) 'ClipDrop (send to phone).lnk'))
$st.TargetPath = Join-Path $pyDir 'pythonw.exe'
$st.Arguments = '"' + (Join-Path $here 'clipdrop.py') + '" --send'
$st.WorkingDirectory = $here
$st.IconLocation = (Join-Path $here 'web\icon.ico')
$st.Description = 'Send files to your phone with ClipDrop'
$st.Save()

# ---- 5. Clean up and start
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

Step 'Starting ClipDrop'
Write-Output 'Look for the orange icon by the clock. A QR code page opens for your iPhone.'
Write-Output 'If Windows asks about the firewall, tick PRIVATE networks and click Allow.'
Start-Process (Join-Path $env:WINDIR 'System32\wscript.exe') -ArgumentList ('"' + (Join-Path $here 'ClipDrop.vbs') + '"')
Start-Sleep -Seconds 4
