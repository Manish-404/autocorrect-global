;------------------------------------------------------------------------------
; INTRODUCTION
;
; Hindi (Devanagari) companion to AutoCorrect.ahk. Run both scripts side by
; side: AutoCorrect.ahk fixes English, this one fixes Hindi.
;
; Same idea as the English list: only words that are clearly misspelled are
; corrected. Spellings that are matters of standard vs. common usage
; (महत्व/महत्त्व, गये/गए, ...) are at the end of this file, commented out, so
; you can enable the ones you agree with.
;
; Win+Shift+H adds your own correction for the selected word (Win+H is already
; used by AutoCorrect.ahk). New entries are appended to the end of this file.
;
; REQUIREMENTS
;
; * Keep this file saved as "UTF-8 with BOM". Without the BOM, AutoHotkey v1
;   reads it as ANSI and none of the Devanagari hotstrings will match.
;   (VS Code shows the encoding in the status bar and keeps the BOM on save.)
; * Type Hindi with a keyboard layout such as Windows' "Hindi Traditional"
;   (INSCRIPT), which sends one keystroke per character. Transliteration IMEs
;   (Google Input Tools, Microsoft Hindi Phonetic) compose text before handing
;   it over, so AutoHotkey usually never sees the letters and nothing fires.
; * Nukta letters (क़ ख़ ग़ ज़ ड़ ढ़ फ़) are written as letter + ़ (U+093C),
;   which is what Windows keyboards type.
;
; NOTES
;
; * Windows does not count matras, virama, anusvara or nukta as letters, so a
;   hotstring can also fire when its word is typed straight after one of them
;   (e.g. inside a longer word). Entries below were chosen so this either
;   cannot happen in real words or still produces the right spelling. Check
;   this when adding short entries, and avoid ones ending in common verb
;   endings such as -ती / -ता (e.g. "गती" would break भागती, मांगती).
; * Some -ी endings corrected here (शक्ती, रात्री, परिस्थिती, ...) are correct
;   in Marathi. Disable those if you also type Marathi.
;
; CONTENTS
;
;   Settings
;   Win+Shift+H code
;   Fixes anywhere in a word
;   Word endings
;   Common misspellings - the main list
;   Ambiguous / prescriptive entries - commented out
;------------------------------------------------------------------------------

;------------------------------------------------------------------------------
; Settings
;------------------------------------------------------------------------------
#NoEnv ; For security
#SingleInstance force
; Default end characters plus the Hindi full stops (danda) । and ॥.
#Hotstring EndChars -()[]{}:;'"/\,.?!`n `t।॥


;------------------------------------------------------------------------------
; Win+Shift+H to enter misspelling correction.  It will be added to this script.
;------------------------------------------------------------------------------
#+h::
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
InputBox, Hotstring, New Hindi Hotstring, Provide the corrected word on the right side. You can also edit the left side if you wish.`n`nExample entry:`n::नही::नहीं,,,,,,,, ::%Hotstring%::%Hotstring%

if ErrorLevel <> 0  ; The user pressed Cancel.
    return
; Otherwise, add the hotstring and reload the script. UTF-8 keeps the
; Devanagari text intact (the file already has its BOM, so none is added).
FileAppend, `n%Hotstring%, %A_ScriptFullPath%, UTF-8
Reload
Sleep 200 ; If successful, the reload will close this instance during the Sleep, so the line below will never be reached.
MsgBox, 4,, The hotstring just added appears to be improperly formatted.  Would you like to open the script for editing? Note that the bad hotstring is at the bottom of the script.
IfMsgBox, Yes, Edit
return

MoveCaret:
IfWinNotActive, New Hindi Hotstring
    return
; Otherwise, move the InputBox's insertion point to where the user will type the abbreviation.
Send {HOME}
Loop % StrLen(Hotstring) + 4
    SendInput {Right}
SetTimer, MoveCaret, Off
return

#Hotstring R  ; Set the default to be "raw mode".


;------------------------------------------------------------------------------
; Fixes anywhere in a word (fire immediately, no end character needed)
;------------------------------------------------------------------------------
:?*:ध्द::द्ध  ; Swapped conjunct: श्रध्दा, शुध्द, सिध्द, युध्द -> श्रद्धा, शुद्ध, सिद्ध, युद्ध


;------------------------------------------------------------------------------
; Word endings
;------------------------------------------------------------------------------
; ई becomes इ before य in plurals: भाईयों -> भाइयों, मिठाईयाँ -> मिठाइयाँ
:?:ईयाँ::इयाँ
:?:ईयां::इयां
:?:ईयों::इयों


;------------------------------------------------------------------------------
; Common Misspellings - the main list
;------------------------------------------------------------------------------

; Words ending in short ि written with long ी
::अतिथी::अतिथि
::तिथी::तिथि
::विधी::विधि
::निधी::निधि
::प्रतिनिधी::प्रतिनिधि
::कवी::कवि
::मुनी::मुनि
::ऋषी::ऋषि
::हानी::हानि
::ध्वनी::ध्वनि
::अग्नी::अग्नि
::रात्री::रात्रि
::लिपी::लिपि
::प्रतिलिपी::प्रतिलिपि
::संधी::संधि
::रुची::रुचि
::रूची::रुचि
::रूचि::रुचि
::अभिरुची::अभिरुचि
::पद्धती::पद्धति
::प्रगती::प्रगति
::नीती::नीति
::राजनीती::राजनीति
::प्रकृती::प्रकृति
::संस्कृती::संस्कृति
::स्थिती::स्थिति
::परिस्थिती::परिस्थिति
::उपस्थिती::उपस्थिति
::स्वीकृती::स्वीकृति
::आकृती::आकृति
::कृती::कृति
::जागृती::जागृति
::शांती::शांति
::शान्ती::शान्ति
::क्रांती::क्रांति
::सम्मती::सम्मति
::अनुमती::अनुमति
::आपत्ती::आपत्ति
::संपत्ती::संपत्ति
::सम्पत्ती::सम्पत्ति
::उत्पत्ती::उत्पत्ति
::व्यक्ती::व्यक्ति
::अभिव्यक्ती::अभिव्यक्ति
::शक्ती::शक्ति
::भक्ती::भक्ति
::मुक्ती::मुक्ति
::युक्ती::युक्ति
::नियुक्ती::नियुक्ति
::बुद्धी::बुद्धि
::सिद्धी::सिद्धि
::वृद्धी::वृद्धि
::शुद्धी::शुद्धि
::समृद्धी::समृद्धि
::प्राप्ती::प्राप्ति
::पूर्ती::पूर्ति
::मूर्ती::मूर्ति
::कीर्ती::कीर्ति
::सृष्टी::सृष्टि
::दृष्टी::दृष्टि
::पुष्टी::पुष्टि
::संतुष्टी::संतुष्टि
::प्रवृत्ती::प्रवृत्ति
::निवृत्ती::निवृत्ति
::सेवानिवृत्ती::सेवानिवृत्ति
::आवृत्ती::आवृत्ति
::उन्नती::उन्नति
::राष्ट्रपती::राष्ट्रपति
::उपराष्ट्रपती::उपराष्ट्रपति
::सभापती::सभापति
::इत्यादी::इत्यादि
::यद्यपी::यद्यपि
::तथापी::तथापि
::कदापी::कदापि

; Short ु / long ू mixed up
::पुरूष::पुरुष
::रूपया::रुपया
::रूपये::रुपये
::रूपए::रुपए
::गुरू::गुरु
::कृपालू::कृपालु
::दयालू::दयालु
::आयू::आयु
::वायू::वायु
::साधू::साधु
::प्रभू::प्रभु
::शत्रू::शत्रु
::वस्तू::वस्तु
::हेतू::हेतु
::पशू::पशु
::मृत्यू::मृत्यु
::हिन्दु::हिन्दू
::हिंदु::हिंदू
::शुरु::शुरू
::जरुरी::जरूरी
::ज़रुरी::ज़रूरी
::जरुरत::जरूरत
::ज़रुरत::ज़रूरत
::खुबसूरत::खूबसूरत
::खूबसुरत::खूबसूरत
::खुबसुरत::खूबसूरत
::अनुभुति::अनुभूति
::सहानुभुति::सहानुभूति
::सहानभूति::सहानुभूति
::भुमिका::भूमिका
::भुगोल::भूगोल
::बहोत::बहुत
::बहूत::बहुत
::सुचना::सूचना
::सुची::सूची
::सुक्ष्म::सूक्ष्म
::पुर्ण::पूर्ण
::संपुर्ण::संपूर्ण
::सम्पुर्ण::सम्पूर्ण
::पुर्व::पूर्व
::सुर्य::सूर्य
::मुर्ख::मूर्ख
::दुसरा::दूसरा
::दुसरे::दूसरे
::दुसरी::दूसरी
::पहूंच::पहुंच
::पहुच::पहुंच

; Short ि / long ी mixed up inside a word
::आशिर्वाद::आशीर्वाद
::परिक्षा::परीक्षा
::परिक्षार्थी::परीक्षार्थी
::परिक्षण::परीक्षण
::प्रतिक्षा::प्रतीक्षा
::समिक्षा::समीक्षा
::निरिक्षण::निरीक्षण
::निरिक्षक::निरीक्षक
::प्रतियोगीता::प्रतियोगिता
::प्रतीयोगिता::प्रतियोगिता
::द्वितिय::द्वितीय
::तृतिय::तृतीय
::भारतिय::भारतीय
::राष्ट्रिय::राष्ट्रीय
::क्षेत्रिय::क्षेत्रीय
::क्षत्रीय::क्षत्रिय
::दिक्षा::दीक्षा
::शिघ्र::शीघ्र
::उत्तिर्ण::उत्तीर्ण
::श्रीमति::श्रीमती
::पत्नि::पत्नी
::दिवार::दीवार
::दिपावली::दीपावली
::दिपक::दीपक
::प्राचिन::प्राचीन
::नविन::नवीन
::अधिन::अधीन
::कठीन::कठिन
::लेकीन::लेकिन
::यकिन::यकीन
::जमिन::जमीन
::ज़मिन::ज़मीन
::मशिन::मशीन
::परीणाम::परिणाम
::परीचय::परिचय
::परीवर्तन::परिवर्तन
::परीश्रम::परिश्रम
::प्रतीशत::प्रतिशत
::दुनीया::दुनिया
::कीया::किया
::बिमार::बीमार
::बिमारी::बीमारी
::महिना::महीना
::महिने::महीने
::स्विकार::स्वीकार
::प्रशीक्षण::प्रशिक्षण
::शारिरिक::शारीरिक
::दैनीक::दैनिक
::मुश्कील::मुश्किल

; Reph (र्) in the wrong place
::आर्शीवाद::आशीर्वाद
::आर्शिवाद::आशीर्वाद
::आर्शीर्वाद::आशीर्वाद
::आशीवार्द::आशीर्वाद
::आर्दश::आदर्श
::प्रर्दशन::प्रदर्शन
::प्रर्दशनी::प्रदर्शनी
::आर्कषण::आकर्षण
::आर्कषक::आकर्षक
::आर्श्चय::आश्चर्य
::आश्र्चय::आश्चर्य
::अर्न्तराष्ट्रीय::अंतरराष्ट्रीय
::अर्न्तगत::अंतर्गत
::अन्र्तगत::अंतर्गत
::प्रर्याप्त::पर्याप्त
::प्रयावरण::पर्यावरण
::प्रयटन::पर्यटन
::कार्यकृम::कार्यक्रम

; ृ and र / ्र mixed up
::प्रष्ठ::पृष्ठ
::प्रथ्वी::पृथ्वी
::क्रपया::कृपया
::कृप्या::कृपया
::क्रषि::कृषि
::श्रृंगार::शृंगार
::श्रृंखला::शृंखला

; Missing anusvara / nasal
::नही::नहीं
::क्यो::क्यों
::क्योकि::क्योंकि
::दोनो::दोनों
::तुम्हे::तुम्हें
::उन्हे::उन्हें
::इन्हे::इन्हें
::जिन्हे::जिन्हें
::किन्हे::किन्हें
::हमे::हमें
::मेंने::मैंने
::मेने::मैंने
::हालाकि::हालांकि
::एंव::एवं

; ए / ऐ, े / ै and ओ / औ mixed up
::एसा::ऐसा
::एसे::ऐसे
::केसा::कैसा
::केसे::कैसे
::जेसा::जैसा
::जेसे::जैसे
::वेसा::वैसा
::वेसे::वैसे
::पेसा::पैसा
::पेसे::पैसे
::तेयार::तैयार
::तेयारी::तैयारी
::धेर्य::धैर्य
::एतिहासिक::ऐतिहासिक
::इतिहासिक::ऐतिहासिक
::एश्वर्य::ऐश्वर्य
::ओरत::औरत
::दोरान::दौरान

; Missing or extra आ / ऐ / औ in the first syllable of -इक words, and similar
::सप्ताहिक::साप्ताहिक
::समाजिक::सामाजिक
::संस्कृतिक::सांस्कृतिक
::अर्थिक::आर्थिक
::शरीरिक::शारीरिक
::प्रकृतिक::प्राकृतिक
::विज्ञानिक::वैज्ञानिक
::परिवारिक::पारिवारिक
::उद्योगिक::औद्योगिक
::भूगोलिक::भौगोलिक
::पुराणिक::पौराणिक
::धर्मिक::धार्मिक
::अध्यात्मिक::आध्यात्मिक
::प्रमाणिक::प्रामाणिक
::व्यवहारिक::व्यावहारिक
::व्यवसायिक::व्यावसायिक
::साहित्यक::साहित्यिक
::अत्याधिक::अत्यधिक
::अनाधिकार::अनधिकार
::दुरावस्था::दुरवस्था
::अवश्यक::आवश्यक
::आवश्यकीय::आवश्यक
::सहयता::सहायता
::अविष्कार::आविष्कार

; Conjuncts (द्य, द्व, द्द, द्घ, ज्ञ, क्ष, ह्म, ह्न, ह्ल, ज्ज्व, श्न, स्र, च्छ ...)
::विधार्थी::विद्यार्थी
::विधालय::विद्यालय
::महाविधालय::महाविद्यालय
::विश्वविधालय::विश्वविद्यालय
::उधोग::उद्योग
::उधोगपति::उद्योगपति
::उद्धेश्य::उद्देश्य
::उदेश्य::उद्देश्य
::विद्धान::विद्वान
::दवारा::द्वारा
::द्धारा::द्वारा
::उदघाटन::उद्घाटन
::उद्धाटन::उद्घाटन
::उज्वल::उज्ज्वल
::उज्जवल::उज्ज्वल
::चिन्ह::चिह्न
::चिन्हित::चिह्नित
::ब्राम्हण::ब्राह्मण
::ब्रम्ह::ब्रह्म
::ब्रम्हा::ब्रह्मा
::ब्रम्हांड::ब्रह्मांड
::आल्हाद::आह्लाद
::प्रल्हाद::प्रह्लाद
::सन्यास::संन्यास
::सन्यासी::संन्यासी
::स्त्रोत::स्रोत
::सहस्त्र::सहस्र
::स्वास्थ::स्वास्थ्य
::अध्यन::अध्ययन
::प्रशन::प्रश्न
::प्रकिया::प्रक्रिया
::पश्चाताप::पश्चात्ताप
::ग्यान::ज्ञान
::विग्यान::विज्ञान
::विग्यापन::विज्ञापन
::आग्या::आज्ञा
::यग्य::यज्ञ
::कृतग्य::कृतज्ञ
::विशेषग्य::विशेषज्ञ
::छमा::क्षमा
::छेत्र::क्षेत्र
::ईच्छा::इच्छा
::इक्छा::इच्छा
::अछा::अच्छा
::अच्चा::अच्छा

; Other common misspellings
::उदहारण::उदाहरण
::उदारहण::उदाहरण
::कोशिस::कोशिश
::इस्तमाल::इस्तेमाल
::मुस्किल::मुश्किल
::हमेंशा::हमेशा
::धन्यबाद::धन्यवाद
::धनयवाद::धन्यवाद
::धन्यावाद::धन्यवाद
::ब्यवहार::व्यवहार
::ब्यक्ति::व्यक्ति
::समश्या::समस्या
::नमश्कार::नमस्कार
::अनुसाशन::अनुशासन
::प्रसाशन::प्रशासन
::कवियत्री::कवयित्री
::गृहणी::गृहिणी
::प्रदर्शिनी::प्रदर्शनी
::पूज्यनीय::पूजनीय
::शुभकामनाऐं::शुभकामनाएं
::शुभकामनाऐँ::शुभकामनाएँ


;------------------------------------------------------------------------------
; Ambiguous / prescriptive entries - commented out.
; The left side is in common use; the right side is the standard spelling
; (Central Hindi Directorate) or the grammatically preferred form. Move any
; line you agree with above this block to enable it.
;------------------------------------------------------------------------------
/*
::महत्व::महत्त्व
::महत्वपूर्ण::महत्त्वपूर्ण
::तत्व::तत्त्व
::सत्व::सत्त्व
::उपरोक्त::उपर्युक्त
::अनेकों::अनेक  - grammar: अनेक is already plural
::राजनैतिक::राजनीतिक
::त्यौहार::त्योहार
::आधीन::अधीन
::सौंदर्यता::सौंदर्य
::सौजन्यता::सौजन्य
::निरपराधी::निरपराध
::अंतर्राष्ट्रीय::अंतरराष्ट्रीय
::अन्तर्राष्ट्रीय::अंतरराष्ट्रीय
::क्यूंकि::क्योंकि  - often deliberate, informal
::चाहिये::चाहिए  - य/ए forms are both widely used
::लिये::लिए
::गये::गए
::गयी::गई
::इसलिये::इसलिए
*/


;-------------------------------------------------------------------------------
; Anything below this point was added to the script by the user via the Win+Shift+H hotkey.
;-------------------------------------------------------------------------------
