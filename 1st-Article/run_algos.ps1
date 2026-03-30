# run_epymarl.ps1
param (
    [string]$NEW_ENV,
    [string]$PythonPath,
    [int]$NSensors = 100,
    [double]$CoverageRadius = 50.0,
    [string]$Seeds = "42,123,456",
    [int]$ParallelSeeds = 2,
    [int]$TestEpisodes = 1000,
    [switch]$SkipEnsemble               # skip Ensemble Max evaluation
)

function Get-UserHome {
    $userDirPath = [Environment]::GetFolderPath('UserProfile')
    if ($userDirPath) { return $userDirPath }
    if ($env:HOME) { return $env:HOME }
    if ($env:USERPROFILE) { return $env:USERPROFILE }
    return $null
}

function Get-CondaExe {
    if ($env:CONDA_EXE -and (Test-Path $env:CONDA_EXE)) { return $env:CONDA_EXE }
    $cmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -and (Test-Path $cmd.Source)) { return $cmd.Source }

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
    foreach ($p in $paths) { if ($p -and (Test-Path $p)) { return $p } }
    return $null
}

function Get-ExpectedGymExamplesVersion {
    param(
        [string]$InitPath = (Join-Path (Join-Path (Join-Path $PSScriptRoot 'gym-examples') 'gym_examples') '__init__.py')
    )
    if (-not (Test-Path $InitPath)) {
        throw "Expected gym_examples version file not found at: $InitPath"
    }
    $content = Get-Content -Path $InitPath -Raw
    $m = [regex]::Match($content, '__version__\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"')
    if (-not $m.Success) {
        throw "Could not parse __version__ from $InitPath"
    }
    return $m.Groups[1].Value
}

function Write-EvaluationMessage {
    param (
        [string]$message
    )

    $border = '*' * ($message.Length + 4)
    Write-Host -NoNewline "`n`n`n"
    Write-Host $border
    Write-Host "* $message *"
    Write-Host $border
    Write-Host -NoNewline "`n`n`n"
}

# Resolve python interpreter to use, preferring explicit path from master.ps1
$python = if ($PythonPath -and (Test-Path $PythonPath)) { $PythonPath } else {
    $repoPython = Join-Path (Get-Location) "myenv/Scripts/python.exe"
    if (Test-Path $repoPython) { $repoPython } else { "python" }
}

Push-Location
try {
    # Navigate to the epymarl directory and install the requirements
    $epymarlDir = Join-Path $PSScriptRoot 'epymarl'
    Set-Location -Path $epymarlDir

    New-Item -ItemType Directory -Path (Join-Path (Join-Path (Get-Location) 'results') 'data') -Force | Out-Null
    # IMPORTANT: gym==0.21.0 has invalid requirements metadata; newer pip/packaging refuse to operate.
    # Keep a known-good installer toolchain for this legacy stack.
    $prevPipCheck = $env:PIP_DISABLE_PIP_VERSION_CHECK
    $env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

    function Test-PipToolchainOk {
        param([Parameter(Mandatory=$true)][string]$PythonExe)
        $code = @'
import sys
try:
    import pip
except Exception:
    print('pip:missing'); sys.exit(2)
try:
    import packaging
except Exception:
    print('packaging:missing'); sys.exit(2)
try:
    import numpy
except Exception:
    numpy=None

def v(s):
    parts=[]
    for x in str(s).split('.'):
        try: parts.append(int(x))
        except Exception: parts.append(0)
    return parts

pip_ok = v(pip.__version__) < v('24.1')
pack_ok = v(packaging.__version__) < v('24')
np_ok = (numpy is None) or (v(numpy.__version__) == v('1.23.5'))

print(f"pip={pip.__version__} packaging={packaging.__version__} numpy={(numpy.__version__ if numpy else 'missing')} ok={(pip_ok and pack_ok and np_ok)}")
sys.exit(0 if (pip_ok and pack_ok and np_ok) else 1)
'@
        & $PythonExe -c $code 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }

    $toolchainOk = Test-PipToolchainOk -PythonExe $python
    $condaExeForPins = $null
    try { $condaExeForPins = Get-CondaExe } catch { $condaExeForPins = $null }
    if (-not $toolchainOk -and $condaExeForPins -and (Test-Path $condaExeForPins) -and $NEW_ENV) {
        # Pin via conda to avoid pip self-downgrade corrupting vendored libs in conda environments.
        # Use conda-forge and constraints rather than exact versions (defaults may not carry older pip builds).
        $prevSolver = $env:CONDA_SOLVER
        $env:CONDA_SOLVER = 'classic'
        & $condaExeForPins install -n $NEW_ENV --yes --override-channels -c conda-forge -c defaults --solver classic --freeze-installed "pip<24.1" "packaging<24" "setuptools<81" wheel "numpy=1.23.5"
        $exit = $LASTEXITCODE
        if ($prevSolver) { $env:CONDA_SOLVER = $prevSolver } else { Remove-Item Env:CONDA_SOLVER -ErrorAction SilentlyContinue }
        if ($exit -ne 0) {
            # If conda crashed but the toolchain is already OK, continue.
            if (Test-PipToolchainOk -PythonExe $python) {
                Write-Warning "Conda pin step failed (exit=$exit) but pip toolchain is already compatible; continuing."
            } else {
                throw "Failed to pin pip toolchain via conda (exit=$exit)."
            }
        }
    } else {
        if (-not $toolchainOk) {
            # Fallback: best-effort pin via pip (less safe in conda envs, but better than failing outright).
            & $python -m pip install --upgrade "pip<24.1" "packaging<24" "setuptools<81" wheel
            if ($LASTEXITCODE -ne 0) { throw "Failed to pin pip toolchain via pip fallback (exit=$LASTEXITCODE)." }
        }
    }
    # Pre-install torch, torchaudio to satisfy downstream packages
    & $python -m pip install "torch==1.13.1" "torchaudio==0.13.1" --only-binary=:all:

    # Gym on macOS arm64 needs conda-forge (no matching PyPI wheels for this legacy version).
    & $python -c "import gym" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing gym=0.21.0 via conda-forge (freeze-installed)" -ForegroundColor DarkCyan
        try {
            $condaExe = Get-CondaExe
            if ($condaExe -and (Test-Path $condaExe) -and $NEW_ENV) {
                $prevSolver2 = $env:CONDA_SOLVER
                $env:CONDA_SOLVER = 'classic'
                & $condaExe install -n $NEW_ENV --yes --override-channels -c conda-forge -c defaults --solver classic --freeze-installed gym=0.21.0
                if ($LASTEXITCODE -ne 0) { throw "conda install gym=0.21.0 failed (exit=$LASTEXITCODE)" }
                # Re-pin after conda ops to ensure we don't end up with pip>=24.1
                & $condaExe install -n $NEW_ENV --yes --override-channels -c conda-forge -c defaults --solver classic --freeze-installed "pip<24.1" "packaging<24" "setuptools<81" wheel "numpy=1.23.5"
                if ($LASTEXITCODE -ne 0) { throw "conda repin toolchain failed (exit=$LASTEXITCODE)" }
                if ($prevSolver2) { $env:CONDA_SOLVER = $prevSolver2 } else { Remove-Item Env:CONDA_SOLVER -ErrorAction SilentlyContinue }
            }
        } catch { Write-Warning "Conda-forge gym install attempt failed: $_" }
    }
    # Verify gym import works before proceeding (single-line to avoid PS newline escaping)
    & $python -c "import gym" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Gym is not installed in env '$NEW_ENV'. Aborting algorithm run." }

    # Prevent pip from attempting to build gym from sdist when processing requirements
    $requirementsPath = Join-Path (Get-Location) 'requirements.txt'
    if (-not (Test-Path $requirementsPath)) { throw "requirements.txt not found at: $requirementsPath" }
    $prevOnlyBin = $Env:PIP_ONLY_BINARY
    $Env:PIP_ONLY_BINARY = "gym"
    & $python -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Initial requirements install failed; retrying once without PIP_ONLY_BINARY override."
        $Env:PIP_ONLY_BINARY = $prevOnlyBin
        & $python -m pip install -r $requirementsPath
    }
    $Env:PIP_ONLY_BINARY = $prevOnlyBin
    if ($LASTEXITCODE -ne 0) { throw "Failed to install epymarl requirements (exit=$LASTEXITCODE)." }

    # Keep numpy pinned; do not install unpinned numpy here.
    # Ensure sacred & matplotlib present (some runs failed earlier)
    & $python -c "import sacred" 2>$null; if ($LASTEXITCODE -ne 0) { & $python -m pip install sacred }
    & $python -c "import matplotlib" 2>$null; if ($LASTEXITCODE -ne 0) { & $python -m pip install "matplotlib==3.5.3" }

    # Uninstall the old gym-examples package and install the new one
    & $python -m pip uninstall gym-examples -y 2>$null

    $expectedVersion = Get-ExpectedGymExamplesVersion
    Write-EvaluationMessage -message "Expected gym-examples version (repo): $expectedVersion"

    Write-EvaluationMessage -message "Installing gym-examples==$expectedVersion from PyPI (strict)"
    $localGymExamplesDir = Join-Path $PSScriptRoot 'gym-examples'
    $localGymExamplesSetup = Join-Path $localGymExamplesDir 'setup.py'
    if (Test-Path $localGymExamplesSetup) {
        Write-EvaluationMessage -message "Installing gym-examples==$expectedVersion from local repo (editable)"
        & $python -m pip install --no-deps --no-build-isolation -e $localGymExamplesDir
        if ($LASTEXITCODE -ne 0) { throw "Failed to install local gym-examples from: $localGymExamplesDir" }
    } else {
        $maxAttempts = 6
        $sleepSeconds = 10
        $installed = $false
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            $installOutput = & $python -m pip install --no-cache-dir "gym-examples==$expectedVersion" 2>&1
            $exit = $LASTEXITCODE
            if ($exit -eq 0) {
                $installed = $true
                break
            }

            $outText = ($installOutput | Out-String)
            $looksLikeIndexLag = ($outText -match 'No matching distribution found for gym-examples==') -or
                                 ($outText -match 'Could not find a version that satisfies the requirement gym-examples==')

            if ($looksLikeIndexLag -and $attempt -lt $maxAttempts) {
                Write-Warning "gym-examples==$expectedVersion not visible on PyPI yet (attempt $attempt/$maxAttempts). Retrying in ${sleepSeconds}s..."
                Start-Sleep -Seconds $sleepSeconds
                $sleepSeconds = [Math]::Min($sleepSeconds * 2, 120)
                continue
            }

            throw "Failed to install gym-examples==$expectedVersion from PyPI. pip exit=$exit. Output: $outText"
        }
        if (-not $installed) {
            throw "Failed to install gym-examples==$expectedVersion from PyPI after $maxAttempts attempts. (PyPI propagation may be delayed.)"
        }
    }

    # Verify installed version matches expected
    Write-EvaluationMessage -message "Verifying installed gym_examples version..."
    $installedVersion = & $python -c "import gym_examples; print(gym_examples.__version__)"
    if ($LASTEXITCODE -ne 0 -or -not $installedVersion) {
        throw "Failed to import gym_examples after installation. Aborting."
    }
    $installedVersion = ($installedVersion | Out-String).Trim()
    if ($installedVersion -ne $expectedVersion) {
        throw "gym-examples version mismatch. Expected=$expectedVersion Installed=$installedVersion. Aborting to avoid wrong results."
    }
    $env:gym_examples_current_version = $installedVersion
    Write-EvaluationMessage -message "Gym_examples.version = $env:gym_examples_current_version (OK)"

# Helper: resolve latest run directory for an algo and map key
function Get-LatestRunDir {
    param(
        [Parameter(Mandatory=$true)][string]$Algo,                 # e.g., QMIX or QTRAN
        [Parameter(Mandatory=$true)][string]$MapKey,               # e.g., "gym_examples:WSNRouting-v0"
        [int]$Seed = -1                                            # if >= 0, filter by seed in dir name
    )
    $root = Join-Path (Get-Location) 'results/models'
    if (-not (Test-Path $root)) { return $null }
    # Folder names have ':' replaced with '_' (see run.py save path sanitization)
    $mapSafe = $MapKey -replace ':', '_'
    $algoLower = $Algo.ToLower()
    # Run folders start with algo name; be strict to avoid cross-algo selection.
    $candidates = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
        Where-Object { ($_.Name -match "^${algoLower}_") -and ($_.Name -like "*${mapSafe}*") }
    if (-not $candidates) { return $null }
    # Filter by seed if specified (dir name contains "seed<N>_")
    if ($Seed -ge 0) {
        $candidates = $candidates | Where-Object { $_.Name -match "seed${Seed}_" }
        if (-not $candidates) { return $null }
    }
    # Only accept directories that contain at least one numeric step subfolder
    $withSteps = @()
    foreach ($dir in $candidates) {
        $steps = Get-ChildItem -Path $dir.FullName -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^[0-9]+$' }
        if ($steps) { $withSteps += $dir }
    }
    if (-not $withSteps) { return $null }
    $latest = $withSteps | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    return $latest
}

# ──────────────────────────────────────────────────────────────
# PARALLEL TRAINING: QMIX, QTRAN, QPSOFL run simultaneously
# ──────────────────────────────────────────────────────────────
# Each algo is launched as a background process with its own log file.
# We wait for all to finish, then run evaluation passes in parallel.
$logDir = Join-Path (Get-Location) 'results'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$mapKey = "gym_examples:WSNRouting-v0"
# Read time_limit and t_max from gymma.yaml (single source of truth for all algos)
$gymmaYaml = Join-Path $epymarlDir 'src' 'config' 'envs' 'gymma.yaml'
if (-not (Test-Path $gymmaYaml)) { throw "gymma.yaml not found at $gymmaYaml. Cannot determine time_limit and t_max." }
$matchTL = Select-String -Path $gymmaYaml -Pattern '^\s*time_limit:\s*(\d+)' | Select-Object -First 1
if (-not $matchTL) { throw "Could not parse time_limit from $gymmaYaml" }
$timeLimit = [int]$matchTL.Matches[0].Groups[1].Value
$matchTM = Select-String -Path $gymmaYaml -Pattern '^\s*t_max:\s*(\d+)' | Select-Object -First 1
if (-not $matchTM) { throw "Could not parse t_max from $gymmaYaml" }
$tMax = [int]$matchTM.Matches[0].Groups[1].Value
$gapfTrainEpisodes = [int]($tMax / $timeLimit)  # e.g. 200000/100 = 2000 episodes
$scenarioTag = "n${NSensors}_r$([int]$CoverageRadius)"
Write-Host "  Scenario: n_sensors=$NSensors, coverage_radius=$CoverageRadius (tag=$scenarioTag)" -ForegroundColor Cyan

# --- Resolve conda run command fragments ---
$condaExe = Get-CondaExe
$epymarlDir = Get-Location   # we are already inside epymarl/

# Helper: build a self-contained script block string that conda-runs a training command
function Start-AlgoTraining {
    param(
        [string]$AlgoName,       # QMIX, QTRAN, QPSOFL
        [string]$ConfigName,     # qmix, qtran, or path to qpsofl.py
        [string]$LogFile,
        [string]$CondaExePath,
        [string]$EnvName,
        [string]$WorkDir,
        [string]$MapKey,
        [int]$TimeLimit,
        [int]$NSensorsArg = 70,
        [double]$CoverageRadiusArg = 35.0,
        [int]$SeedArg = 42,
        [switch]$IsQPSOFL
    )
    if ($IsQPSOFL) {
        $proc = Start-Process -FilePath $CondaExePath `
            -ArgumentList "run","-n",$EnvName,"--no-capture-output","--cwd",$WorkDir,"python","src/extended_baselines/qpsofl.py","--n-sensors","$NSensorsArg","--coverage-radius","$CoverageRadiusArg","--seed","$SeedArg","--steps","$TimeLimit","--episodes","$TestEpisodes" `
            -RedirectStandardOutput $LogFile `
            -RedirectStandardError "$LogFile.err" `
            -PassThru -NoNewWindow `
            -WorkingDirectory $WorkDir
        return $proc
    } else {
        $proc = Start-Process -FilePath $CondaExePath `
            -ArgumentList "run","-n",$EnvName,"--no-capture-output","--cwd",$WorkDir,"python","src/main.py","--config=$ConfigName","--env-config=gymma","with","env_args.time_limit=$TimeLimit","env_args.key=$MapKey","env_args.n_sensors=$NSensorsArg","env_args.coverage_radius=$CoverageRadiusArg","seed=$SeedArg" `
            -RedirectStandardOutput $LogFile `
            -RedirectStandardError "$LogFile.err" `
            -PassThru -NoNewWindow `
            -WorkingDirectory $WorkDir
        return $proc
    }
}

# ──────────────────────────────────────────────────────────────
# Parse seeds and configure GPU/thread settings
# ──────────────────────────────────────────────────────────────
$seedList = @($Seeds.Split(',') | ForEach-Object { [int]$_.Trim() })
Write-EvaluationMessage -message "MULTI-SEED TRAINING: $($seedList.Count) seeds [$($seedList -join ', ')], sequential execution, $TestEpisodes test episodes"

# ── GPU Detection ──
$cudaGpuCount = 0
$hasMPS = $false
try {
    $nvidiaSmi = & nvidia-smi --query-gpu=index --format=csv,noheader,nounits 2>$null
    if ($LASTEXITCODE -eq 0 -and $nvidiaSmi) {
        $cudaGpuIds = ($nvidiaSmi | ForEach-Object { $_.Trim() }) | Where-Object { $_ -match '^\d+$' }
        $cudaGpuCount = @($cudaGpuIds).Count
    }
} catch { $cudaGpuCount = 0 }
if ($cudaGpuCount -eq 0 -and -not $IsWindows) { $hasMPS = $true }

if ($cudaGpuCount -ge 2) {
    Write-Host "  [Accel] Detected $cudaGpuCount CUDA GPUs" -ForegroundColor DarkCyan
    $gpuQMIX  = $cudaGpuIds[0]
    $gpuQTRAN = $cudaGpuIds[1 % $cudaGpuCount]
    $env:OMP_NUM_THREADS = "4"; $env:MKL_NUM_THREADS = "4"; $env:OMP_DYNAMIC = "FALSE"; $env:PYTORCH_NUM_THREADS = "4"
} elseif ($cudaGpuCount -eq 1) {
    Write-Host "  [Accel] Detected 1 CUDA GPU — shared" -ForegroundColor DarkCyan
    $gpuQMIX = $null; $gpuQTRAN = $null
    $env:OMP_NUM_THREADS = "3"; $env:MKL_NUM_THREADS = "3"; $env:OMP_DYNAMIC = "FALSE"; $env:PYTORCH_NUM_THREADS = "3"
} else {
    $env:PYTORCH_MPS_HIGH_WATERMARK_RATIO = "0.0"
    $env:PYTORCH_MPS_LOW_WATERMARK_RATIO = "0.0"
    $env:PYTORCH_ENABLE_MPS_FALLBACK = "1"
    $env:OMP_NUM_THREADS = "3"; $env:MKL_NUM_THREADS = "3"; $env:OMP_DYNAMIC = "FALSE"; $env:PYTORCH_NUM_THREADS = "3"
    $gpuQMIX = $null; $gpuQTRAN = $null
    if ($hasMPS) {
        Write-Host "  [Accel] Apple MPS: watermark=disabled, threads=3/process, MPS_FALLBACK=1" -ForegroundColor DarkCyan
    } else {
        Write-Host "  [Accel] CPU-only: threads=3/process" -ForegroundColor DarkCyan
    }
}

# ──────────────────────────────────────────────────────────────
# TRAINING PHASE: Run algos SEQUENTIALLY per seed to avoid OOM
# ──────────────────────────────────────────────────────────────
# QTRAN alone uses ~14.7GB, QMIX ~1.4GB, QPSOFL ~0.2GB.
# Running them in parallel causes OOM (exit=137/SIGKILL on macOS).
# Order: QPSOFL (~2min) → QMIX (~20min) → QTRAN (~25min)
# Each algo finishes and releases memory before the next starts.
$seedResults = @{}  # key: "ALGO_seed" -> exit code

foreach ($seed in $seedList) {
    $seedTag = "_seed$seed"
    $seedIdx = [Array]::IndexOf($seedList, $seed) + 1
    Write-EvaluationMessage -message "TRAINING seed ${seedIdx}/$($seedList.Count): seed=$seed (sequential: QPSOFL -> QMIX -> QTRAN)"

    # --- QPSOFL (CPU-only, fastest, ~2 min, ~0.2GB) ---
    $env:ALGO_NAME = "QPSOFL"
    $env:SEED_TAG = $seedTag
    if ($null -ne $gpuQMIX) { Remove-Item Env:CUDA_VISIBLE_DEVICES -ErrorAction SilentlyContinue }
    $qpsoflLog = Join-Path $logDir "train_qpsofl_seed${seed}.log"
    Write-Host "  -> QPSOFL seed=$seed -> log: $qpsoflLog" -ForegroundColor Cyan
    $procQPSOFL = Start-AlgoTraining -AlgoName "QPSOFL" -IsQPSOFL -LogFile $qpsoflLog `
        -CondaExePath $condaExe -EnvName $NEW_ENV -WorkDir "$epymarlDir" -MapKey $mapKey -TimeLimit $timeLimit `
        -NSensorsArg $NSensors -CoverageRadiusArg $CoverageRadius -SeedArg $seed
    $procQPSOFL.WaitForExit()
    $seedResults["QPSOFL_seed$seed"] = $procQPSOFL.ExitCode
    $elapsed = try { [math]::Round(($procQPSOFL.ExitTime - $procQPSOFL.StartTime).TotalMinutes, 1) } catch { '?' }
    if ($procQPSOFL.ExitCode -eq 0) {
        Write-Host "  [OK] QPSOFL_seed$seed DONE (${elapsed}min)" -ForegroundColor Green
    } else {
        Write-Warning "  [FAIL] QPSOFL_seed$seed FAILED (exit=$($procQPSOFL.ExitCode), ${elapsed}min). See $qpsoflLog"
    }

    # --- QMIX (~20 min, ~1.4GB) ---
    $env:ALGO_NAME = "QMIX"
    $env:SEED_TAG = $seedTag
    if ($null -ne $gpuQMIX) { $env:CUDA_VISIBLE_DEVICES = "$gpuQMIX" }
    $qmixLog = Join-Path $logDir "train_qmix_seed${seed}.log"
    Write-Host "  -> QMIX  seed=$seed -> log: $qmixLog" -ForegroundColor Cyan
    $procQMIX = Start-AlgoTraining -AlgoName "QMIX" -ConfigName "qmix" -LogFile $qmixLog `
        -CondaExePath $condaExe -EnvName $NEW_ENV -WorkDir "$epymarlDir" -MapKey $mapKey -TimeLimit $timeLimit `
        -NSensorsArg $NSensors -CoverageRadiusArg $CoverageRadius -SeedArg $seed
    $procQMIX.WaitForExit()
    $seedResults["QMIX_seed$seed"] = $procQMIX.ExitCode
    $elapsed = try { [math]::Round(($procQMIX.ExitTime - $procQMIX.StartTime).TotalMinutes, 1) } catch { '?' }
    if ($procQMIX.ExitCode -eq 0) {
        Write-Host "  [OK] QMIX_seed$seed DONE (${elapsed}min)" -ForegroundColor Green
    } else {
        Write-Warning "  [FAIL] QMIX_seed$seed FAILED (exit=$($procQMIX.ExitCode), ${elapsed}min). See $qmixLog"
    }

    # --- QTRAN (~25 min, ~14.7GB) ---
    $env:ALGO_NAME = "QTRAN"
    $env:SEED_TAG = $seedTag
    if ($null -ne $gpuQTRAN) { $env:CUDA_VISIBLE_DEVICES = "$gpuQTRAN" }
    $qtranLog = Join-Path $logDir "train_qtran_seed${seed}.log"
    Write-Host "  -> QTRAN seed=$seed -> log: $qtranLog" -ForegroundColor Cyan
    $procQTRAN = Start-AlgoTraining -AlgoName "QTRAN" -ConfigName "qtran" -LogFile $qtranLog `
        -CondaExePath $condaExe -EnvName $NEW_ENV -WorkDir "$epymarlDir" -MapKey $mapKey -TimeLimit $timeLimit `
        -NSensorsArg $NSensors -CoverageRadiusArg $CoverageRadius -SeedArg $seed
    $procQTRAN.WaitForExit()
    $seedResults["QTRAN_seed$seed"] = $procQTRAN.ExitCode
    $elapsed = try { [math]::Round(($procQTRAN.ExitTime - $procQTRAN.StartTime).TotalMinutes, 1) } catch { '?' }
    if ($procQTRAN.ExitCode -eq 0) {
        Write-Host "  [OK] QTRAN_seed$seed DONE (${elapsed}min)" -ForegroundColor Green
    } else {
        Write-Warning "  [FAIL] QTRAN_seed$seed FAILED (exit=$($procQTRAN.ExitCode), ${elapsed}min). See $qtranLog"
    }
}
Write-EvaluationMessage -message "All training completed ($($seedList.Count) seeds, sequential execution)"

# ──────────────────────────────────────────────────────────────
# EVALUATION PHASE: Run eval for each seed sequentially
# ──────────────────────────────────────────────────────────────
$env:OMP_NUM_THREADS = "4"; $env:MKL_NUM_THREADS = "4"; $env:PYTORCH_NUM_THREADS = "4"
Write-Host "  [Accel] Eval phase: threads=4/process" -ForegroundColor DarkCyan

$ensembleScript = Join-Path (Join-Path $PSScriptRoot 'tools') 'ensemble_eval.py'

foreach ($seed in $seedList) {
    $seedTag = "_seed$seed"
    Write-Host "`n  === Evaluating seed=$seed ===" -ForegroundColor Magenta

    # QMIX eval
    if ($seedResults["QMIX_seed$seed"] -eq 0) {
        $env:ALGO_NAME = "QMIX"
        $env:SEED_TAG = $seedTag
        if ($null -ne $gpuQMIX) { $env:CUDA_VISIBLE_DEVICES = "$gpuQMIX" }
        $qmixLatest = Get-LatestRunDir -Algo 'QMIX' -MapKey $mapKey -Seed $seed
        if ($qmixLatest) {
            Write-Host "  -> QMIX eval seed=$seed (checkpoint: $($qmixLatest.FullName))" -ForegroundColor Cyan
            $qmixEvalLog = Join-Path $logDir "eval_qmix_seed${seed}.log"
            $procEval = Start-Process -FilePath $condaExe `
                -ArgumentList "run","-n",$NEW_ENV,"--no-capture-output","--cwd","$epymarlDir","python","src/main.py","--config=qmix","--env-config=gymma","with","env_args.time_limit=$timeLimit","env_args.key=$mapKey","env_args.n_sensors=$NSensors","env_args.coverage_radius=$CoverageRadius","`"checkpoint_path=$($qmixLatest.FullName)`"","evaluate=True","test_nepisode=$TestEpisodes","seed=$seed" `
                -RedirectStandardOutput $qmixEvalLog `
                -RedirectStandardError "$qmixEvalLog.err" `
                -PassThru -NoNewWindow `
                -WorkingDirectory "$epymarlDir"
            $procEval.WaitForExit()
            if ($procEval.ExitCode -eq 0) { Write-Host "  [OK] QMIX eval seed=$seed DONE" -ForegroundColor Green }
            else { Write-Warning "  [FAIL] QMIX eval seed=$seed (exit=$($procEval.ExitCode))" }
        } else { Write-Warning "QMIX checkpoint for seed=$seed not found; skipping." }
    }

    # QTRAN eval
    if ($seedResults["QTRAN_seed$seed"] -eq 0) {
        $env:ALGO_NAME = "QTRAN"
        $env:SEED_TAG = $seedTag
        if ($null -ne $gpuQTRAN) { $env:CUDA_VISIBLE_DEVICES = "$gpuQTRAN" }
        $qtranLatest = Get-LatestRunDir -Algo 'QTRAN' -MapKey $mapKey -Seed $seed
        if ($qtranLatest) {
            Write-Host "  -> QTRAN eval seed=$seed (checkpoint: $($qtranLatest.FullName))" -ForegroundColor Cyan
            $qtranEvalLog = Join-Path $logDir "eval_qtran_seed${seed}.log"
            $procEval = Start-Process -FilePath $condaExe `
                -ArgumentList "run","-n",$NEW_ENV,"--no-capture-output","--cwd","$epymarlDir","python","src/main.py","--config=qtran","--env-config=gymma","with","env_args.time_limit=$timeLimit","env_args.key=$mapKey","env_args.n_sensors=$NSensors","env_args.coverage_radius=$CoverageRadius","`"checkpoint_path=$($qtranLatest.FullName)`"","evaluate=True","test_nepisode=$TestEpisodes","seed=$seed" `
                -RedirectStandardOutput $qtranEvalLog `
                -RedirectStandardError "$qtranEvalLog.err" `
                -PassThru -NoNewWindow `
                -WorkingDirectory "$epymarlDir"
            $procEval.WaitForExit()
            if ($procEval.ExitCode -eq 0) { Write-Host "  [OK] QTRAN eval seed=$seed DONE" -ForegroundColor Green }
            else { Write-Warning "  [FAIL] QTRAN eval seed=$seed (exit=$($procEval.ExitCode))" }
        } else { Write-Warning "QTRAN checkpoint for seed=$seed not found; skipping." }
    }

    # Ensemble Max eval (requires both QMIX and QTRAN for this seed)
    if (-not $SkipEnsemble -and $seedResults["QMIX_seed$seed"] -eq 0 -and $seedResults["QTRAN_seed$seed"] -eq 0) {
        $env:SEED_TAG = $seedTag
        $qmixLatest = Get-LatestRunDir -Algo 'QMIX' -MapKey $mapKey -Seed $seed
        $qtranLatest = Get-LatestRunDir -Algo 'QTRAN' -MapKey $mapKey -Seed $seed
        if ($qmixLatest -and $qtranLatest -and (Test-Path $ensembleScript)) {
            Write-Host "  -> Ensemble Max eval seed=$seed" -ForegroundColor Cyan
            $ensembleLog = Join-Path $logDir "eval_ensemble_max_seed${seed}.log"
            & $python $ensembleScript --mode max --n-episodes $TestEpisodes --seed $seed `
                --n-sensors $NSensors --coverage-radius $CoverageRadius --time-limit $timeLimit `
                --qmix-model $qmixLatest.FullName --qtran-model $qtranLatest.FullName `
                2>&1 | Tee-Object -FilePath $ensembleLog
            if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] Ensemble Max seed=$seed DONE" -ForegroundColor Green }
            else { Write-Warning "  [FAIL] Ensemble Max seed=$seed (exit=$LASTEXITCODE)" }
        }
    } elseif ($SkipEnsemble) {
        Write-Host "  -> Ensemble Max SKIPPED (-SkipEnsemble)" -ForegroundColor DarkGray
    }

    # GAPF train+eval (requires QMIX and QTRAN checkpoints for this seed)
    if ($seedResults["QMIX_seed$seed"] -eq 0 -and $seedResults["QTRAN_seed$seed"] -eq 0) {
        $env:SEED_TAG = $seedTag
        $gapfScript = Join-Path $epymarlDir 'GAPF_hybrid_model.py'
        if (Test-Path $gapfScript) {
            Write-Host "  -> GAPF train+eval seed=$seed" -ForegroundColor Cyan
            $gapfLog = Join-Path $logDir "gapf_seed${seed}.log"
            & $python $gapfScript --mode cas --seed $seed `
                --train-episodes $gapfTrainEpisodes --eval-episodes $TestEpisodes `
                --time-limit $timeLimit --n-sensors $NSensors --coverage-radius $CoverageRadius `
                2>&1 | Tee-Object -FilePath $gapfLog
            if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] GAPF seed=$seed DONE" -ForegroundColor Green }
            else { Write-Warning "  [FAIL] GAPF seed=$seed (exit=$LASTEXITCODE)" }
        }
    }
}
Write-EvaluationMessage -message "All evaluations completed ($($seedList.Count) seeds)"

# ──────────────────────────────────────────────────────────────
# AGGREGATION: Compute mean ± std across seeds
# ──────────────────────────────────────────────────────────────
$aggregateScript = Join-Path (Join-Path $PSScriptRoot 'tools') 'aggregate_seeds.py'
if (Test-Path $aggregateScript) {
    Write-Host "  Aggregating results across seeds..." -ForegroundColor Cyan
    & $python $aggregateScript --seeds $Seeds
    if ($LASTEXITCODE -eq 0) { Write-Host "  [OK] Aggregation DONE" -ForegroundColor Green }
    else { Write-Warning "Aggregation failed (exit=$LASTEXITCODE)" }
}

# Copy metrics into repo-level results/data so tools/TSMixer (run from repo root) can find them.
try {
    $epymarlDataDir = Join-Path (Join-Path (Get-Location) 'results') 'data'
    $repoDataDir = Join-Path (Join-Path $PSScriptRoot 'results') 'data'
    New-Item -ItemType Directory -Path $repoDataDir -Force | Out-Null
    if (Test-Path $epymarlDataDir) {
        Get-ChildItem -Path $epymarlDataDir -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in @('.npy', '.txt') } |
            ForEach-Object { Copy-Item -Path $_.FullName -Destination (Join-Path $repoDataDir $_.Name) -Force }
    }
} catch {
    Write-Warning "Failed to copy metrics into repo-level results/data: $_"
}

Remove-Item -Path Env:ALGO_NAME -ErrorAction SilentlyContinue
Remove-Item -Path Env:SEED_TAG -ErrorAction SilentlyContinue
Remove-Item -Path Env:gym_examples_current_version -ErrorAction SilentlyContinue

# Visualize the results (auto-save to Results_Graphics, no blocking)
$resultsGraphicsDir = Join-Path $PSScriptRoot 'Results_Graphics'
& $python display_results.py --n-sensors $NSensors --coverage-radius $CoverageRadius --seeds $Seeds --output-dir $resultsGraphicsDir

} finally {
    $env:PIP_DISABLE_PIP_VERSION_CHECK = $prevPipCheck
    Pop-Location
}