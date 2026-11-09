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

---

# Unicode 16 width table for ConEmu64.exe (`wcwidth-unicode16-wide.patch`)

ConEmu decides whether a character occupies one or two cells with
`is_char_cjk()` in `src/common/wcwidth.cpp`. Upstream implements it as a
hand-written range list that predates the emoji blocks in Unicode: it covers
1F300..1F5FF but not 1F600..1F64F, and it misses the BMP emoji that modern
TUIs print (U+2705 WHITE HEAVY CHECK MARK and friends). The result is a
half-cell drift between the TUI's own width calculation (go-runewidth /
lipgloss) and the terminal's.

`gen_wide_table.py` replaces that function with the East Asian Wide and
Fullwidth intervals of Unicode 16.0.0 (122 ranges), taken from the official
`EastAsianWidth.txt`. Ambiguous (A) characters deliberately stay one cell.

## Regenerate the patch

```
python scripts\conemu-patch\gen_wide_table.py ^
    --eaw .ai\fonts-donor\EastAsianWidth-16.0.0.txt ^
    --wcwidth <ConEmu-checkout>\src\common\wcwidth.cpp
```

The generator rewrites the function body in place, keeps the file's BOM and
CRLF line endings, and prints the unified diff.

## Build

```
git clone --depth 1 --branch v23.07.24 https://github.com/Maximus5/ConEmu.git
cd ConEmu
git submodule update --init --recursive
git apply ..\cmder-fork\scripts\conemu-patch\wcwidth-unicode16-wide.patch
cd src
call "C:\BuildTools\Common7\Tools\VsDevCmd.bat" -no_logo -arch=amd64
msbuild ConEmu.vcxproj -p:Configuration=Release -p:Platform=x64 -p:PlatformToolset=v143 -m -v:m
```

Result: `ConEmu\Release\ConEmu64.exe` (FileVersion 230724, identical to the
stock binary apart from the width table).

## Deployment

The rebuilt `ConEmu64.exe` replaces `vendor\conemu-maximus5\ConEmu64.exe`; the
stock binary is kept beside it as `ConEmu64.stock.exe`. Vendor executables are
ignored by git, so the patched binary travels with the release archive, not
with the source tree.

## Effect

Only `is_char_cjk()` changes: the old range list is replaced by a generated
bisection table. `get_wcwidth()` itself (combining characters, control
characters) is untouched.

