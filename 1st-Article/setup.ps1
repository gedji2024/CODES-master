# setup.ps1
param (
    [string]$filePath = ".\gym-examples\gym_examples\__init__.py",
    [string]$dirPath = ".\gym-examples"
)

# Read the content of the file
$content = Get-Content -Path $filePath

# Extract the current version number
$oldVersion = [regex]::match($content, '__version__ = "(\d+.\d+.\d+)"').Groups[1].Value

# Split the version into parts
$versionParts = $oldVersion.Split('.')

# Increment the last part of the version number
$versionParts[-1] = [int]$versionParts[-1] + 1

# Combine the version parts back into a string
$newVersion = $versionParts -join '.'

# Replace the old version with the new version
$content = $content -replace "__version__ = `"$oldVersion`"", "__version__ = `"$newVersion`""

# Write the updated content back to the file
$content | Set-Content -Path $filePath

# Delete the directories
Remove-Item -Path "$dirPath\gym_examples.egg-info" -Recurse -Force -ErrorAction Ignore
Remove-Item -Path "$dirPath\dist" -Recurse -Force -ErrorAction Ignore
Remove-Item -Path "$dirPath\build" -Recurse -Force -ErrorAction Ignore