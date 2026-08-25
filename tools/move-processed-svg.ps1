# Moves *_processed.svg exports from the browser's Downloads folder into
# data/svg/processed/, validating each file before it enters the pipeline.
#
# Launched by move-processed-svg.bat in the repo root.

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$destDir  = Join-Path $repoRoot 'data\svg\processed'

# --- Locate the Downloads folder (it can be redirected, so ask the shell) ---
$downloads = $null
try {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    $raw = (Get-ItemProperty -Path $key -Name '{374DE290-123F-4565-9164-39C4925E467B}' -ErrorAction Stop).'{374DE290-123F-4565-9164-39C4925E467B}'
    $downloads = [Environment]::ExpandEnvironmentVariables($raw)
} catch {
    $downloads = Join-Path $env:USERPROFILE 'Downloads'
}

if (-not (Test-Path $downloads)) {
    Write-Host "Downloads folder not found: $downloads" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

Write-Host "From: $downloads"
Write-Host "To  : $destDir"
Write-Host ''

$candidates = @(Get-ChildItem -Path $downloads -Filter '*_processed.svg' -File)
if ($candidates.Count -eq 0) {
    Write-Host 'Nothing to move: no *_processed.svg in Downloads.' -ForegroundColor Yellow
    exit 0
}

# --- Validation: is this really a stitch-editor export? ---
function Test-ProcessedSvg {
    param([string]$Path)

    try {
        $doc = New-Object System.Xml.XmlDocument
        $doc.Load($Path)
    } catch {
        return "not valid XML ($($_.Exception.Message))"
    }

    if ($doc.DocumentElement.LocalName -ne 'svg') {
        return "root element is <$($doc.DocumentElement.LocalName)>, not <svg>"
    }

    $paths = @($doc.GetElementsByTagName('path'))
    if ($paths.Count -eq 0) {
        return 'contains no <path> elements'
    }

    # Layer parameters live in each path's id: 7 underscore-separated fields.
    $named = @($paths | Where-Object { ($_.GetAttribute('id') -split '_').Count -ge 7 })
    if ($named.Count -eq 0) {
        return 'no <path> carries a 7-field layer name in its id'
    }
    if ($named.Count -lt $paths.Count) {
        Write-Host ("  note: {0} of {1} paths have no layer name" -f ($paths.Count - $named.Count), $paths.Count) -ForegroundColor Yellow
    }

    return $null  # valid
}

$moved = 0; $skipped = 0; $rejected = 0

foreach ($file in $candidates) {
    Write-Host "- $($file.Name)"

    # Still downloading? Chrome/Edge/Firefox leave a partial file alongside.
    $partial = @(Get-ChildItem -Path $downloads -File -Filter "$($file.BaseName)*" |
                 Where-Object { $_.Extension -in '.crdownload', '.part', '.tmp' })
    if ($partial.Count -gt 0) {
        Write-Host '  skipped: download still in progress' -ForegroundColor Yellow
        $skipped++; continue
    }

    # Locked by another process (still being written)?
    try {
        $fs = [IO.File]::Open($file.FullName, 'Open', 'Read', 'None')
        $fs.Close()
    } catch {
        Write-Host '  skipped: file is locked by another process' -ForegroundColor Yellow
        $skipped++; continue
    }

    $problem = Test-ProcessedSvg -Path $file.FullName
    if ($problem) {
        Write-Host "  REJECTED: $problem" -ForegroundColor Red
        Write-Host '  left in Downloads, nothing was moved'
        $rejected++; continue
    }

    $target = Join-Path $destDir $file.Name

    if (Test-Path $target) {
        $srcHash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash
        $dstHash = (Get-FileHash $target        -Algorithm SHA256).Hash

        if ($srcHash -eq $dstHash) {
            Remove-Item $file.FullName -Force
            Write-Host '  already in processed/ with identical content; removed the duplicate download'
            $skipped++; continue
        }

        # Different content, same name: keep both rather than overwrite.
        $stamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
        $target = Join-Path $destDir ("{0}_{1}{2}" -f $file.BaseName, $stamp, $file.Extension)
        Write-Host "  name clash with different content -> saving as $(Split-Path $target -Leaf)" -ForegroundColor Yellow
    }

    $srcHash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash
    Move-Item -LiteralPath $file.FullName -Destination $target
    $dstHash = (Get-FileHash $target -Algorithm SHA256).Hash

    if ($srcHash -ne $dstHash) {
        Write-Host '  ERROR: hash mismatch after move, file may be corrupt' -ForegroundColor Red
        $rejected++; continue
    }

    Write-Host "  moved -> $(Split-Path $target -Leaf)" -ForegroundColor Green
    $moved++
}

Write-Host ''
Write-Host ("Done. moved: {0}  skipped: {1}  rejected: {2}" -f $moved, $skipped, $rejected)
