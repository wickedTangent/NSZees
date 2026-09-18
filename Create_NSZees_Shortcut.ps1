$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSCommandPath
$shortcutPath = Join-Path $root 'NSZees.lnk'
$cmdLauncher = Join-Path $root 'NSZees-NoConsole.cmd'
$iconPath = Join-Path $root 'assets\icon.ico'

if (-not (Test-Path -Path $cmdLauncher -PathType Leaf)) {
    throw "Missing launcher: $cmdLauncher"
}

$wsh = New-Object -ComObject WScript.Shell
$lnk = $wsh.CreateShortcut($shortcutPath)
$lnk.TargetPath = $cmdLauncher
$lnk.Arguments = ''
$lnk.WorkingDirectory = $root

if (Test-Path -Path $iconPath -PathType Leaf) {
    $lnk.IconLocation = "$iconPath,0"
}

$lnk.Description = 'Launch NSZees'
$lnk.Save()

Write-Host "Created shortcut: $shortcutPath"