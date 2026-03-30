param(
    [Parameter(Mandatory=$false)][string]$InputMd = "./docs/Model_Stats_Report.md",
    [Parameter(Mandatory=$false)][string]$OutputPdf = "./docs/Model_Stats_Report.pdf",
    [Parameter(Mandatory=$false)][string]$PdfEngine = "wkhtmltopdf"
)

function Test-Command {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

if (!(Test-Path $InputMd)) {
    Write-Error "Input Markdown not found: $InputMd"
    exit 1
}

if (!(Test-Command pandoc)) {
    Write-Host "Pandoc not found. Install from https://pandoc.org/install.html" -ForegroundColor Yellow
    exit 1
}

$engineArgs = @()
if ($PdfEngine -ieq "wkhtmltopdf") {
    if (Test-Command wkhtmltopdf) {
        $engineArgs = @("--pdf-engine=wkhtmltopdf", "-V", "margin-top=15mm", "-V", "margin-bottom=15mm", "-V", "margin-left=12mm", "-V", "margin-right=12mm")
    } else {
        Write-Host "wkhtmltopdf not found; falling back to default PDF engine. Install from https://wkhtmltopdf.org/ for best results." -ForegroundColor Yellow
    }
} elseif ($PdfEngine -ieq "xelatex") {
    $engineArgs = @("--pdf-engine=xelatex")
}

$pandocArgs = @($InputMd, "-o", $OutputPdf) + $engineArgs

Write-Host "Running: pandoc $($pandocArgs -join ' ')" -ForegroundColor Cyan
pandoc @pandocArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "PDF generated: $OutputPdf" -ForegroundColor Green
} else {
    Write-Error "Failed to generate PDF. Check that the engine is installed and try again."
}
