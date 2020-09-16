#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory. 

XButton1::send {Ctrl down}{LWin down}{left down}{Ctrl up}{LWin up}{left up} ; Remap forward mouse button to Ctrl+Win+L to shift left 1 virtual display
XButton2::send {Ctrl down}{LWin down}{right down}{Ctrl up}{LWin up}{right up} ; Remap back mouse button to Ctrl+Win+R to shift right 1 virtual display