; Types every line of the test file into a scratch window and saves what ended up there.
; Usage: type_test.ahk <tests.txt> <result.txt>
#NoEnv
#SingleInstance force
SetBatchLines, -1
SendMode Event
SetKeyDelay, 14, 14
SendLevel 1   ; lets other AutoHotkey scripts' hotstrings see this typing

testsFile = %1%
resultFile = %2%
FileRead, tests, %testsFile%
Gui, Add, Edit, vOut w900 r28 -Wrap
Gui, Show,, HinglishTest
WinWaitActive, HinglishTest,, 5
if ErrorLevel
{
    FileDelete, %resultFile%
    FileAppend, ABORT: window never became active, %resultFile%
    ExitApp
}
GuiControl, Focus, Out
Sleep, 600
Loop, Parse, tests, `n, `r
{
    if (A_LoopField = "")
        continue
    if !WinActive("HinglishTest")
    {
        FileDelete, %resultFile%
        FileAppend, ABORT: lost focus at test %A_Index%, %resultFile%
        ExitApp
    }
    SendRaw, %A_LoopField%
    Send, {Enter}
    Sleep, 25
}
Sleep, 800
GuiControlGet, txt,, Out
FileDelete, %resultFile%
FileAppend, %txt%, %resultFile%, UTF-8-RAW
ExitApp
