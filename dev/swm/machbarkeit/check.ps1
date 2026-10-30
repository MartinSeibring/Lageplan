# Lageplan – Machbarkeits-Check (PowerShell)
#
# Prüft, ob die spätere Radar-Recherche als PowerShell-Skript in dieser
# Umgebung laufen kann: Version, Ausführungsrichtlinie, Sprachmodus,
# Internetzugriff über den Proxy und Schreiben einer JSON-Datei ohne BOM.
# Es werden keine Daten gesendet – nur drei öffentliche RSS-Feeds abgerufen.
#
# Kompatibel mit Windows PowerShell 5.1. Diese Datei ist UTF-8 mit BOM
# gespeichert, damit 5.1 die Umlaute korrekt liest.

$ErrorActionPreference = 'Continue'
$ergebnis = New-Object System.Collections.ArrayList

function Melde([string]$status, [string]$name, [string]$text) {
    $zeile = "[$status] ${name}: $text"
    [void]$ergebnis.Add($zeile)
    $farbe = switch ($status) { 'OK' { 'Green' } 'Hinweis' { 'Yellow' } default { 'Red' } }
    Write-Host $zeile -ForegroundColor $farbe
}

Write-Host ''
Write-Host 'Lageplan Machbarkeits-Check (PowerShell)' -ForegroundColor Cyan
Write-Host '----------------------------------------'

# ── Umgebung ─────────────────────────────────────────────
$ordner = $PSScriptRoot
if (-not $ordner) { $ordner = Split-Path -Parent $MyInvocation.MyCommand.Path }
Melde 'OK' 'PowerShell-Version' $PSVersionTable.PSVersion.ToString()
Melde 'OK' 'Skriptordner' $ordner
$istNetz = $ordner -like '\\*'
if (-not $istNetz -and $ordner -match '^[A-Za-z]:') {
    try {
        $lw = Get-PSDrive -Name $ordner.Substring(0, 1) -ErrorAction Stop
        if ($lw.DisplayRoot -like '\\*') { $istNetz = $true }
    } catch { }
}
Melde 'OK' 'Liegt auf Netzlaufwerk' $(if ($istNetz) { 'ja' } else { 'nein (lokal)' })

$modus = $ExecutionContext.SessionState.LanguageMode.ToString()
if ($modus -eq 'FullLanguage') {
    Melde 'OK' 'Sprachmodus' $modus
} else {
    Melde 'Hinweis' 'Sprachmodus' "$modus – eingeschränkt (AppLocker/WDAC), Skript muss mit einfachen Befehlen auskommen"
}

try {
    $policies = Get-ExecutionPolicy -List | ForEach-Object { "$($_.Scope)=$($_.ExecutionPolicy)" }
    Melde 'OK' 'Ausführungsrichtlinien' ($policies -join ', ')
    $gpo = Get-ExecutionPolicy -List | Where-Object {
        ($_.Scope -eq 'MachinePolicy' -or $_.Scope -eq 'UserPolicy') -and
        @('Restricted', 'AllSigned', 'RemoteSigned') -contains $_.ExecutionPolicy.ToString()
    }
    if ($gpo) {
        Melde 'Hinweis' 'Gruppenrichtlinie' ("einschränkende Richtlinie per GPO (" + (($gpo | ForEach-Object { "$($_.Scope)=$($_.ExecutionPolicy)" }) -join ', ') + ") – der Starter mit -ExecutionPolicy Bypass wirkt dann nicht")
    } else {
        Melde 'OK' 'Gruppenrichtlinie' 'keine einschränkende GPO – Start über die .cmd-Datei möglich'
    }
} catch {
    Melde 'Hinweis' 'Ausführungsrichtlinien' $_.Exception.Message
}

try {
    $zone = Get-Content -Path $MyInvocation.MyCommand.Path -Stream Zone.Identifier -ErrorAction Stop
    Melde 'Hinweis' 'Download-Markierung' ("Skript ist als aus dem Internet stammend markiert (" + (($zone | Where-Object { $_ -like 'ZoneId*' }) -join '') + ") – ZIP vor dem Entpacken: Rechtsklick > Eigenschaften > Zulassen")
} catch {
    Melde 'OK' 'Download-Markierung' 'keine'
}

# ── Internetzugriff über den Proxy ───────────────────────
try {
    # Windows PowerShell 5.1 nutzt sonst evtl. kein TLS 1.2
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    [Net.WebRequest]::DefaultWebProxy.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials
    Melde 'OK' 'TLS 1.2 und Proxy-Anmeldung' 'gesetzt'
} catch {
    Melde 'Hinweis' 'TLS 1.2 und Proxy-Anmeldung' ("nicht setzbar: " + $_.Exception.Message)
}

$feeds = @(
    @{ Name = 'BNetzA Pressemitteilungen'; Url = 'https://www.bundesnetzagentur.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed/RSSNewsfeed_Pressemitteilungen.xml?nn=693926' },
    @{ Name = 'pv magazine';               Url = 'https://www.pv-magazine.de/feed/' },
    @{ Name = 'Google News';               Url = 'https://news.google.com/rss/search?q=Netzentgelt&hl=de&gl=DE&ceid=DE:de' }
)
$feedsOk = 0
foreach ($f in $feeds) {
    try {
        # Anmeldung nur am Proxy (DefaultWebProxy oben) – nicht an der Zielseite
        $antwort = Invoke-WebRequest -Uri $f.Url -UseBasicParsing -TimeoutSec 30 `
                   -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Lageplan-Check'
        $inhalt = $antwort.Content
        if ($inhalt -is [byte[]]) { $inhalt = [Text.Encoding]::UTF8.GetString($inhalt) }
        $inhalt = $inhalt.TrimStart([char]0xFEFF).Trim()
        $xml = [xml]$inhalt
        $anzahl = @($xml.SelectNodes('//item')).Count + @($xml.SelectNodes("//*[local-name()='entry']")).Count
        Melde 'OK' "Feed $($f.Name)" "$anzahl Einträge"
        $feedsOk++
    } catch {
        Melde 'Fehler' "Feed $($f.Name)" $_.Exception.Message
    }
}

# ── JSON ohne BOM schreiben ──────────────────────────────
$psDatei = Join-Path $ordner 'check-ps.json'
$daten = [ordered]@{
    erstellt = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
    umlaute  = 'äöüß€'
    feeds_ok = $feedsOk
}
$json = $daten | ConvertTo-Json
try {
    $utf8OhneBom = New-Object System.Text.UTF8Encoding -ArgumentList $false
    [IO.File]::WriteAllText($psDatei, $json, $utf8OhneBom)
    Melde 'OK' 'JSON schreiben (UTF-8 ohne BOM)' $psDatei
} catch {
    try {
        Set-Content -Path $psDatei -Value $json -Encoding UTF8
        Melde 'Hinweis' 'JSON schreiben' "nur mit BOM möglich ($($_.Exception.Message))"
    } catch {
        Melde 'Fehler' 'JSON schreiben' $_.Exception.Message
    }
}

try {
    $bytes = [IO.File]::ReadAllBytes($psDatei)
    $hatBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    Melde $(if ($hatBom) { 'Hinweis' } else { 'OK' }) 'JSON-Datei prüfen' $(if ($hatBom) { 'enthält BOM' } else { 'ohne BOM' })
} catch {
    Melde 'Hinweis' 'JSON-Datei prüfen' $_.Exception.Message
}

# ── Ergebnis sichern ─────────────────────────────────────
$kopf = "Lageplan Machbarkeits-Check (PowerShell) – " + (Get-Date).ToString('dd.MM.yyyy HH:mm')
$txtDatei = Join-Path $ordner 'check-ergebnis.txt'
try {
    [IO.File]::WriteAllText($txtDatei, ($kopf + "`r`n" + ($ergebnis -join "`r`n")), (New-Object System.Text.UTF8Encoding -ArgumentList $true))
    Write-Host ''
    Write-Host "Ergebnis gespeichert in: $txtDatei" -ForegroundColor Cyan
} catch {
    Write-Host "Ergebnis konnte nicht gespeichert werden: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host 'Bitte den Inhalt dieser Datei (oder dieses Fensters) zurückmelden.'
