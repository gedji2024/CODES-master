param(
  [Parameter(Mandatory=$true)][string]$Command,
  [Parameter(Mandatory=$false)][int]$IntervalMs = 200,
  [Parameter(Mandatory=$false)][string]$LogCsv = "./docs/ipg_power_log.csv"
)

# Requires Intel Power Gadget installed (Windows). It provides PowerLog3.0.exe.
# Download: https://www.intel.com/content/www/us/en/developer/articles/tool/power-gadget.html

function Test-Command {
  param([string]$Name)
  $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $LogCsv)) {
  New-Item -ItemType File -Path $LogCsv -Force | Out-Null
}

$ipg = "PowerLog3.0.exe"
if (-not (Test-Command $ipg)) {
  Write-Error "Intel Power Gadget logger ($ipg) not found in PATH. Install Intel Power Gadget and add PowerLog3.0.exe to PATH."
  exit 1
}

# Start PowerLog in background to CSV
$args = @("-resolution", $IntervalMs, "-file", $LogCsv)
$ipgProc = Start-Process -FilePath $ipg -ArgumentList $args -PassThru
Start-Sleep -Milliseconds 300

try {
  # Run the target command
  Write-Host "Running: $Command" -ForegroundColor Cyan
  $proc = Start-Process -FilePath pwsh -ArgumentList "-NoProfile","-Command", $Command -PassThru -Wait
} finally {
  # Stop PowerLog
  if ($ipgProc -and -not $ipgProc.HasExited) { $ipgProc.Kill() }
}

# Compute average package power from CSV
$lines = Get-Content $LogCsv | Where-Object { $_ -and -not $_.StartsWith("#") }
if ($lines.Count -lt 2) {
  Write-Error "No samples collected. Check Intel Power Gadget setup."
  exit 1
}

# Find column index for Package Power (W) (header is first non-comment row)
$header = $lines[0].Split(',')
$data = $lines[1..($lines.Count-1)]
$col = ($header | Select-String -Pattern "Package Power" -SimpleMatch).Matches.Count
if ($col -eq 0) {
  # fallback: try generic pattern
  $pkgIdx = ($header | ForEach-Object { $_.Trim() }) | ForEach-Object -Begin { $i=0 } -Process { if ($_ -like "*Package Power*") { $script:found=$true; $script:idx=$i }; $i++ } -End { $script:idx }
} else {
  $pkgIdx = ($header | ForEach-Object -Begin { $i=0 } -Process { if ($_ -like "*Package Power*") { $script:idx=$i }; $i++ } -End { $script:idx })
}

if ($null -eq $pkgIdx) {
  Write-Error "Could not find 'Package Power' column in $LogCsv."
  exit 1
}

$values = @()
foreach ($row in $data) {
  $cells = $row.Split(',')
  if ($cells.Length -gt $pkgIdx) {
    $v = [double]::Parse($cells[$pkgIdx])
    $values += $v
  }
}

if ($values.Count -eq 0) {
  Write-Error "No power values parsed from $LogCsv."
  exit 1
}

$avg = ($values | Measure-Object -Average).Average
Write-Host ("Average CPU package power: {0:N2} W" -f $avg) -ForegroundColor Green

exit 0
