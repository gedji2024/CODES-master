# upload_package.ps1
param (
    [string]$NEW_ENV,
    [switch]$PromptPassword,
    [switch]$StorePrompted,   # after secure prompt, persist token to keyring for future runs
    [switch]$SkipBuild,
    [switch]$VerboseCreds,
    [switch]$SkipCondaActivate,
    [string]$PythonPath  # explicit python interpreter to use
)

<#
Secure package upload script.
Priority order for credentials:
  1. Use existing environment variables TWINE_USERNAME / TWINE_PASSWORD if already set.
  2. If TWINE_PASSWORD not set and -PromptPassword specified, prompt securely.
  3. Abort with clear message if no password available (never read from deleted plaintext file).

Usage examples:
    .\upload_package.ps1 -NEW_ENV d6 -PromptPassword            # prompt once for PyPI token
    .\upload_package.ps1 -NEW_ENV d6 -PromptPassword -StorePrompted # prompt then persist to keyring
    (Set $Env:TWINE_USERNAME and $Env:TWINE_PASSWORD beforehand to skip prompting.)

You previously removed password_pypi.txt for security; this script no longer expects it.
#>

function Get-PlaintextFromSecure($secure) {
    if (-not $secure) { return $null }
    $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

# Choose python interpreter
$py = if ($PythonPath -and (Test-Path $PythonPath)) { $PythonPath } else { 'python' }
if ($VerboseCreds) { Write-Host "Using Python: $py" -ForegroundColor DarkGray }

$twUser = $Env:TWINE_USERNAME
$twPass = $Env:TWINE_PASSWORD

$credSource = $null

if (-not $twUser) { $twUser = "__token__" }  # default for PyPI token uploads

# Attempt automatic credential sources in order:
# 1. Existing env vars
# 2. Windows Credential Manager via keyring (if available)
# 3. ~/.pypirc file
# 4. Secure prompt (if -PromptPassword)
# 5. Abort

if (-not $twPass) {
    # Try Windows Credential Manager via Python keyring (if available)
    try {
        $code = "import sys;\ntry:\n import keyring\nexcept Exception:\n sys.exit(2)\nservice='https://upload.pypi.org/legacy/'; user='__token__'\npwd = keyring.get_password(service, user)\nprint(pwd) if pwd else sys.exit(1)\n"
        $keyringLookup = & $py -c $code 2>$null
        if ($LASTEXITCODE -eq 0 -and $keyringLookup) {
            $twPass = ($keyringLookup | Out-String).Trim()
            $credSource = 'keyring'
            if ($VerboseCreds) { Write-Host "Found PyPI token in Windows Credential Manager (keyring)." -ForegroundColor DarkGray }
        } elseif ($LASTEXITCODE -eq 2) {
            if ($VerboseCreds) { Write-Host "keyring not installed; skipping credential manager lookup." -ForegroundColor DarkGray }
        }
    } catch { if ($VerboseCreds) { Write-Host "Keyring lookup failed: $_" -ForegroundColor DarkGray } }
}

if (-not $twPass) {
    $pyPircPath = Join-Path $HOME ".pypirc"
    if (Test-Path $pyPircPath) {
        $content = Get-Content $pyPircPath
        $inPypi = $false
        foreach ($line in $content) {
            $trim = $line.Trim()
            if ($trim -match '^\[pypi\]$') { $inPypi = $true; continue }
            if ($inPypi -and $trim -match '^username\s*=\s*(.+)$' -and -not $Env:TWINE_USERNAME) { $twUser = $Matches[1].Trim() }
            if ($inPypi -and $trim -match '^password\s*=\s*(.+)$') { $twPass = $Matches[1].Trim(); break }
            if ($trim -match '^\[' -and $trim -ne '[pypi]') { $inPypi = $false }
        }
        if ($twPass) { $credSource = '.pypirc' }
        if ($VerboseCreds) { Write-Host "Detected .pypirc credentials (user=$twUser passPresent=$([bool]$twPass))" -ForegroundColor DarkGray }
    }
}

if (-not $twPass) {
    if ($PromptPassword) {
        $secure = Read-Host "Enter TWINE password (PyPI token)" -AsSecureString
        $twPass = Get-PlaintextFromSecure $secure
        if ($twPass) { $credSource = 'prompt' }
        if ($StorePrompted -and $twPass) {
            try {
                # Store under both common service names to maximize compatibility across twine/keyring versions.
                $codeSet = @"
import keyring, sys
pwd=sys.argv[1]
user='__token__'
services=['https://upload.pypi.org/legacy/','pypi']
for service in services:
    keyring.set_password(service,user,pwd)
print('Stored token in keyring')
"@
                & $py -c $codeSet $twPass 2>$null | Write-Host
            } catch { Write-Warning "Failed to store token in keyring: $_" }
        }
    } else {
        Write-Error "No TWINE_PASSWORD env var, not found in Windows Credential Manager or ~/.pypirc, and -PromptPassword not specified. Set TWINE_PASSWORD, store via keyring, create ~/.pypirc, or use -PromptPassword."; exit 1
    }
}

# Sanity checks for common auth mistakes (do not print secrets)
if (-not $twUser) { $twUser = '__token__' }
if ($twUser -eq '__token__') {
    if ($twPass -match '^[0-9a-f]{16}$') {
        Write-Error "The provided value looks like a PyPI recovery code (16 hex chars), not an API token. Create a PyPI API token and use that as the password (it starts with 'pypi-')."; exit 1
    }
    if ($twPass -and -not ($twPass.StartsWith('pypi-'))) {
        Write-Error "When using username '__token__', the password must be a PyPI API token that starts with 'pypi-'. The provided value doesn't match that format."; exit 1
    }
}

if (-not $credSource -and $Env:TWINE_PASSWORD) { $credSource = 'env' }
if ($VerboseCreds) { Write-Host "Twine credential source: $credSource (username=$twUser)" -ForegroundColor DarkGray }

# Export to environment for twine (so downstream tools see them even if sourced from .pypirc)
$Env:TWINE_USERNAME = $twUser
$Env:TWINE_PASSWORD = $twPass

# Build wheel unless skipped
Push-Location
try {
    Set-Location -Path (Join-Path $PSScriptRoot 'gym-examples')
    if (-not $SkipBuild) {
        if (Test-Path .\dist) { Remove-Item .\dist -Recurse -Force }
        & $py -m pip install --upgrade build
        & $py -m build --wheel
    } else {
        Write-Host "Skipping build step (-SkipBuild provided)."
    }

    & $py -m pip install --upgrade twine keyring
    # Avoid failing the whole pipeline if the same version artifact already exists on the repository.
    & $py -m twine upload --skip-existing dist/*
} finally {
    Pop-Location
}
Write-Host "Upload complete." 