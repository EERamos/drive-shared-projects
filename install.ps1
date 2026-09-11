# Copies the skill into the user's Claude Code skills folder.
# Usage: .\install.ps1 [-Destination <folder>]
param(
    [string]$Destination = (Join-Path $HOME ".claude\skills\drive-shared-projects")
)
$ErrorActionPreference = "Stop"
$dest = $Destination
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($item in @("SKILL.md", "templates", "references", "scripts")) {
    $src = Join-Path $PSScriptRoot $item
    Copy-Item -Path $src -Destination $dest -Recurse -Force
}
Write-Host "Installed drive-shared-projects to $dest"
