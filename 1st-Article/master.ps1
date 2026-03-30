# master.ps1
param (
    [string]$OLD_ENV,
    [string]$NEW_ENV,
    [switch]$SkipUpload,
    [switch]$PromptPassword,
    [switch]$StorePrompted,  # persist prompted PyPI token to keyring for future runs
    [switch]$SkipVersionBump,
    [switch]$SkipMetrics,
    [switch]$SkipEnvSetup,  # skip conda env destruction/recreation (use when env already exists)
    [string]$PythonVersion = "3.7",
    [string]$FeasBudgets = "10,50",  # comma-separated ms budgets for summary
    [int]$LastN = 0,                 # 0 = use all test episodes (default: $TestEpisodes)
    [switch]$ForceInsideVenv,  # allow running even if currently inside a venv (not recommended)
    [switch]$AccelerateMPS,      # tune env vars for maximum MPS + CPU parallelism on Apple Silicon
    [string]$Scenarios = "100:50",  # comma-separated scenario specs: "n:r,n:r,..." e.g. "70:35,30:25"
    [string]$Seeds = "42,123,456",  # comma-separated training seeds for reproducibility
    [int]$ParallelSeeds = 2,            # how many seeds to train in parallel (RAM dependent)
    [int]$TestEpisodes = 1000,          # number of test episodes per seed per algo
    [switch]$SkipEnsemble                # skip Ensemble Max evaluation phase
)

<#
master.ps1: Orchestrated pipeline for WSN routing with QMIX, QTRAN, QPSOFL, and Ensemble Max.

Steps:
  1. (optional) bump gym_examples version via setup.ps1
  2. recreate conda env (remove OLD_ENV, create NEW_ENV)
  3. install epymarl requirements in NEW_ENV
  4. (optional) upload package securely using upload_package.ps1
  5. for each scenario: run algorithms (QMIX, QTRAN, QPSOFL, Ensemble Max) via run_algos.ps1
  6. (optional) summarize feasibility metrics with budgets

Flags:
  -SkipVersionBump : do not modify version file
  -SkipUpload      : skip twine upload step
  -PromptPassword  : prompt securely for TWINE password if uploading
    -StorePrompted   : after prompting, store token in keyring so future runs skip prompt
  -SkipMetrics     : skip metrics validation/summarization at end
  -SkipEnvSetup    : skip conda env destruction/recreation + pip install (reuse existing env)
  -FeasBudgets     : comma list of ms thresholds for p95 PASS/FAIL table
  -Scenarios       : comma-separated "n_sensors:coverage_radius" pairs.
                     Default: "70:35" (single scenario, 70 sensors, 35m radius).
                     Example: "20:25,30:25,50:35,70:35,70:45,100:35,100:50"

Prerequisites: conda initialized.
#>

# Resolve LastN: default (0) = use all test episodes
if ($LastN -le 0) { $LastN = $TestEpisodes }

# ──────────────────────────────────────────────────────────────
# Define scenarios: array of @{N=...; R=...} hashtables
# ──────────────────────────────────────────────────────────────
$scenarioList = @()
if ($Scenarios -and $Scenarios.Trim()) {
    foreach ($spec in $Scenarios.Split(',')) {
        $parts = $spec.Trim().Split(':')
        if ($parts.Count -eq 2) {
            $scenarioList += @{ N = [int]$parts[0]; R = [double]$parts[1] }
        } else {
            Write-Warning "Invalid scenario spec '$spec' (expected n_sensors:coverage_radius). Skipping."
        }
    }
}
if ($scenarioList.Count -eq 0) {
    # Default: single scenario matching the original configuration
    $scenarioList += @{ N = 70; R = 35.0 }
}

Write-Host "Scenarios to run ($($scenarioList.Count)):" -ForegroundColor Cyan
foreach ($s in $scenarioList) {
    Write-Host "  n_sensors=$($s.N), coverage_radius=$($s.R)" -ForegroundColor DarkCyan
}

function Get-UserHome {
    $userDirPath = [Environment]::GetFolderPath('UserProfile')
    if ($userDirPath) { return $userDirPath }
    if ($env:HOME) { return $env:HOME }
    if ($env:USERPROFILE) { return $env:USERPROFILE }
    return $null
}

function Get-CondaExe {
    # 1) Respect CONDA_EXE if set (common in conda-initialized shells)
    if ($env:CONDA_EXE -and (Test-Path $env:CONDA_EXE)) { return $env:CONDA_EXE }

    # 2) Prefer PATH lookup (works on macOS/Linux/Windows)
    $cmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -and (Test-Path $cmd.Source)) { return $cmd.Source }

    # 3) Common install locations
    $userDir = Get-UserHome
    $paths = @()
    if ($userDir) {
        if ($IsWindows) {
            $paths += (Join-Path $userDir 'miniconda3\Scripts\conda.exe')
            $paths += (Join-Path $userDir 'anaconda3\Scripts\conda.exe')
        } else {
            $paths += (Join-Path $userDir 'miniconda3/bin/conda')
            $paths += (Join-Path $userDir 'miniconda3/condabin/conda')
            $paths += (Join-Path $userDir 'anaconda3/bin/conda')
            $paths += (Join-Path $userDir 'miniforge3/bin/conda')
            $paths += (Join-Path $userDir 'mambaforge/bin/conda')
        }
    }

    if (-not $IsWindows) {
        $paths += '/opt/homebrew/Caskroom/miniconda/base/bin/conda'
        $paths += '/usr/local/Caskroom/miniconda/base/bin/conda'
        $paths += '/opt/homebrew/anaconda3/bin/conda'
        $paths += '/usr/local/anaconda3/bin/conda'
    }

    foreach ($p in $paths) {
        if ($p -and (Test-Path $p)) { return $p }
    }

    throw "Conda executable not found. On macOS/Linux, install Miniconda/Miniforge and ensure 'conda' is on PATH (or set CONDA_EXE). On Windows, install Miniconda/Anaconda or add conda to PATH."
}

function Invoke-Conda {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CondaArgs)
    & (Get-CondaExe) @CondaArgs
}

# Preflight: on macOS/Linux, Python 3.7 is not available on defaults for osx-arm64 and is unsupported by pinned wheels.
if (-not $IsWindows) {
    $userSpecifiedPy = $PSBoundParameters.ContainsKey('PythonVersion')
    $parsedPy = $null
    try {
        $parsedPy = [version]$PythonVersion
    } catch {
        Write-Error "Could not parse -PythonVersion '$PythonVersion' as a version (expected like 3.10). Aborting."; exit 1
    }

    if (-not $userSpecifiedPy -and $parsedPy -lt [version]'3.8') {
        Write-Warning "Default -PythonVersion '$PythonVersion' is not supported on macOS/Linux. Using -PythonVersion 3.10 instead."
        $PythonVersion = '3.10'
        $parsedPy = [version]$PythonVersion
    }

    if ($parsedPy -lt [version]'3.8') {
        Write-Error "On macOS/Linux, -PythonVersion '$PythonVersion' is not supported. Re-run with -PythonVersion 3.10 (or any >= 3.8)."; exit 1
    }
}

if (-not $SkipVersionBump) {
    Write-Host "[1/6] Bumping version (setup.ps1)" -ForegroundColor Cyan
    .\setup.ps1
} else {
    Write-Host "[1/6] Skipping version bump" -ForegroundColor Yellow
}

if (-not $SkipEnvSetup) {
    Write-Host "[2/6] Resetting environment: remove $OLD_ENV create $NEW_ENV" -ForegroundColor Cyan
    try {
        if ($OLD_ENV) {
            Invoke-Conda @('env','remove','-n',$OLD_ENV,'--yes')
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Direct removal of env '$OLD_ENV' failed (exit=$LASTEXITCODE). Retrying via 'conda run -n base'."
                Invoke-Conda @('run','-n','base','conda','env','remove','-n',$OLD_ENV,'--yes')
            }
        }
    } catch { Write-Warning "Could not remove old env ${OLD_ENV}: $($_)" }
    Invoke-Conda @('create','-n',$NEW_ENV,"python=$PythonVersion","--yes")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Conda failed to create env '$NEW_ENV' with python=$PythonVersion (exit=$LASTEXITCODE). Aborting."; exit 1
    }

    # Detect if user is inside a virtualenv; recommend exiting for clean conda activation
    if ($env:VIRTUAL_ENV -and -not $ForceInsideVenv) {
        Write-Warning "Detected active virtualenv: $env:VIRTUAL_ENV. For reliable conda ops, exit this venv (run 'deactivate') then re-run master.ps1. Or use -ForceInsideVenv to proceed with explicit python paths."
    }
} else {
    Write-Host "[2/6] Skipping env setup (reusing existing env '$NEW_ENV')" -ForegroundColor Yellow
}

# Instead of relying on 'conda activate' in a venv, use explicit python path from the target conda env
$condaBase = (Invoke-Conda @('info','--base') | Out-String).Trim()
if (-not $condaBase) {
    Write-Error "Failed to resolve conda base directory via 'conda info --base'. Aborting."; exit 1
}
$CondaEnvRoot = Join-Path (Join-Path $condaBase 'envs') $NEW_ENV
$CondaEnvPython = if ($IsWindows) { Join-Path $CondaEnvRoot 'python.exe' } else { Join-Path $CondaEnvRoot 'bin/python' }
if (-not (Test-Path $CondaEnvPython)) {
    Write-Error "Expected python executable not found at $CondaEnvPython. Aborting."; exit 1
}
Write-Host "Using conda env python: $CondaEnvPython" -ForegroundColor DarkCyan

# Emulate essential parts of 'conda activate' for DLL discovery (primarily needed on Windows)
$env:CONDA_PREFIX = $CondaEnvRoot
if ($IsWindows) {
    $prepend = @(
        $CondaEnvRoot,
        (Join-Path $CondaEnvRoot 'Library\mingw-w64\bin'),
        (Join-Path $CondaEnvRoot 'Library\usr\bin'),
        (Join-Path $CondaEnvRoot 'Library\bin'),
        (Join-Path $CondaEnvRoot 'Scripts'),
        (Join-Path $CondaEnvRoot 'bin')
    ) -join ';'
    $env:PATH = "$prepend;$env:PATH"
}

if (-not $SkipEnvSetup) {
    Write-Host "[3/6] Installing requirements (epymarl/requirements.txt)" -ForegroundColor Cyan
    Invoke-Conda @('install','-n',$NEW_ENV,'--yes','--override-channels','-c','conda-forge','-c','defaults',
        '--solver','classic','--freeze-installed',
        'pip<24.1','packaging<24','setuptools<81','wheel','numpy=1.23.5')
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to pin installer toolchain/numpy via conda for env '$NEW_ENV' (exit=$LASTEXITCODE)."; exit 1 }

    # Install gym via conda-forge without upgrading pinned deps.
    Invoke-Conda @('install','-n',$NEW_ENV,'--yes','--override-channels','-c','conda-forge','-c','defaults',
        '--solver','classic','--freeze-installed','gym=0.21.0')
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install gym=0.21.0 via conda-forge in env '$NEW_ENV' (exit=$LASTEXITCODE)."; exit 1 }

    # Pre-install torch/torchaudio to satisfy packages (some import torch during metadata)
    & $CondaEnvPython -m pip install "torch==1.13.1" "torchaudio==0.13.1" --only-binary=:all:
    # Verify gym import works before proceeding (use single-line to avoid PS newline escaping)
    & $CondaEnvPython -c "import gym" 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Error "Gym is not installed in env '$NEW_ENV'. Please ensure 'conda install -n $NEW_ENV -c conda-forge gym=0.21.0' succeeds and re-run."; exit 1 }
    # Prevent pip from attempting to build gym from sdist when processing requirements
    $prevOnlyBin = $Env:PIP_ONLY_BINARY
    $Env:PIP_ONLY_BINARY = "gym"
    & $CondaEnvPython -m pip install -r (Join-Path (Join-Path $PSScriptRoot 'epymarl') 'requirements.txt')
    $Env:PIP_ONLY_BINARY = $prevOnlyBin
} else {
    Write-Host "[3/6] Skipping requirements install (reusing existing env)" -ForegroundColor Yellow
}

if (-not $SkipUpload) {
    Write-Host "[4/6] Upload step (upload_package.ps1)" -ForegroundColor Cyan
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Stop'
    try {
        if ($PromptPassword) {
            if ($StorePrompted) {
                & .\upload_package.ps1 -NEW_ENV $NEW_ENV -PythonPath $CondaEnvPython -PromptPassword -StorePrompted
            } else {
                & .\upload_package.ps1 -NEW_ENV $NEW_ENV -PythonPath $CondaEnvPython -PromptPassword
            }
        } else {
            & .\upload_package.ps1 -NEW_ENV $NEW_ENV -PythonPath $CondaEnvPython
        }
        if ($LASTEXITCODE -ne 0) {
            throw "upload_package.ps1 exited with code $LASTEXITCODE"
        }
    } catch {
        Write-Error "Upload step failed: $($_.Exception.Message). Aborting pipeline.";
        $ErrorActionPreference = $prevEAP
        exit 1
    }
    $ErrorActionPreference = $prevEAP
} else {
    Write-Host "[4/6] Skipping upload" -ForegroundColor Yellow
}

# ──────────────────────────────────────────────────────────────
# [5/6] Run scenarios: QMIX, QTRAN, QPSOFL, Ensemble Max
# ──────────────────────────────────────────────────────────────
Write-Host "[5/6] Running algorithms across $($scenarioList.Count) scenario(s)" -ForegroundColor Cyan
if ($AccelerateMPS -or (-not $IsWindows)) {
    Write-Host "  [Accel] Configuring MPS acceleration + thread tuning for Apple Silicon" -ForegroundColor DarkCyan
    $env:PYTORCH_MPS_HIGH_WATERMARK_RATIO = "0.0"
    $env:PYTORCH_MPS_LOW_WATERMARK_RATIO = "0.0"
    $env:PYTORCH_ENABLE_MPS_FALLBACK = "1"
    $env:OMP_NUM_THREADS = "3"
    $env:MKL_NUM_THREADS = "3"
    $env:OMP_DYNAMIC = "FALSE"
}
$scenarioIndex = 0
foreach ($scenario in $scenarioList) {
    $scenarioIndex++
    $nSensors = $scenario.N
    $covRadius = $scenario.R
    $scenarioTag = "n${nSensors}_r$([int]$covRadius)"

    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Magenta
    Write-Host " SCENARIO $scenarioIndex/$($scenarioList.Count): n_sensors=$nSensors, coverage_radius=$covRadius ($scenarioTag)" -ForegroundColor Magenta
    Write-Host "========================================================" -ForegroundColor Magenta

    $runAlgoArgs = @{
        NEW_ENV       = $NEW_ENV
        PythonPath    = $CondaEnvPython
        NSensors      = $nSensors
        CoverageRadius = $covRadius
        Seeds         = $Seeds
        ParallelSeeds = $ParallelSeeds
        TestEpisodes  = $TestEpisodes
    }
    if ($SkipEnsemble) { $runAlgoArgs['SkipEnsemble'] = $true }
    & (Join-Path $PSScriptRoot 'run_algos.ps1') @runAlgoArgs
}

if (-not $SkipMetrics) {
    Write-Host "[6/6] Validating & summarizing metrics" -ForegroundColor Cyan
    $budgets = $FeasBudgets.Split(',') | ForEach-Object { [double]$_ }
    & $CondaEnvPython (Join-Path (Join-Path $PSScriptRoot 'tools') 'validate_metrics.py')
    # Build a seed suffix for output filenames so results are traceable
    $seedSuffix = "seeds_$($Seeds -replace ',','_')"
    # Emit full metrics table (md)
    & $CondaEnvPython (Join-Path (Join-Path $PSScriptRoot 'tools') 'summarize_npys.py') --test --last-n $LastN --format md --output-file (Join-Path (Join-Path $PSScriptRoot 'Results_Graphics') "summary_last${LastN}_${seedSuffix}.md")

    # Emit p99 PASS/FAIL table
    $summaryArgs = @((Join-Path (Join-Path $PSScriptRoot 'tools') 'summarize_npys.py'),'--test','--last-n',"$LastN",'--format','md','--p95-table','--use-p99','--budget-ms') + ($budgets | ForEach-Object { $_.ToString() })
    & $CondaEnvPython @summaryArgs

    # Emit generalized feasibility table
    & $CondaEnvPython (Join-Path (Join-Path $PSScriptRoot 'tools') 'summarize_npys.py') --test --last-n $LastN --format md --feas-table --feas wall_step_time_ms_p99:<:50 --feas peak_memory_mb:<:1024 --output-file (Join-Path (Join-Path $PSScriptRoot 'Results_Graphics') "feasibility_last${LastN}_${seedSuffix}.md")
} else {
    Write-Host "[6/6] Skipping metrics summarization" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Pipeline complete. Ran $($scenarioList.Count) scenario(s)." -ForegroundColor Green
