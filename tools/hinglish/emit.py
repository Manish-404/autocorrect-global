#!/usr/bin/env python3
"""Write AutoCorrectHinglish.ahk from final.json (made by build.py)."""
import json, pathlib, sys, collections, datetime

ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent.parent / 'AutoCorrectHinglish.ahk'
d = json.loads((ROOT / 'final.json').read_text(encoding='utf-8'))
stats = json.loads((ROOT / 'stats.json').read_text(encoding='utf-8'))
order = stats['sections']

ON_KINDS = ['cur-on', 'typo-transposed', 'typo-omitted']
n_on = sum(len(d.get(k, [])) for k in ON_KINDS)
n_off = sum(len(v) for k, v in d.items() if k not in ON_KINDS)

RULE = ';' + '-' * 78


def title(text, n=None):
    t = f'; {text}' + (f'  ({n:,} entries)' if n is not None else '')
    return [RULE, t, RULE]


def lines_for(rows):
    out = []
    last = None
    for c, a, _ in sorted(rows, key=lambda r: (r[0], r[1])):
        ch = c[0]
        if ch != last:
            out.append(f'; --- {ch} ---')
            last = ch
        out.append(f'::{a}::{c}')
    return out


def plain_lines(rows):
    return [f'::{a}::{c}' for c, a, _ in sorted(rows, key=lambda r: (r[0], r[1]))]


HEADER = f""";------------------------------------------------------------------------------
; INTRODUCTION
;
; AutoCorrect for HINGLISH: Hindi written in English letters (nahi, kya, kuch ...).
; Companion to AutoCorrect.ahk (English) and AutoCorrectHindi.ahk (Devanagari).
; Run them side by side. Each one only touches its own language.
;
; Hinglish has no official spelling, so this file does NOT try to force one.
; Spellings that people really use (kyu / kyun, acha / accha, pani / paani,
; jyada / zyada ...) are left alone. What it fixes:
;
;   ON by default
;   1. Chat shorthand  - words typed without their vowels:
;                        nhi -> nahi, mjhe -> mujhe, krna -> karna, rha -> raha ...
;   2. Swapped letters - kuhc -> kuch, bhaiay -> bhaiya
;   3. A missing letter inside a longer word - muhse -> mujhse, faurn -> fauran
;
;   OFF by default (the /* ... */ block near the end of this file)
;   4. Alternate spellings - nahee -> nahi, nahii -> nahi, muje -> mujhe ...
;   5. Stretched endings   - tumharaa -> tumhara, humey -> hume ...
;   To switch them on, delete the /* line and the */ line around the block.
;   To use only some, copy those lines above the block.
;
; THE NUMBERS
;
;   About {stats['valid_words']:,} Hinglish words are known to this file (names, places and verb
;   forms included). {n_on:,} corrections are ON and {n_off:,} are OFF.
;
; HOW WRONG CORRECTIONS WERE KEPT OUT
;
;   Every correction was checked, and dropped if it:
;   * is itself a real word in this file's word list (so kam / kaam, par / paar,
;     baar / bahar, pata / paata are never mixed up)
;   * is an English word (so "ache", "pure", "fool", "sham" stay as typed)
;   * could mean two different words (karog may be karoge or karogi: not guessed)
;   * is only one letter away from a different known word
;   * swaps the letters of a 4-letter word that is not one of the very common ones
;     (short words sit next to too many real words, e.g. abbu / babu)
;   * would also fire in AutoCorrect.ahk (two scripts must never both rewrite a word)
;   Matching ignores case and keeps your capitals: Nhi -> Nahi, NHI -> NAHI.
;
; IF A CORRECTION EVER CHANGES A WORD YOU MEANT
;
;   Delete that one line. Spellings of names are not guessed, so a name that looks
;   like a typo (for example Bhaiay) can be removed the same way.
;
; ADDING YOUR OWN
;
;   Select a word, press Win+Alt+H, and type the correction. It is added at the
;   very bottom of this file and the script reloads. (Win+H is English and
;   Win+Shift+H is Hindi, so each language keeps its own list.)
;
; REQUIREMENTS AND LIMITS
;
;   * AutoHotkey v1.1 (like the other two scripts).
;   * Corrections fire when you press space, Enter or punctuation after the word.
;   * Some input boxes do not accept replacement text from AutoHotkey (the Chrome
;     address bar and some chat boxes inside VS Code, for example). That is the
;     same for all three scripts.
;
; CONTENTS
;
;   Settings
;   Win+Alt+H code
;   ON:  Chat shorthand
;   ON:  Swapped letters
;   ON:  Missing letter inside a word
;   OFF: Alternate spellings, stretched endings (commented out)
;------------------------------------------------------------------------------

;------------------------------------------------------------------------------
; Settings
;------------------------------------------------------------------------------
#NoEnv ; For security
#SingleInstance force


;------------------------------------------------------------------------------
; Win+Alt+H to enter your own correction.  It will be added to this script.
;------------------------------------------------------------------------------
#!h::
; Get the selected text. The clipboard is used instead of "ControlGet Selected"
; as it works in more editors and word processors, java apps, etc. Save the
; current clipboard contents to be restored later.
AutoTrim Off  ; Retain any leading and trailing whitespace on the clipboard.
ClipboardOld = %ClipboardAll%
Clipboard =  ; Must start off blank for detection to work.
Send ^c
ClipWait 1
if ErrorLevel  ; ClipWait timed out.
    return
; Replace CRLF and/or LF with `n for use in a "send-raw" hotstring:
; The same is done for any other characters that might otherwise
; be a problem in raw mode:
StringReplace, Hotstring, Clipboard, ``, ````, All  ; Do this replacement first to avoid interfering with the others below.
StringReplace, Hotstring, Hotstring, `r`n, ``r, All  ; Using `r works better than `n in MS Word, etc.
StringReplace, Hotstring, Hotstring, `n, ``r, All
StringReplace, Hotstring, Hotstring, %A_Tab%, ``t, All
StringReplace, Hotstring, Hotstring, `;, ```;, All
Clipboard = %ClipboardOld%  ; Restore previous contents of clipboard.
; This will move the InputBox's caret to a more friendly position:
SetTimer, MoveCaret, 10
; Show the InputBox, providing the default hotstring:
InputBox, Hotstring, New Hinglish Hotstring, Provide the corrected word on the right side. You can also edit the left side if you wish.`n`nExample entry:`n::nhi::nahi,,,,,,,, ::%Hotstring%::%Hotstring%

if ErrorLevel <> 0  ; The user pressed Cancel.
    return
; Otherwise, add the hotstring and reload the script:
FileAppend, `n%Hotstring%, %A_ScriptFullPath%, UTF-8
Reload
Sleep 200 ; If successful, the reload will close this instance during the Sleep, so the line below will never be reached.
MsgBox, 4,, The hotstring just added appears to be improperly formatted.  Would you like to open the script for editing? Note that the bad hotstring is at the bottom of the script.
IfMsgBox, Yes, Edit
return

MoveCaret:
IfWinNotActive, New Hinglish Hotstring
    return
; Otherwise, move the InputBox's insertion point to where the user will type the abbreviation.
Send {{HOME}}
Loop % StrLen(Hotstring) + 4
    SendInput {{Right}}
SetTimer, MoveCaret, Off
return

#Hotstring R  ; Set the default to be "raw mode".

"""

FOOTER = """
;-------------------------------------------------------------------------------
; Anything below this point was added to the script by the user via the Win+Alt+H hotkey.
;-------------------------------------------------------------------------------
"""


def main():
    out = [HEADER]

    # ---- ON: chat shorthand, by lexicon section
    by_sec = collections.OrderedDict((s, []) for s in order)
    for row in d.get('cur-on', []):
        by_sec.setdefault(row[2], []).append(row)
    out += title('ON: CHAT SHORTHAND (words typed without vowels)', len(d.get('cur-on', [])))
    for sec, rows in by_sec.items():
        if rows:
            out.append(f'; {sec}')
            out += plain_lines(rows)
            out.append('')

    # ---- ON: typos
    rows = d.get('typo-transposed', [])
    out += title('ON: SWAPPED LETTERS (two neighbouring letters typed in the wrong order)', len(rows))
    out += lines_for(rows)
    out.append('')
    rows = d.get('typo-omitted', [])
    out += title('ON: MISSING LETTER INSIDE A WORD', len(rows))
    out += lines_for(rows)
    out.append('')

    # ---- OFF block
    out += title('OFF: ALTERNATE SPELLINGS AND STRETCHED ENDINGS (commented out)', n_off)
    out.append('; These are real spellings that many people use, so they are not applied by default.')
    out.append('; Delete the /* line below and the */ line at the end of this block to switch them all on.')
    out.append('/*')
    alt = collections.OrderedDict((s, []) for s in order)
    for row in d.get('cur-alt', []):
        alt.setdefault(row[2], []).append(row)
    first = True
    for sec, rows in alt.items():
        if rows:
            out.append(f'; Alternate spellings: {sec}')
            out += plain_lines(rows)
            out.append('')
    rows = d.get('rule-style', [])
    out.append(f'; Alternate spellings by pattern: aa/a, ee/i, oo/u, w/v, z/j, ph/f, ai/e  ({len(rows):,} entries)')
    out += lines_for(rows)
    out.append('')
    rows = d.get('rule-elong', [])
    out.append(f'; Stretched endings: kyaa, thaa, nahee, merey ...  ({len(rows):,} entries)')
    out += lines_for(rows)
    out.append('*/')
    out.append(FOOTER)
    text = '\n'.join(out)
    # AutoHotkey v1 reads a UTF-8 file correctly only with a BOM; the content is plain ASCII.
    OUT.write_text(text, encoding='utf-8-sig', newline='\r\n')
    print(f'wrote {OUT}  ({OUT.stat().st_size:,} bytes, {n_on:,} on, {n_off:,} off)')


if __name__ == '__main__':
    main()
