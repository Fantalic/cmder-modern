# ConEmuHk child-exit terminal-mode guard (patched DLLs)

Rebuilds of `ConEmuHk64.dll` / `ConEmuHk.dll` with one behavioral change:
`CEAnsi::DoneTermMode()` now only runs when the dying process is the one
that actually enabled the terminal mode itself
(`CEAnsi::gWasXTermModeSet[tmc_TerminalType].pid == GetCurrentProcessId()`).

## Why

ConEmuHk is injected into every console child. `InitTermMode()` reads the
*shared* output-buffer mode; any child spawned inside a full-screen TUI
whose parent enabled `ENABLE_VIRTUAL_TERMINAL_PROCESSING` reports "XTerm
mode on" as its own and, on exit, `DoDllStop` → `DoneTermMode` →
`ChangeTermMode(tmc_TerminalType, te_win32)` flips the whole console to
Win32 emulation. The TUI's once-negotiated `?1000h…` mouse routing dies
until the tab is closed (keys survive; mouse dies) - reproduced with
`cmd /c ping` children, fully logged in `.ai/diagnostics/child_clip_result.log`.
This is the root of [Maximus5/ConEmu#2246].

## Build recipe (verified)

```
git clone --depth 1 https://github.com/Maximus5/ConEmu.git
cd ConEmu\src
git submodule update --init src/modules/minhook src/modules/terminals
git apply ..\ConEmuHk-doneExit-pid-guard.patch
call "C:\BuildTools\Common7\Tools\VsDevCmd.bat" -no_logo
msbuild ConEmuHk.vcxproj -p:Configuration=Release -p:Platform=x64  -p:PlatformToolset=v143
msbuild ConEmuHk.vcxproj -p:Configuration=Release -p:Platform=x86  -p:PlatformToolset=v143
```

## Deployment

Copy the built `ConEmuHk64.dll` + `ConEmuHk.dll` into
`vendor\conemu-maximus5\ConEmu\` while no ConEmu window is running (the DLL
is locked otherwise). Original stock binaries are preserved next to the
patched ones (`*.stock.dll`).

Base upstream commit of this rebuild: Maximus5/ConEmu c8cebb9
(2026 master, "Added Ctrl+Shift+M default hotkey ...", fresh clone).
