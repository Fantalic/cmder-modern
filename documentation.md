# Modernized cmder fork — documentation

Fork base: upstream cmderdev/cmder @ 1d6777b, built on 2026-11-08 for Windows 10/11.

## Why this fork exists

Modern CLI tools (braille spinners, Nerd Font icons, UTF-8 output) were broken in classic cmder because of
three independent causes. All three are fixed here:

| Cause | Classic cmder | This fork |
|---|---|---|
| Terminal font | Consolas (no Braille, no Nerd glyphs; half-block art aligned, though) | **CaskaydiaCove NF** (Cascadia Code base) vendored + auto-registered per-user; line-art stays pixel-perfect *and* glyphs/icons draw |
| Output code page | system OEM (cp850 etc.) mangles UTF-8 | ConEmu `CmdOutputCP=65001` (UTF-8) |
| Clink | 1.9.5 (Dec 2025) | **1.9.35** (Oct 2026) — includes DECSET sync-output fixes for prompt/suggestion flicker |

Fonts and ConEmu cell math — why the default is CaskaydiaCove NF: ConEmu's GDI renderer fits glyphs
into cells using the font's vertical metrics. Fonts whose baseline overshoots the requested pixel height
(e.g. JetBrains Mono: ~22 px of metrics at a 16 px cell) land the baseline *fractionally* inside the cell,
which displaces half-block characters (`U+2580/2584/258C/2590`) by one raster line — invisible in normal
text, glaring in terminal block art (the opencode wordmark, lattice tables, progress bars). CaskaydiaCove
NF uses terminal-tuned metrics that fit cells exactly, keeping block art aligned; NF glyphs (icons) draw
identically in both. JetBrains Mono NF ships anyway as an opt-in for users who prefer its look and accept
the 1-px seams, or use other renderers (Windows Terminal handles it fine).

## What changed vs upstream

1. **`vendor/sources.json`** — refreshed pins:
   - clink 1.9.5 → **1.9.35**, clink-completions 0.6.7 → **0.6.9** (maintained again: dotnet/kubectl/scoop/chocolatey/yarn
     completion modules), git-for-windows 2.52 → **2.56.0.4**, ConEmu stays 23.07.24 (this *is* the newest ConEmu stable;
     the dormant project's Alpha channel is older than stable).
   - Removed the vendored windows-terminal entry (~30 MB dead weight; Windows Terminal integration is untouched and still
     possible via the cmder wiki).
2. **Bundled fonts + auto-registration**
   - `vendor/fonts/` carries 4 weights each (Regular/Bold/Italic/BoldItalic) of **CaskaydiaCove NF** (`patched-fonts/CascadiaCode`,
     the default) and **JetBrains Mono NF** (`patched-fonts/JetBrainsMono/Ligatures`, opt-in), plus the OFL licenses
     (CascadiaCode-OFL.txt, JetBrainsMono-OFL.txt), all fetched from ryanoasis/nerd-fonts tag v3.5.1 — note: NF v3 family
     names are the short forms (**"CaskaydiaCove NF"**, **"JetBrainsMono NF"**), not the v2 long names; GDI enumerates the
     ID-1 name table entry, so all config references must use the short names verbatim.
   - `vendor/bin/cmder_font.cmd` installs per-user (copy to `%LOCALAPPDATA%\Microsoft\Windows\Fonts` + one `HKCU` registry
     value per file with the style in the value name — no admin needed on Win10 1809+), stamps `config\fonts_installed`,
     refreshes GDI with `AddFontResourceW` + `WM_FONTCHANGE`, and becomes a no-op afterwards.
   - The launcher (`cmder.exe`) runs the same registration *before* ConEmu starts, so even the very first session renders
     glyphs (see `RegisterBundledFonts` in `launcher/src/CmderLauncher.cpp`).
3. **`vendor/ConEmu.xml.default`** — `FontName`/`ConsoleFontName` = `CaskaydiaCove NF`, `FontName2` = `JetBrainsMono NF`
   (fallback), `CmdOutputCP` = 65001, `DisableMouse` = 0 (mouse events forwarded to apps that request mouse tracking —
   wheel scrolling, marking and clicking inside TUIs like opencode/micro; plain text selection keeps working via the
   ConEmu selection modifier, Shift + drag, whenever the app owns the mouse). ANSI processing (`ProcessAnsi`) was already
   on upstream.
4. **`vendor/clink_settings.default`** — enables inline autosuggest (`autosuggest.enable = True`, strategy
   `history popups files_end_with completion`) on top of upstream defaults. Tab-completion behavior unchanged.
5. **Modern CLI toolset, vendored flat in `bin\`** (upstream's documented runtime drop-in; `.gitignore`d):
   fzf 0.75.0, eza 0.23.5, bat 0.26.1, ripgrep 15.2.0, fd 10.5.2, zoxide 0.10.0.
   - `vendor/init.bat` ends with a fork guarantee block that force-prepends `bin` and `vendor\bin` so the bundled tools
     shadow older system copies (e.g. a stale Chocolatey fzf was otherwise winning because upstream's recursive path
     enhancement can order things unpredictably).
   - `config\fzf.lua`, `config\fzf_git.lua`, `config\fzf_rg.lua` from chrisant996/clink-fzf: Ctrl+T fuzzy file picker,
     Ctrl+R fuzzy history, git helpers inside cmd.
   - Default aliases redefined in `vendor/user_aliases.cmd.default`: `ls` → eza with icons, `l` → eza long list with
     git status, `cat` → bat (no paging). Delete the generated `config\user_aliases.cmd` to get upstream behavior back.
   - zoxide ships as a binary but has **no cmd integration by design** (`zoxide init` supports bash/fish/powershell/…
     but not cmd); a community shim could be added later if wanted.
6. **Icons redesigned** (`scripts/generate_icons.py`): parametric flat rounded-square tiles, vertical gradient,
   λ typeset in the bundled font, all upstream icon names/variants rewritten (`cmder.ico` + 6 color variants,
   PNGs at 16/32/48/256). Each size is rendered directly (supersampled), tiny sizes auto-switch to the Bold face.
7. **Launcher can be built without Visual Studio** — a MinGW/w64devkit path works:
   - `winres.h` shim (tiny header, only for toolchains without the MSVC resource header) and `app_manifest.rc`
     (RT_MANIFEST embedding for windres; keeps upstream's mt.exe flow untouched for MSVC builds).
   - `scripts/build.ps1` `-Compile` still targets MSBuild; the gcc flow used during development:
     `windres -c65001 -Ilauncher/src launcher/src/resource.rc -o build_res.o`,
     `g++ -O1 -std=c++17 -municode -mwindows -static -DUNICODE -D_UNICODE -DWIN32 -DNDEBUG -D_WINDOWS -D_WIN32_WINNT=0x0601
     -D_WIN32_IE=0x0600 -Ilauncher/src -c launcher/src/CmderLauncher.cpp`, then link the three objects with
     `-lshlwapi -lcomctl32 -lole32 -luuid -luser32 -lshell32 -ladvapi32 -lkernel32`.
   - The portable fallback for MSVC's `WIDEN(__FUNCTION__)` macro-awareness widens `__FILE__` instead on MinGW.

## Build from scratch (this machine)

1. `.\scripts\build.ps1` — downloads + extracts all `vendor/sources.json` entries (7-Zip must be installed; PS 5.1
   quirk: invoke with `& .\scripts\build.ps1`, *not* `powershell -File`, or `$PSScriptRoot` resolves empty in the
   `[CmdletBinding]` param block).
2. Regenerate icons (optional): `python scripts\generate_icons.py` (Pillow).
3. Pick your launcher build: MSBuild (`.\scripts\build.ps1 -Compile`) or the gcc commands above; copy
   `launcher\cmder.exe` to the repo root.

## Known quirks discovered along the way

- git-for-windows 2.56's one-time `post-install.bat` self-deletes after first boot; the "batch file not found" message on
  the very first run is its own cleanup noise, not an error.
- `ConEmu.xml.default` is only adopted while `vendor\conemu-maximus5\ConEmu.xml` is absent (and the
  `config\user-ConEmu.xml` dance does not refresh it once both exist) — if you change defaults, delete those two files
  for a clean test.
- ConEmu's font-failure dialog ("font is not registered for use in console") is what you see when `FontName` in the
  *loaded* XML does not match the GDI family name — the short `… NF` name is the fix.

## Licensing & attribution (for publication)

| Component | License | Notes |
|---|---|---|
| cmder code (launcher, init, lua, scripts, this fork's changes) | MIT (LICENSE) | Upstream copyright notice retained; all fork changes under the same MIT |
| ConEmu (vendored) | BSD | As vendored upstream |
| Clink | GPL-3.0 | Vendored binary; source obtainable from github.com/chrisant996/clink, satisfying binary-distribution obligations |
| git-for-windows | GPLv2 | As vendored upstream |
| CaskaydiaCove NF (vendored TTFs) | OFL 1.1 (vendor/fonts/CascadiaCode-OFL.txt) | Redistribution permitted with the license kept |
| JetBrains Mono NF (vendored TTFs) | OFL 1.1 (vendor/fonts/JetBrainsMono-OFL.txt) | Redistribution permitted with the license kept |
| fzf, eza, bat, ripgrep, fd, zoxide | MIT / Apache-2.0 | Runtime `bin\` binaries (release zips); binaries not committed to git, license info lives here |
| Icons | MIT | Drawn from scratch programmatically; not derived from the upstream PSD; λ typeset in the OFL font (allowed use) |

Naming etiquette: this fork is "a modernized fork of Cmder" — do not present it as official upstream; cmder name is
upstream's project identity even without a formal trademark.

## Mouse break inside full-screen TUIs after console children (fixed)

Symptom: inside opencode, after the first copy interaction (mark + right-click, which spawns
`powershell.exe` as a console child for the clipboard write), mouse scrolling and selection die and stay
dead until the tab is closed. Keyboard keeps working.

Root-cause chain (all verified experimentally, evidence in `.ai/diagnostics/`):
1. opencode's clipboard write spawns `powershell.exe` as a *console child* of the TUI (`clipboard.ts`
   `copyCommand`, spawned with piped stdio but still attaching to the TUI's console).
2. When that child exits, ConEmu's hook DLL resets shared console state on child termination
   (upstream clone of Maximus5/ConEmu#2246: `ConEmuHk` `DoDllStop` resets terminal-mode state while
   the console itself keeps the old bits).
3. opencode's TUI negotiated mouse tracking (`?1000h/1002h/1003h/1006h`) exactly once and never
   re-asserts, so after the reset the wheel/click stream stops being translated while keypresses
   (non-VT path) keep flowing.

Fixes shipped in the fork (two layers, general + specific):

- **Patched `ConEmuHk64.dll` / `ConEmuHk.dll`** (root-cause fix, closes the general class):
  rebuilt from [Maximus5/ConEmu](https://github.com/Maximus5/ConEmu) @ c8cebb9 with one behavioral
  change: `CEAnsi::DoneTermMode()` in `DoDllStop()` runs only when the dying process is the one
  that *itself* enabled the terminal mode (`gWasXTermModeSet[tmc_TerminalType].pid == GetCurrentProcessId()`).
  ConEmuHk is injected into every console child; `InitTermMode()` reads the *shared* output-buffer
  mode, so children inherit "XTerm on" and, on exit, flipped the whole console to Win32 emulation -
  destroying the parent TUI's negotiated `?1000h…` mouse routing (upstream:
  [Maximus5/ConEmu#2246](https://github.com/Maximus5/ConEmu/issues/2246)). Validated: wheel/selection
  now survive unrelated console children (`cmd /c ping -n 3` inside opencode) **and** repeated
  clipboard copies. Rebuild steps + `git apply` patch + stock backups live in
  `scripts/conemu-patch/`; `scripts/build.ps1` auto-applies them after vendor extraction via
  `scripts/apply_conemu_patch.ps1` (no-ops while ConEmu runs).
- **`bin/powershell.exe` shim** (opencode-specific interception, defense in depth): when the command
  line contains opencode's clipboard pattern (`Set-Clipboard` + `In.ReadToEnd` / `InputEncoding`), it
  runs the *real* system PowerShell with `CREATE_NO_WINDOW` (its own hidden console: working message
  pump so `Set-Clipboard` actually commits, isolated from the TUI console; opencode's pipes stay
  connected as stdio) and returns its exit code; every other invocation passes straight through with
  the same console. Without this, `powershell.exe` children attach to the TUI console and their exit
  still hits the (stock-) upstream reset path wherever the stock hook DLL is in use. The shim is
  picked up from the fork's bin path precedence (`which("powershell.exe")` resolves to it inside
  cmder sessions). Attempted-and-rejected alternatives (silent no-op `DETACHED_PROCESS`, hostile
  OSC/DECSET injection, resize jiggle) documented below.
- **`vendor/bin/cmder_tui_guard.py`** (optional defense-in-depth, started by `vendor/init.bat`,
  disable with `CMDER_NO_TUI_GUARD=1`): resident watcher that re-asserts the TUI's expected console
  input-buffer mode (`0x0208`) if any console child stomps it. Catches the shared-mode variant of
  the break, costs nothing while no TUI runs, spawned via `vendor/bin/cmder_tui_guard.cmd`.

Rebuild the shim without Visual Studio:
```
g++ -O1 -std=c++17 -municode -mconsole -static -DUNICODE -D_UNICODE \
    -o bin\powershell.exe bin\powershell_shim.c -lkernel32
```

What NOT to do (failed approaches, documented to save future cycles):
- Re-injecting the DECSET handshake from an attached *external* process does **not** revive the
  forwarding state.
- ConEmu's private `OSC 9;10;1` terminal-mode switch * externally * potentially re-arms
  forwarding but registers the injecting process as the mode "enabler" and reverts the whole
  console to plain Windows emulation when that process exits — transcript scrolling, translucent
  panels and highlighting get wrecked (verified). External OSC injection is forbidden in this fork.
- Resize/refresh tricks: no effect.

## Ideas parked (deliberately, in `plan` spirit)

- oh-my-posh / starship prompt integration (λ prompt kept per user decision).
- yazi TUI file manager.
- Vendor-refresh metadata for the `bin\` tool set (a `tools.json` consumed by an extended `build.ps1`).
