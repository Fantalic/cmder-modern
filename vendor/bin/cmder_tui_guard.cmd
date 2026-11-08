@echo off
rem ---- TUI console-mode guard -------------------------------------------
rem While a modern TUI (opencode) runs in this console, console children
rem (clipboard helpers etc.) can leave the shared console input mode cooked
rem after they exit; the TUI never re-asserts, so the mouse dies while keys
rem keep working. This resident helper re-asserts the TUI's console mode.
rem Costs nothing when no TUI runs; produces no console output.
if not exist "%CMDER_ROOT%\vendor\bin\cmder_tui_guard.py" exit /b
start /b "" cmd /c "python "%CMDER_ROOT%\vendor\bin\cmder_tui_guard.py" >nul 2>&1"
