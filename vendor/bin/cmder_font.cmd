@echo off
rem ---------------------------------------------------------------------------
rem cmder_font.cmd - one time per-user install of the bundled fonts.
rem
rem Modern CLIs (eza, yazi) and Nerd-patched prompts draw icons with glyphs
rem living in unicode private areas.  A stock Windows install has no font for
rem them, and ConEmu then renders the old "empty box" glyphs people know from
rem ancient cmder screenshots.  The fork therefore bundles JetBrainsMono
rem Nerd Font in %CMDER_ROOT%\vendor\fonts and registers it under HKCU,
rem which needs no admin rights on Windows 10 1809 and later.
rem
rem Uses %CMDER_ROOT% and optionally %CMDER_USER_CONFIG% (shared install).
rem ---------------------------------------------------------------------------

if not defined CMDER_ROOT (
    echo cmder_font.cmd: CMDER_ROOT is not set, nothing to do.
    exit /b 1
)

set "FONT_SRC=%CMDER_ROOT%\vendor\fonts"
set "FONT_DST=%LOCALAPPDATA%\Microsoft\Windows\Fonts"
set "FONT_REG=HKCU\Software\Microsoft\Windows NT\CurrentVersion\Fonts"

if not exist "%FONT_SRC%\JetBrainsMonoNerdFont-Regular.ttf" (
    rem Bundled fonts are missing - probably a mini build; stay silent.
    exit /b 0
)

rem Stamp file records that registration already succeeded, so every later
rem session costs exactly one "if exist".
if defined CMDER_USER_CONFIG (
    set "FONT_STAMP=%CMDER_USER_CONFIG%\fonts_installed"
) else (
    set "FONT_STAMP=%CMDER_ROOT%\config\fonts_installed"
)
if exist "%FONT_STAMP%" exit /b 0

if not exist "%FONT_DST%" mkdir "%FONT_DST%" 2>nul

rem Windows needs the TTFs inside %LOCALAPPDATA%\Microsoft\Windows\Fonts,
rem registry values pointing back at them. One registry value per file, with
rem the style in the value name so all four weights stay registered. Two
rem families ship: CaskaydiaCove (default; terminal-first metrics render
rem block art pixel-perfect) and JetBrains Mono (opt-in; some mixed
rem half-block rows misalign by 1 px vs ConEmu's cell fitting).
set FONT_MISSING=0
for %%F in (Regular,Bold,Italic,BoldItalic) do (
    if not exist "%FONT_DST%\CaskaydiaCoveNerdFont-%%F.ttf" (
        copy /y "%FONT_SRC%\CaskaydiaCoveNerdFont-%%F.ttf" "%FONT_DST%\" >nul
    )
    if exist "%FONT_DST%\CaskaydiaCoveNerdFont-%%F.ttf" (
        reg add "%FONT_REG%" /v "CaskaydiaCove NF %%F (TrueType)" /t REG_SZ /d "%FONT_DST%\CaskaydiaCoveNerdFont-%%F.ttf" /f >nul 2>&1
    )
)
for %%F in (Regular,Bold,Italic,BoldItalic) do (
    if not exist "%FONT_DST%\JetBrainsMonoNerdFont-%%F.ttf" (
        copy /y "%FONT_SRC%\JetBrainsMonoNerdFont-%%F.ttf" "%FONT_DST%\" >nul
    )
    if exist "%FONT_DST%\JetBrainsMonoNerdFont-%%F.ttf" (
        reg add "%FONT_REG%" /v "JetBrainsMono NF %%F (TrueType)" /t REG_SZ /d "%FONT_DST%\JetBrainsMonoNerdFont-%%F.ttf" /f >nul 2>&1
    )
)

if "%FONT_MISSING%"=="1" (
    echo cmder_font.cmd: could not copy bundled fonts, skipping registration.
    exit /b 1
)

rem Tell running processes (ConEmu picks it up for new consoles).
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$a=Add-Type -MemberDefinition '[DllImport(\"Kernel32.dll\")] public static extern int AddFontResourceW([MarshalAs(UnmanagedType.LPWStr)] string L);[DllImport(\"user32.dll\")] public static extern int SendMessageTimeout(int h,int m,int w,int l,int f,int t,ref int r);' -Name NF -Namespace W32 -PassThru; $p=\"%FONT_DST%\"; foreach($n in 'CaskaydiaCoveNerdFont-Regular','CaskaydiaCoveNerdFont-Bold','CaskaydiaCoveNerdFont-Italic','CaskaydiaCoveNerdFont-BoldItalic','JetBrainsMonoNerdFont-Regular','JetBrainsMonoNerdFont-Bold','JetBrainsMonoNerdFont-Italic','JetBrainsMonoNerdFont-BoldItalic'){$a::AddFontResourceW(\"$p\$n.ttf\") > $null}; $r=0; $a::SendMessageTimeout(0xffff,0x001d,0,0,2,2000,[ref]$r)" >nul 2>&1

echo. > "%FONT_STAMP%"
exit /b 0
