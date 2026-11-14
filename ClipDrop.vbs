' Starts ClipDrop without a black window. It lives in the tray by the clock.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
py = dir & "\runtime\python\pythonw.exe"
If Not fso.FileExists(py) Then py = "pythonw.exe"
sh.CurrentDirectory = dir
sh.Run """" & py & """ """ & dir & "\clipdrop.py""", 0, False
