; Types a few test words into an already open window, then copies everything in the box and saves it.
; Run by run_compat.ps1, which starts the autocorrect script first and checks the result afterwards.
;
; Usage: app_test.ahk <window title, e.g. "ahk_pid 1234"> <result file> <address bar: 0 or 1> <text to type> [enter]
;
;   address bar = 1 presses Ctrl+L first, so the words go into the browser's address bar
;   instead of the page.
;   The text is typed one word at a time, like a person would, with a space after each word.
#NoEnv
#SingleInstance Off
SetBatchLines, -1
SendMode Event
SetKeyDelay, 30, 30
SendLevel 1   ; lets other AutoHotkey scripts' hotstrings see this typing

winTitle = %1%
resultFile = %2%
addressBar = %3%
words = %4%
mode = %5%   ; "enter": press Enter right after the last word and report what the page received

Abort(msg)
{
    global resultFile
    FileDelete, %resultFile%
    FileAppend, ABORT: %msg%, %resultFile%, UTF-8-RAW
    ExitApp
}

WinWait, %winTitle%,, 45
if ErrorLevel
    Abort("window never appeared")
WinActivate, %winTitle%
WinWaitActive, %winTitle%,, 10
if ErrorLevel
    Abort("could not bring the window to the front")
Sleep, 2500   ; let the app finish starting and put the cursor in the text box

if (addressBar = 1)
{
    Send, ^l
    Sleep, 500
}

clipSaved := ClipboardAll   ; the user's own clipboard is put back at the end
Clipboard =
StringSplit, part, words, %A_Space%
Loop, %part0%
{
    if !WinActive(winTitle)
    {
        Clipboard := clipSaved
        WinGetTitle, nowTitle, A
        WinGet, nowExe, ProcessName, A
        WinGetClass, nowClass, A
        Abort("lost focus while typing (word " . A_Index . "; active window is now '" . nowTitle . "' / " . nowExe . " / " . nowClass . ")")
    }
    word := part%A_Index%
    SendRaw, %word%
    if (mode = "enter" and A_Index = part0)
        break   ; the last word is followed by Enter, not by a space
    Send, {Space}
    Sleep, 220
}

if (mode = "enter")
{
    ; Enter sends the box (see compat_enter.html). Read back what was sent from the window title.
    Sleep, 300
    Send, {Enter}
    Sleep, 2500
    WinGetTitle, sentTitle, %winTitle%
    Clipboard := clipSaved
    FileDelete, %resultFile%
    FileAppend, %sentTitle%, %resultFile%, UTF-8-RAW
    ExitApp
}
Sleep, 800
Send, ^a
Sleep, 200
Send, ^c
ClipWait, 3
copied := Clipboard
Clipboard := clipSaved

FileDelete, %resultFile%
FileAppend, %copied%, %resultFile%, UTF-8-RAW
ExitApp
