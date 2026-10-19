param([string]$Path)
$utf8 = New-Object System.Text.UTF8Encoding($false)
$text = [IO.File]::ReadAllText($Path, $utf8)
if ($text.Length -gt 0 -and $text[0] -eq [char]0xFEFF) { $text = $text.Substring(1) }
$norm = $text.Normalize([Text.NormalizationForm]::FormC)
"NFC changed text: $($text -ne $norm)"
[IO.File]::WriteAllText($Path, $norm, (New-Object System.Text.UTF8Encoding($true)))
$b = [IO.File]::ReadAllBytes($Path); 'BOM: {0:X2} {1:X2} {2:X2}' -f $b[0], $b[1], $b[2]

$inComment = $false; $seen = @{}; $n = 0
foreach ($line in ($norm -split "`r?`n")) {
    if ($line -match '^\s*/\*') { $inComment = $true; continue }
    if ($line -match '^\s*\*/') { $inComment = $false; continue }
    if ($inComment) { continue }
    if ($line -match '^:([^:]*):(.+?)::(.*?)(\s+;.*)?$') {
        $opts = $Matches[1]; $abbr = $Matches[2]; $rep = $Matches[3]; $n++
        $key = "$opts|$abbr"
        if ($seen.ContainsKey($key)) { "DUPLICATE: $abbr" } else { $seen[$key] = 1 }
        if ($abbr -eq $rep) { "NO-OP: $abbr" }
        foreach ($ch in ($abbr + $rep).ToCharArray()) {
            if ([int]$ch -lt 0x0900 -or [int]$ch -gt 0x097F) { 'NON-DEVANAGARI U+{0:X4} in: {1}' -f [int]$ch, $abbr; break }
        }
    }
}
"Hotstrings checked: $n"
