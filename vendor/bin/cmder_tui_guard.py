"""TUI console-mode guard for ConEmu-hosted cmd consoles.

Background helper (spawned per console via vendor\\bin, no child processes):
while a modern full-screen TUI runs in THIS console, it sets the console
input-buffer mode to a specific raw/VT combination. Console children the
TUI spawns (clipboard helpers, hooks) share that one buffer mode; when a
child exits, ConEmuHk + the child's own SetConsoleMode leave the shared
mode cooked. The TUI never re-asserts, so the mouse dies while keys
survive. This watcher polls the shared mode via its own handle and, while
a known TUI process is attached to this console and the mode differs from
the TUI's expected value, re-asserts it.

No console children, no output, no OSC: pure Get/SetConsoleMode on the
shared input buffer, so it cannot disturb rendering state.
"""
import ctypes, os, time

MODE_TARGET = 0x0208          # WINDOW_INPUT | ENABLE_VIRTUAL_TERMINAL_INPUT
TUI_NAMES = frozenset(("opencode.exe",))
POLL_SECONDS = 0.25

LOG_PATH = os.environ.get("CMDER_TUI_GUARD_LOG", "")

kk = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong),
                ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", ctypes.c_ulong),
                ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_wchar * 260)]


TH32CS_SNAPPROCESS = 0x00000002


def _pid_name_map():
    snap = kk.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1 or not snap:
        return {}
    try:
        result = {}
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if kk.Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                result[entry.th32ProcessID] = entry.szExeFile.lower()
                if not kk.Process32NextW(snap, ctypes.byref(entry)):
                    break
        return result
    finally:
        kk.CloseHandle(snap)


def console_pids():
    buf = (ctypes.c_ulong * 1024)()
    n = kk.GetConsoleProcessList(buf, 1024)
    if n <= 0:
        return []
    return [buf[i] for i in range(n)]


def tui_running_here():
    cmap = _pid_name_map()
    return any(cmap.get(pid, "") in TUI_NAMES for pid in console_pids())


def main():
    h_in = kk.GetStdHandle(-10)
    logf = None
    log_path = LOG_PATH
    if log_path:
        logf = open(log_path, "a", buffering=1)

    def w(s):
        if logf:
            logf.write(time.strftime("%H:%M:%S ") + s + "\n")
            logf.flush()

    w("guard started pid=%d target_mode=0x%04X tui=%r"
      % (kk.GetCurrentProcessId(), MODE_TARGET, TUI_NAMES))
    reasserts = 0
    while True:
        time.sleep(POLL_SECONDS)
        try:
            if not tui_running_here():
                continue
            m = ctypes.c_ulong()
            ok = kk.GetConsoleMode(h_in, ctypes.byref(m))
            if not ok:
                continue
            if m.value != MODE_TARGET:
                if kk.SetConsoleMode(h_in, MODE_TARGET):
                    reasserts += 1
                    w("re-asserted 0x%04X (was 0x%04X) total=%d"
                      % (MODE_TARGET, m.value, reasserts))
        except Exception as e:  # never let the guard die loudly
            w("guard error %s" % repr(e)[:120])


if __name__ == "__main__":
    main()
