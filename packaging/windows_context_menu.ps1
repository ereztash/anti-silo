param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath,
    [switch]$Remove
)

$menuKey = "HKCU:\Software\Classes\Directory\shell\AntiSiloScan"

if ($Remove) {
    Remove-Item -LiteralPath $menuKey -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed the Anti-Silo folder context-menu entry."
    exit 0
}

$resolvedExecutable = (Resolve-Path -LiteralPath $ExecutablePath).Path
New-Item -Path $menuKey -Force | Out-Null
Set-ItemProperty -Path $menuKey -Name "MUIVerb" -Value "Scan with Anti-Silo"
Set-ItemProperty -Path $menuKey -Name "Icon" -Value $resolvedExecutable
New-Item -Path "$menuKey\command" -Force | Out-Null
Set-ItemProperty -Path "$menuKey\command" -Name "(default)" -Value ('"{0}" --open-path "%V"' -f $resolvedExecutable)

Write-Host "Added 'Scan with Anti-Silo' to folder context menus for the current Windows user."
