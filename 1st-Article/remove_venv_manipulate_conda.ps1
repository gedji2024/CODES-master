[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param(
    # Path to the virtual environment folder (default: ./myenv)
    [string]$Path = ".\myenv",
    # If provided, search for a folder with this name under the current directory
    [string]$Name,
    # Kill any running processes whose executable resides inside the venv folder
    [switch]$KillProcesses,
    # Also prune VS Code interpreter pin if it points to this venv (./.vscode/settings.json)
    [switch]$UpdateVSCode,
    # Number of delete retries on failure (locks)
    [int]$Retries = 3,
    # Milliseconds to wait between retries
    [int]$RetryDelayMs = 500
)

function Resolve-VenvPath {
    param([string]$Path,[string]$Name)
    if ($Name) {
        $matches = Get-ChildItem -Path . -Directory -Filter $Name -Recurse -ErrorAction SilentlyContinue
        if (-not $matches) { throw "No folder named '$Name' found under $(Get-Location)." }
        if ($matches.Count -gt 1) {
            $list = ($matches | ForEach-Object { $_.FullName }) -join [Environment]::NewLine
            throw "Multiple folders named '$Name' found. Please specify -Path explicitly. Found:\n$list"
        }
        return $matches.FullName
    } else {
        return (Resolve-Path -Path $Path -ErrorAction Stop).Path
    }
}

function Deactivate-VenvIfActive {
    try {
        if ($env:VIRTUAL_ENV) {
            if ($env:VIRTUAL_ENV -and ($env:VIRTUAL_ENV -eq $script:VenvFullPath)) {
                if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }
                Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue | Out-Null
            }
        }
    } catch { Write-Verbose "Deactivate check failed: $_" }
}

function Stop-VenvProcesses {
    param([string]$VenvPath)
    $procs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($VenvPath, [System.StringComparison]::OrdinalIgnoreCase) }
    if ($procs) {
        Write-Host "Found processes running from venv: " ($procs | Select-Object -ExpandProperty ProcessName -Unique -join ', ')
        if ($KillProcesses) {
            foreach ($p in $procs) {
                try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
            }
        } else {
            Write-Warning "Some processes are using the venv. Re-run with -KillProcesses or close them manually."
        }
    }
}

function Remove-VenvFolder {
    param([string]$VenvPath,[int]$Retries,[int]$DelayMs)
    if (-not (Test-Path -LiteralPath $VenvPath)) { return }

    for ($i=0; $i -le $Retries; $i++) {
        try {
            if ($PSCmdlet.ShouldProcess($VenvPath, 'Remove venv folder')) {
                Remove-Item -LiteralPath $VenvPath -Recurse -Force -ErrorAction Stop
            }
            return
        } catch {
            if ($i -eq $Retries) { break }
            Start-Sleep -Milliseconds $DelayMs
        }
    }

    # Long-path or stubborn lock fallback using cmd rmdir with long-path prefix
    try {
        $long = "\\\\?\" + $VenvPath
        if ($PSCmdlet.ShouldProcess($long, 'Force remove via rmdir /s /q')) {
            cmd /c rmdir /s /q "$long"
        }
    } catch {}
}

# Entry
try {
    $script:VenvFullPath = Resolve-VenvPath -Path $Path -Name $Name
} catch {
    Write-Error $_
    exit 1
}

Write-Host "Target venv: $script:VenvFullPath" -ForegroundColor Cyan

# 1) Deactivate if this shell is inside the venv
Deactivate-VenvIfActive

# 2) Stop processes from that venv (optional)
Stop-VenvProcesses -VenvPath $script:VenvFullPath

# 3) Remove folder with retries and fallback
Remove-VenvFolder -VenvPath $script:VenvFullPath -Retries $Retries -DelayMs $RetryDelayMs

if (Test-Path -LiteralPath $script:VenvFullPath) {
    Write-Error "Failed to remove venv folder. Check file locks or use -KillProcesses."
    exit 1
}

# 4) VS Code settings cleanup (optional)
if ($UpdateVSCode -and (Test-Path .\.vscode\settings.json)) {
    try {
        $settingsPath = ".\\.vscode\\settings.json"
        $json = Get-Content $settingsPath -Raw | ConvertFrom-Json
        $updated = $false
        if ($json.python && $json.python.defaultInterpreterPath) {
            if ($json.python.defaultInterpreterPath -like "*$script:VenvFullPath*") { $json.python.defaultInterpreterPath = $null; $updated = $true }
        }
        if ($json.pythonPath) {
            if ($json.pythonPath -like "*$script:VenvFullPath*") { $json | Add-Member -NotePropertyName pythonPath -NotePropertyValue $null -Force; $updated = $true }
        }
        if ($updated) {
            ($json | ConvertTo-Json -Depth 10) | Set-Content -Path $settingsPath -Encoding UTF8
            Write-Host "Updated .vscode/settings.json to remove venv interpreter pin." -ForegroundColor DarkGreen
        }
    } catch { Write-Warning "Could not update VS Code settings: $_" }
}

Write-Host "Virtual environment removed successfully." -ForegroundColor Green

# How to use this script:
# .\remove_venv.ps1 -Path ".\myenv" -KillProcesses -UpdateVSCode -Confirm:$false # If the venv folder is in the repo root:
# .\remove_venv.ps1 -Name xxxx -KillProcesses -UpdateVSCode -Confirm:$false # If you need to search for the venv folder by name:

# To list all conda envs:
# & "$Env:USERPROFILE\miniconda3\Scripts\conda.exe" env list

# To completely remove a conda env:
# & "$Env:USERPROFILE\miniconda3\Scripts\conda.exe" env remove -n ENV_NAME_HERE --yes
# (Replace ENV_NAME_HERE with the name of the conda environment to remove)

# use conda to run a script with proper activation context
# & "$Env:USERPROFILE\miniconda3\Scripts\conda.exe" run -n ENV_NAME_HERE python .\script_to_run.py
# (Replace ENV_NAME_HERE with the name of the conda environment and script_to_run.py with your script)