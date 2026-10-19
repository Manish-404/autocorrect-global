<#
Checks that the autocorrect really fires in real programs, not just in a test box.

For each program it opens its own fresh window, types a sentence the way a person would, copies what ended up in
the text box and compares it with what should be there. It only touches windows it opened itself (browsers get a
throw-away profile under .tmp, Office gets a new blank file that is never saved, so your own windows, sign-ins and
documents are left alone), and it puts your clipboard back afterwards.

Run it from a normal PowerShell window and keep your hands off the keyboard for about a minute.

  .\run_compat.ps1                                   # WordPad, Chrome and Firefox (page box + address bar)
  .\run_compat.ps1 -Targets wordpad                  # just one
  .\run_compat.ps1 -Language hindi                   # test the Devanagari script instead
  .\run_compat.ps1 -Targets word,excel,powerpoint    # Microsoft Office (skipped for any app you already have open)
  .\run_compat.ps1 -Targets enter-key                # what happens when Enter comes straight after the last word

-Language picks a sentence from cases.json: hinglish (default), hindi or english, plus the three demo lines for Office:
word-demo, excel-demo and powerpoint-demo.

English has no script of its own to start: it goes through the copy of AutoCorrect.ahk you already have running,
because starting a second copy of a script replaces the first.
#>
param(
    [string[]]$Targets = @('wordpad', 'chrome', 'firefox'),
    [string]$Language = 'hinglish',
    [string]$Script = '',
    [string]$Ahk = 'C:\Program Files\AutoHotkey\AutoHotkeyU64.exe'
)
$ErrorActionPreference = 'Stop'
$Targets = @($Targets | ForEach-Object { $_ -split ',' } | Where-Object { $_ })   # "-File ... -Targets a,b" arrives as one string

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$work = Join-Path $root '.tmp\compat'
New-Item -ItemType Directory -Force $work | Out-Null
$env:TEMP = $work; $env:TMP = $work          # keep temp files off the C: drive
$driver = Join-Path $PSScriptRoot 'app_test.ahk'
$pageUrl = ([System.Uri](Join-Path $PSScriptRoot 'compat_page.html')).AbsoluteUri
# The sentences (real ones, with a meaning) live in cases.json, which is UTF-8 so Hindi survives.
$cases = Get-Content (Join-Path $PSScriptRoot 'cases.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$case = $cases.$Language
if (-not $case) { throw "Unknown -Language '$Language'. Choose one of: $(($cases.PSObject.Properties.Name) -join ', ')" }
if (-not $Script) { $Script = $case.script }
$typed = [string]$case.typed
$expected = [string]$case.expected

Add-Type -Namespace Win -Name User32 -MemberDefinition '[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);'
function Get-WindowOwner([int]$hwnd) { $owner = [uint32]0; [void][Win.User32]::GetWindowThreadProcessId([IntPtr]$hwnd, [ref]$owner); [int]$owner }

$results = New-Object System.Collections.Generic.List[object]

# $win is an AutoHotkey window description, e.g. "ahk_pid 1234" or "ahk_id 5678".
function Invoke-Typing([string]$name, [string]$win, [int]$addressBar) {
    $out = Join-Path $work ("result_{0}.txt" -f ($name -replace '[^a-zA-Z0-9]+', '_'))
    Remove-Item $out -ErrorAction SilentlyContinue
    $t = Start-Process -FilePath $Ahk -ArgumentList ('"{0}" "{1}" "{2}" {3} "{4}"' -f $driver, $win, $out, $addressBar, $typed) -PassThru
    if (-not $t.WaitForExit(150000)) { $t.Kill() }
    $raw = if (Test-Path $out) { Get-Content $out -Raw -Encoding UTF8 } else { 'ABORT: no result file' }
    if ($null -eq $raw) { $raw = '' }
    $got = ([string]$raw -replace "`r`n|`n|`r|`v", ' ').Trim()
    if ($got.StartsWith('ABORT')) { $status = 'ABORT' }
    elseif ($got -eq '') { $status = 'FAIL'; $got = '(nothing was copied from the text box)' }
    elseif ($got -ceq $expected) { $status = 'PASS' }
    elseif ($addressBar -eq 1 -and $got.StartsWith($expected)) { $status = 'PASS' }   # the address bar may add a suggestion after the text
    else { $status = 'FAIL' }
    $results.Add([pscustomobject]@{ Where = $name; Result = $status; Got = $got })
    Write-Host ("  {0,-6} {1}" -f $status, $name)
}

# Like Invoke-Typing, but ends the sentence with Enter instead of a space, in a box where Enter "sends" the text
# (compat_enter.html). Nothing to pass or fail: it reports what was sent, so you can see where the last word ends up.
function Invoke-EnterTest([string]$name, [int]$procId) {
    $out = Join-Path $work 'result_enter_key.txt'
    Remove-Item $out -ErrorAction SilentlyContinue
    $text = $typed.TrimEnd('.')
    $t = Start-Process -FilePath $Ahk -ArgumentList ('"{0}" "ahk_pid {1}" "{2}" 0 "{3}" enter' -f $driver, $procId, $out, $text) -PassThru
    if (-not $t.WaitForExit(150000)) { $t.Kill() }
    $raw = if (Test-Path $out) { Get-Content $out -Raw -Encoding UTF8 } else { 'ABORT: no result file' }
    if ($null -eq $raw) { $raw = '' }
    $got = ([string]$raw -replace "`r`n|`n", ' ').Trim()
    $status = if ($got.StartsWith('ABORT')) { 'ABORT' } else { 'INFO' }
    $results.Add([pscustomobject]@{ Where = $name; Result = $status; Got = $got })
    Write-Host ("  {0,-6} {1}" -f $status, $name)
}

function Stop-Tree([int]$procId) {
    cmd.exe /c "taskkill.exe /PID $procId /T /F >nul 2>&1"
    $global:LASTEXITCODE = 0
}

# A browser's first process may hand over to another one (Firefox does), so find the real one by its
# profile folder: the main process is the one that is not a helper (--type= / -contentproc).
function Wait-BrowserPid([string]$exeName, [string]$profileDir, [int]$timeoutSec = 40) {
    $until = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $until) {
        $main = Get-CimInstance Win32_Process -Filter "Name='$exeName'" |
            Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profileDir) -and $_.CommandLine -notmatch '--type=|-contentproc' } |
            Select-Object -First 1
        $proc = if ($main) { Get-Process -Id $main.ProcessId -ErrorAction SilentlyContinue } else { $null }
        if ($proc -and $proc.MainWindowHandle -ne 0) { return [int]$proc.Id }   # a launcher that already exited gives $null: skip it
        Start-Sleep -Milliseconds 500
    }
    return 0
}

function Stop-Profile([string]$exeName, [string]$profileDir) {
    Get-CimInstance Win32_Process -Filter "Name='$exeName'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profileDir) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

# Word, Excel or PowerPoint: opens a blank file through the app's automation interface, puts the cursor where
# typing goes (the document, cell A1, the title of a new slide), types, and closes the app without saving.
function Test-Office([string]$kind) {
    $nice = @{ word = 'Word'; excel = 'Excel'; powerpoint = 'PowerPoint' }[$kind]
    $exeName = @{ word = 'WINWORD'; excel = 'EXCEL'; powerpoint = 'POWERPNT' }[$kind]
    $progId = @{ word = 'Word.Application'; excel = 'Excel.Application'; powerpoint = 'PowerPoint.Application' }[$kind]
    if (Get-Process $exeName -ErrorAction SilentlyContinue) {
        $results.Add([pscustomobject]@{ Where = $nice; Result = 'SKIPPED'; Got = "$nice is already open: your documents are not touched" })
        return
    }
    if (-not [type]::GetTypeFromProgID($progId)) {
        $results.Add([pscustomobject]@{ Where = $nice; Result = 'SKIPPED'; Got = 'not installed' })
        return
    }
    $app = $null; $owner = 0
    try {
        $app = New-Object -ComObject $progId
        switch ($kind) {
            'word' {
                $app.Visible = $true
                $null = $app.Documents.Add()
                $app.Activate()
                $hwnd = [int]$app.ActiveWindow.Hwnd
            }
            'excel' {
                $app.Visible = $true
                $null = $app.Workbooks.Add()
                $null = $app.ActiveSheet.Range('A1').Select()
                $hwnd = [int]$app.Hwnd
            }
            'powerpoint' {
                $app.Visible = -1
                $pres = $app.Presentations.Add()
                $slide = $pres.Slides.AddSlide(1, $pres.SlideMaster.CustomLayouts.Item(1))
                $app.ActiveWindow.ViewType = 9            # normal view
                $app.Activate()
                $slide.Shapes.Item(1).TextFrame.TextRange.Select()   # cursor inside the slide's title
                $hwnd = [int]$app.HWND
            }
        }
        $owner = Get-WindowOwner $hwnd
        Start-Sleep -Seconds 3
        Invoke-Typing $nice "ahk_id $hwnd" 0
    }
    catch {
        $results.Add([pscustomobject]@{ Where = $nice; Result = 'ABORT'; Got = $_.Exception.Message })
        Write-Host ("  ABORT  {0}: {1}" -f $nice, $_.Exception.Message)
    }
    finally {
        # nothing was ever saved, so there is nothing to ask about: close the app we opened
        if ($owner) { Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue }
        if ($app) { try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch { } }
    }
}

$hotstringHost = $null
try {
    if ($Script) {
        $hotstringHost = Start-Process -FilePath $Ahk -ArgumentList ('"{0}"' -f (Join-Path $root $Script)) -PassThru
        "Started {0} as a test copy (PID {1}); waiting for it to load..." -f $Script, $hotstringHost.Id
        Start-Sleep -Seconds 8
    }
    else {
        # English: go through the copy of AutoCorrect.ahk that is already running (a second copy would replace it)
        $list = Join-Path $work 'running_scripts.txt'
        Remove-Item $list -ErrorAction SilentlyContinue
        Start-Process -FilePath $Ahk -ArgumentList ('"{0}" "{1}"' -f (Join-Path $PSScriptRoot 'running_scripts.ahk'), $list) -Wait
        $running = if (Test-Path $list) { Get-Content $list -Encoding UTF8 } else { @() }
        if (-not ($running | Where-Object { $_ -match 'AutoCorrect\.ahk - AutoHotkey' })) {
            throw 'AutoCorrect.ahk is not running. Start it first (double-click it), then run this again.'
        }
        'Using the copy of AutoCorrect.ahk that is already running.'
    }

    if ($Targets -contains 'wordpad') {
        $exe = 'C:\Program Files\Windows NT\Accessories\wordpad.exe'
        if (Test-Path $exe) {
            $p = Start-Process $exe -PassThru
            try { Invoke-Typing 'WordPad (document editor)' "ahk_pid $($p.Id)" 0 } finally { Stop-Tree $p.Id }
        } else { $results.Add([pscustomobject]@{ Where = 'WordPad'; Result = 'SKIPPED'; Got = 'not installed' }) }
    }

    foreach ($office in 'word', 'excel', 'powerpoint') {
        if ($Targets -contains $office) { Test-Office $office }
    }

    if ($Targets -contains 'chrome') {
        $exe = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
        if (Test-Path $exe) {
            $profile = Join-Path $work 'chrome-profile'
            Remove-Item $profile -Recurse -Force -ErrorAction SilentlyContinue
            $null = Start-Process $exe -PassThru -ArgumentList ('--user-data-dir="{0}" --no-first-run --no-default-browser-check --disable-extensions --new-window "{1}"' -f $profile, $pageUrl)
            try {
                $browser = Wait-BrowserPid 'chrome.exe' $profile
                if ($browser -eq 0) { $results.Add([pscustomobject]@{ Where = 'Chrome'; Result = 'ABORT'; Got = 'window did not open' }) }
                else {
                    Invoke-Typing 'Chrome: text box on a web page' "ahk_pid $browser" 0
                    Invoke-Typing 'Chrome: address bar' "ahk_pid $browser" 1
                }
            } finally { Stop-Profile 'chrome.exe' $profile }
        } else { $results.Add([pscustomobject]@{ Where = 'Chrome'; Result = 'SKIPPED'; Got = 'not installed' }) }
    }

    if ($Targets -contains 'enter-key') {
        $exe = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
        if (Test-Path $exe) {
            $profile = Join-Path $work 'chrome-profile-enter'
            Remove-Item $profile -Recurse -Force -ErrorAction SilentlyContinue
            $enterUrl = ([System.Uri](Join-Path $PSScriptRoot 'compat_enter.html')).AbsoluteUri
            $null = Start-Process $exe -PassThru -ArgumentList ('--user-data-dir="{0}" --no-first-run --no-default-browser-check --disable-extensions --new-window "{1}"' -f $profile, $enterUrl)
            try {
                $browser = Wait-BrowserPid 'chrome.exe' $profile
                if ($browser -eq 0) { $results.Add([pscustomobject]@{ Where = 'Enter key'; Result = 'ABORT'; Got = 'window did not open' }) }
                else { Invoke-EnterTest 'Chat or search box: last word followed straight by Enter' $browser }
            } finally { Stop-Profile 'chrome.exe' $profile }
        } else { $results.Add([pscustomobject]@{ Where = 'Enter key'; Result = 'SKIPPED'; Got = 'Chrome not installed' }) }
    }

    if ($Targets -contains 'firefox') {
        $exe = 'C:\Program Files\Mozilla Firefox\firefox.exe'
        if (Test-Path $exe) {
            $profile = Join-Path $work 'firefox-profile'
            Remove-Item $profile -Recurse -Force -ErrorAction SilentlyContinue
            New-Item -ItemType Directory -Force $profile | Out-Null
            Set-Content -Path (Join-Path $profile 'user.js') -Encoding ASCII -Value @(
                'user_pref("browser.aboutwelcome.enabled", false);',
                'user_pref("browser.shell.checkDefaultBrowser", false);',
                'user_pref("browser.startup.homepage_override.mstone", "ignore");',
                'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
                'user_pref("browser.newtabpage.enabled", false);',
                'user_pref("browser.preonboarding.enabled", false);',
                'user_pref("termsofuse.bypassNotification", true);',
                'user_pref("browser.startup.page", 0);')
            $null = Start-Process $exe -PassThru -ArgumentList ('-no-remote -profile "{0}" -new-window "{1}"' -f $profile, $pageUrl)
            try {
                $browser = Wait-BrowserPid 'firefox.exe' $profile
                if ($browser -eq 0) { $results.Add([pscustomobject]@{ Where = 'Firefox'; Result = 'ABORT'; Got = 'window did not open' }) }
                else {
                    Invoke-Typing 'Firefox: text box on a web page' "ahk_pid $browser" 0
                    Invoke-Typing 'Firefox: address bar' "ahk_pid $browser" 1
                }
            } finally { Stop-Profile 'firefox.exe' $profile }
        } else { $results.Add([pscustomobject]@{ Where = 'Firefox'; Result = 'SKIPPED'; Got = 'not installed' }) }
    }
}
finally {
    if ($hotstringHost -and -not $hotstringHost.HasExited) { $hotstringHost.Kill() }
}

"`nScript:   $Script"
"Typed:    $typed"
"Expected: $expected`n"
$table = $results | Format-Table -AutoSize -Wrap | Out-String -Width 200
$table
# the console may not show Hindi properly, so keep a UTF-8 copy too
Set-Content -Path (Join-Path $work 'last_results.txt') -Encoding UTF8 -Value (@("Script: $Script", "Typed: $typed", "Expected: $expected", '') + ($results | ForEach-Object { '{0,-8} {1}  ->  {2}' -f $_.Result, $_.Where, $_.Got }))
