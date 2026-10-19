; Writes one line per running AutoHotkey script ("<pid> | <script path> - AutoHotkey vX") to the file given as the first argument.
; run_compat.ps1 uses it to check that your own copy of AutoCorrect.ahk is running before testing English through it.
#NoEnv
#SingleInstance Off
DetectHiddenWindows, On
out := ""
WinGet, list, List, ahk_class AutoHotkey
Loop, %list%
{
    id := list%A_Index%
    WinGetTitle, t, ahk_id %id%
    WinGet, pid, PID, ahk_id %id%
    out .= pid . " | " . t . "`n"
}
FileDelete, %1%
FileAppend, %out%, %1%, UTF-8-RAW
ExitApp
