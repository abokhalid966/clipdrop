; ClipDrop setup — build with:  makensis setup.nsi   (from this folder)
; Installs for the current user only, so it never needs admin rights.

Unicode true
!define APP "ClipDrop"
!ifndef VERSION
  !define VERSION "5.1"
!endif
!define UNKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP}"
!ifndef OUTDIR
  !define OUTDIR "."
!endif

Name "${APP}"
OutFile "${OUTDIR}\ClipDrop-Setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP}"
InstallDirRegKey HKCU "${UNKEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show
BrandingText "${APP} ${VERSION}"

VIProductVersion "${VERSION}.0.0"
VIAddVersionKey "ProductName" "${APP}"
VIAddVersionKey "FileDescription" "${APP} setup"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "Free to use and share"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Var IsUpdate

!define MUI_ICON "web\icon.ico"
!define MUI_UNICON "web\icon.ico"
!define MUI_ABORTWARNING

!define MUI_WELCOMEPAGE_TITLE "Welcome to ClipDrop"
!define MUI_WELCOMEPAGE_TEXT "ClipDrop keeps the last moments of your games. Press a hotkey to save a clip, then watch, edit and send it to your phone over your home Wi-Fi. You can also send any file between your PC and your phone.$\r$\n$\r$\nThe first time, setup downloads Python and FFmpeg (about 150 MB) into the ClipDrop folder. Nothing else on your PC is changed, and you don't need admin rights.$\r$\n$\r$\nIf ClipDrop is already installed, this updates it and keeps your settings and clips."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!define MUI_COMPONENTSPAGE_SMALLDESC
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "ClipDrop is ready"
!define MUI_FINISHPAGE_TEXT "ClipDrop runs as a small green icon by the clock.$\r$\n$\r$\nPress Ctrl+F9 in a game to save the last 30 seconds.$\r$\n$\r$\nWhen it starts, a QR code opens: scan it with your phone to connect. If Windows asks about the firewall, tick Private networks and click Allow."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Start ClipDrop now"
!define MUI_FINISHPAGE_RUN_FUNCTION StartApp
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; Stop a running ClipDrop (and its FFmpeg) so files can be replaced
!macro StopClipDrop
  DetailPrint "Closing ClipDrop if it's running..."
  nsExec::ExecToLog `powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($$_.CommandLine -like '*clipdrop.py*') -or ($$_.ExecutablePath -like '$INSTDIR\runtime\*') } | ForEach-Object { Invoke-CimMethod -InputObject $$_ -MethodName Terminate | Out-Null }"`
  Pop $0
  Sleep 800
!macroend

Function StartApp
  Exec '"$WINDIR\System32\wscript.exe" "$INSTDIR\ClipDrop.vbs"'
FunctionEnd

Section "ClipDrop (required)" SecApp
  SectionIn RO
  !insertmacro StopClipDrop
  SetOutPath "$INSTDIR"
  File "clipdrop.py"
  File "recorder.py"
  File "winutil.py"
  File "ClipDrop.vbs"
  File "install.ps1"
  File "start.bat"
  File "README.md"
  SetOutPath "$INSTDIR\web"
  File "web\app.html"
  File "web\help.html"
  File "web\shortcut.html"
  File "web\icon.png"
  File "web\icon180.png"
  File "web\icon.ico"
  File "web\i18n.js"
  File "web\help.ar.html"
  File "web\shortcut.ar.html"
  SetOutPath "$INSTDIR"

  DetailPrint "Getting Python and FFmpeg (skipped if you already have them)..."
  nsExec::ExecToLog 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install.ps1" -FromSetup'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION|MB_RETRYCANCEL "Setup couldn't download everything it needs (error $0).$\r$\n$\r$\nCheck your internet connection and click Retry." /SD IDCANCEL IDRETRY retry
    Abort "Download failed. Run the setup again when you're online."
    retry:
    nsExec::ExecToLog 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install.ps1" -FromSetup'
    Pop $0
    ${If} $0 != 0
      Abort "Download failed again. Run the setup again later."
    ${EndIf}
  ${EndIf}

  ; Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\${APP}"
  CreateShortcut "$SMPROGRAMS\${APP}\ClipDrop.lnk" "$WINDIR\System32\wscript.exe" '"$INSTDIR\ClipDrop.vbs"' "$INSTDIR\web\icon.ico" 0 SW_SHOWNORMAL "" "Record and send game clips"
  CreateShortcut "$SMPROGRAMS\${APP}\ClipDrop (show messages).lnk" "$INSTDIR\start.bat" "" "$INSTDIR\web\icon.ico" 0 SW_SHOWNORMAL "" "Run ClipDrop with a window that shows messages"
  CreateShortcut "$SMPROGRAMS\${APP}\Uninstall ClipDrop.lnk" "$INSTDIR\Uninstall ClipDrop.exe"
  ; Explorer right-click > Send to > ClipDrop (send to phone)
  CreateShortcut "$SENDTO\ClipDrop (send to phone).lnk" "$INSTDIR\runtime\python\pythonw.exe" '"$INSTDIR\clipdrop.py" --send' "$INSTDIR\web\icon.ico" 0 SW_SHOWNORMAL "" "Send files to your phone with ClipDrop"
  ; the old installer put one directly in Programs
  Delete "$SMPROGRAMS\ClipDrop.lnk"

  ; Installed apps entry
  WriteUninstaller "$INSTDIR\Uninstall ClipDrop.exe"
  WriteRegStr HKCU "${UNKEY}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${UNKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNKEY}" "Publisher" "${APP}"
  WriteRegStr HKCU "${UNKEY}" "DisplayIcon" "$INSTDIR\web\icon.ico"
  WriteRegStr HKCU "${UNKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNKEY}" "UninstallString" '"$INSTDIR\Uninstall ClipDrop.exe"'
  WriteRegDWORD HKCU "${UNKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNKEY}" "NoRepair" 1
  WriteRegDWORD HKCU "${UNKEY}" "EstimatedSize" 250000
SectionEnd

Section "Desktop shortcut" SecDesktop
  CreateShortcut "$DESKTOP\ClipDrop.lnk" "$WINDIR\System32\wscript.exe" '"$INSTDIR\ClipDrop.vbs"' "$INSTDIR\web\icon.ico" 0 SW_SHOWNORMAL "" "Record and send game clips"
SectionEnd

Section /o "Start ClipDrop with Windows" SecStartup
  FileOpen $1 "$SMSTARTUP\ClipDrop.vbs" w
  FileWrite $1 'CreateObject("WScript.Shell").Run """$INSTDIR\ClipDrop.vbs""", 0$\r$\n'
  FileClose $1
SectionEnd

; Started by ClipDrop's updater:  ClipDrop-Setup.exe /S /UPDATE /D=<folder>
; Keeps your shortcut choices and starts ClipDrop again when done.
Function .onInit
  StrCpy $IsUpdate 0
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/UPDATE" $R1
  ${IfNot} ${Errors}
    StrCpy $IsUpdate 1
    SectionSetFlags ${SecDesktop} 0
    SectionSetFlags ${SecStartup} 0
  ${EndIf}
FunctionEnd

Function .onInstSuccess
  ${If} $IsUpdate == 1
    Call StartApp
  ${EndIf}
FunctionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecApp} "The app itself, plus Python and FFmpeg (downloaded the first time)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Put a ClipDrop icon on your Desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "ClipDrop starts quietly by the clock when you turn on your PC. You can change this later in Settings."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  !insertmacro StopClipDrop
  Delete "$SMSTARTUP\ClipDrop.vbs"
  Delete "$DESKTOP\ClipDrop.lnk"
  Delete "$SENDTO\ClipDrop (send to phone).lnk"
  RMDir /r "$SMPROGRAMS\${APP}"
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\web"
  Delete "$INSTDIR\*.py"
  Delete "$INSTDIR\ClipDrop.vbs"
  Delete "$INSTDIR\install.ps1"
  Delete "$INSTDIR\start.bat"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\settings.json"
  Delete "$INSTDIR\Uninstall ClipDrop.exe"
  RMDir /r "$INSTDIR\__pycache__"
  RMDir "$INSTDIR"
  RMDir /r "$LOCALAPPDATA\ClipDrop"
  DeleteRegKey HKCU "${UNKEY}"
  MessageBox MB_ICONINFORMATION "ClipDrop is removed. Your clips (Videos\ClipDrop) and shared files (Downloads\ClipDrop Shared) are still there."
SectionEnd
