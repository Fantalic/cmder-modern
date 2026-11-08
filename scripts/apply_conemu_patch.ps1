# Apply the rebuilt ConEmuHk DLLs on top of a freshly extracted ConEmu vendor
# set. Run after scripts\build.ps1. The patched DLLs keep the terminal-mode
# state of the parent TUI alive when unrelated console children exit
# (root cause of the "mouse dies inside full-screen TUIs" defect,
# reproduced and documented in documentation.md).
#
# Usage: powershell -File scripts\apply_conemu_patch.ps1
# Honors the same layout ConEmu uses: vendor\conemu-maximus5\ConEmu\

$ErrorActionPreference = "Stop"

$patchDir = Join-Path $PSScriptRoot "conemu-patch"
$target   = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "vendor\conemu-maximus5\ConEmu"

if (-not (Test-Path (Join-Path $target "ConEmuHk64.dll"))) {
    # shell legacy layout (files beside the exe)
    $alt = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "vendor\conemu-maximus5"
    if (Test-Path (Join-Path $alt "ConEmuHk64.dll")) { $target = $alt }
}

if (-not (Test-Path (Join-Path $target "ConEmuHk64.dll"))) {
    Write-Warning "apply_conemu_patch: vendor ConEmu not extracted yet (run build.ps1 first); skipping."
    exit 0
}

if (Get-Process ConEmu64, ConEmu -ErrorAction SilentlyContinue) {
    Write-Warning "apply_conemu_patch: ConEmu is running - DLLs are locked. Close ConEmu windows and re-run."
    exit 1
}

foreach ($dll in @("ConEmuHk.dll", "ConEmuHk64.dll")) {
    $src = Join-Path $patchDir $dll
    $dst = Join-Path $target $dll
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Verbose "applied $dll -> $dst"
    }
}

Write-Host "ConEmuHk patch applied (terminal-mode child-exit guard, cf. Maximus5/ConEmu#2246)."
