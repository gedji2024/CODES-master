param(
	[switch]$IncludeVenv,             # also remove myenv/ (virtual environment)
	[switch]$IncludeResults,          # also remove results/ and epymarl/results/
	[switch]$Hard,                    # also remove build artifacts in subprojects aggressively
	[switch]$ArchiveTSMixer = $true,  # move TSMixer variant files to epymarl/archive instead of delete
	[switch]$WhatIf = $true,          # preview by default; override with -Force or -WhatIf:$false
	[switch]$Force                    # set to perform real deletions (alias for -WhatIf:$false)
)

# Normalize dry-run flag: if -Force passed, disable WhatIf preview
if ($Force) { $WhatIf = $false }

function Remove-PathSafe {
	param(
		[string]$Path
	)
	if (Test-Path $Path) {
		if ($WhatIf) {
			Write-Host "[DRY-RUN] Would remove: $Path"
		} else {
			Write-Host "[REMOVE] $Path"
			Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Path
		}
	}
}

function Remove-Glob {
	param(
		[string]$Pattern,
		[switch]$Recurse = $true
	)
	$items = Get-ChildItem -Force -Recurse:$Recurse -ErrorAction SilentlyContinue -Filter $Pattern
	foreach ($it in $items) {
		Remove-PathSafe -Path $it.FullName
	}
}

Write-Host "[CLEAN] Python bytecode & caches"
Remove-Glob -Pattern "__pycache__"
Remove-Glob -Pattern "*.pyc"
Remove-Glob -Pattern "*.pyo"
Remove-Glob -Pattern ".pytest_cache"
Remove-Glob -Pattern ".mypy_cache"
Remove-Glob -Pattern ".ipynb_checkpoints"

Write-Host "[CLEAN] Build artifacts"
Remove-PathSafe -Path "build"
Remove-PathSafe -Path "dist"
Remove-Glob -Pattern "*.egg-info"
if ($Hard) {
	# Subproject build outputs
	Remove-PathSafe -Path "gym-examples/build"
	Remove-Glob -Pattern "*.egg-info"
}

Write-Host "[CLEAN] Logs & coverage"
Remove-Glob -Pattern "*.log"
Remove-PathSafe -Path ".coverage"
Remove-PathSafe -Path "coverage.xml"

if ($IncludeResults) {
	Write-Host "[CLEAN] Results directories (requested)"
	Remove-PathSafe -Path "results"
	Remove-PathSafe -Path "epymarl/results"
}

if ($IncludeVenv) {
	Write-Host "[CLEAN] Virtual environment myenv (requested)"
	Remove-PathSafe -Path "myenv"
}

if ($ArchiveTSMixer) {
	Write-Host "[ARCHIVE] TSMixer variant files"
	$archiveDir = Join-Path "epymarl" "archive"
	if (-not $WhatIf) {
		New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null
	}
	$variants = Get-ChildItem -Path "epymarl" -Filter "TSMixer_hybrid_model_3.*.py" -ErrorAction SilentlyContinue
	foreach ($v in $variants) {
		$dest = Join-Path $archiveDir $v.Name
		if ($WhatIf) {
			Write-Host "[DRY-RUN] Would move: $($v.FullName) -> $dest"
		} else {
			Write-Host "[MOVE] $($v.FullName) -> $dest"
			Move-Item -Force $v.FullName $dest
		}
	}
}

if ($WhatIf) {
	Write-Host "[CLEAN] Complete (dry-run). Use -Force to execute deletions."
} else {
	Write-Host "[CLEAN] Complete. Deletions executed."
}
