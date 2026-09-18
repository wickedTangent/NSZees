$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSCommandPath
$pythonBackup = Join-Path $root 'bin_py3.10.5_nsz5.0.0_backup'
$nszBackup = Join-Path $root 'bin_nsz_4.6.1_backup'

if (-not (Test-Path -Path $pythonBackup -PathType Container)) {
    throw "Backup not found: $pythonBackup`nNothing to restore from - is bin/ already the master release?"
}
if (-not (Test-Path -Path $nszBackup -PathType Container)) {
    throw "Backup not found: $nszBackup`nNothing to restore from - is bin/ already the master release?"
}

Write-Host "Restoring the full Python 3.10.5 environment from $pythonBackup ..."

$bin = Join-Path $root 'bin'
if (Test-Path -Path $bin -PathType Container) {
    Remove-Item -Path $bin -Recurse -Force -Confirm:$false
}
Copy-Item -Path $pythonBackup -Destination $bin -Recurse -Force

Write-Host "Overlaying nsz 4.6.1 from $nszBackup ..."

Copy-Item -Path (Join-Path $nszBackup 'nsz.exe') -Destination (Join-Path $bin 'nsz.exe') -Force
Copy-Item -Path (Join-Path $nszBackup 'version.txt') -Destination (Join-Path $bin 'version.txt') -Force

$sitePackages = Join-Path $bin 'Lib\site-packages'
Remove-Item -Path (Join-Path $sitePackages 'nsz') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $sitePackages 'nsz-5.0.0.dist-info') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $bin 'run_nsz.py') -Force -ErrorAction SilentlyContinue

Copy-Item -Path (Join-Path $nszBackup 'nsz-package') -Destination (Join-Path $sitePackages 'nsz') -Recurse -Force
Copy-Item -Path (Join-Path $nszBackup 'nsz-4.6.1.dist-info') -Destination (Join-Path $sitePackages 'nsz-4.6.1.dist-info') -Recurse -Force

Write-Host "Restored bin/ to the exact Python 3.10.5 + nsz 4.6.1 state master was tested against."
Write-Host "Note: this only restores files - switch to the master branch yourself (git checkout master) for the matching source code."
