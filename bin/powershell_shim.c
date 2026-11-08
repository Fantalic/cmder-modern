/**
 * powershell.exe shim (bin\powershell.exe shadows the system one within cmder).
 *
 * Purpose: opencode's clipboard path spawns `powershell.exe -NonInteractive
 * -NoProfile "-Command ...Set-Clipboard..."` as a console-subsystem child of
 * the TUI. That child inherits the TUI's console; when it exits, ConEmuHk's
 * child-termination handling resets the shared console state and the TUI's
 * mouse forwarding dies until restart. We intercept exactly that call
 * pattern, detach ourselves from the console, run the real PowerShell
 * headless (DETACHED_PROCESS, pipes from opencode stay inherited), and
 * return its exit code. Without a console attached, the real PowerShell
 * cannot be the "child that exits with terminal modes enabled", so no
 * forwarding reset occurs and the break never happens.
 *
 * Every other invocation passes through transparently (same exe, same args,
 * same console), so general `powershell` usage in the fork is unaffected.
 *
 * Detector strings match opencode's clipboard write command exactly:
 *   [Console]::InputEncoding = ...Set-Clipboard -Value ...
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#pragma comment(lib, "kernel32.lib")

static BOOL g_detect=FALSE;

static BOOL looks_like_clipboard_call(const wchar_t* cmd)
{
	/* target: "[Console]::InputEncoding ... Set-Clipboard -Value" */
	if (wcsstr(cmd, L"Set-Clipboard") != NULL && wcsstr(cmd, L"In.ReadToEnd") != NULL)
		return TRUE;
	if (wcsstr(cmd, L"Set-Clipboard") != NULL && wcsstr(cmd, L"InputEncoding") != NULL)
		return TRUE;
	return FALSE;
}

static wchar_t g_real_ps[MAX_PATH];

static void find_real_powershell(void)
{
	/* PS 5.1 lives at a fixed system location on every supported Windows build.
	 * Read the environment via the Win32 API (the CRT _wgetenv can return
	 * nothing under some MinGW CRT configurations). */
	wchar_t sysRoot[MAX_PATH] = { 0 };
	DWORD n = GetEnvironmentVariableW(L"SystemRoot", sysRoot, MAX_PATH);
	if (n == 0 || n >= MAX_PATH || !sysRoot[0])
		lstrcpyW(sysRoot, L"C:\\Windows");
	lstrcpyW(g_real_ps, sysRoot);
	lstrcatW(g_real_ps, L"\\System32\\WindowsPowerShell\\v1.0\\powershell.exe");
}

static int run_passthrough(int argc, wchar_t** argv)
{
	STARTUPINFOW si = { 0 };
	PROCESS_INFORMATION pi = { 0 };
	wchar_t cmdLine[MAX_PATH * 4 + 256];
	int i;

	/* When lpApplicationName is set, lpCommandLine's first token names the
	 * module; keep it explicit so argument parsing starts exactly at argv[1]. */
	wchar_t quotedReal[MAX_PATH + 4];
	swprintf(quotedReal, MAX_PATH + 4, L"\"%s\"", g_real_ps);
	wcscpy(cmdLine, quotedReal);
	for (i = 1; i < argc; i++)
	{
		BOOL hasSpace = wcschr(argv[i], L' ') != NULL;
		BOOL hasQuote = wcschr(argv[i], L'"') != NULL;
		if (hasSpace || hasQuote)
		{
			wcscat(cmdLine, L" \"");
			wcscat(cmdLine, argv[i]);
			wcscat(cmdLine, L"\"");
		}
		else
		{
			wcscat(cmdLine, L" ");
			wcscat(cmdLine, argv[i]);
		}
	}

	si.cb = sizeof(si);
	if (!CreateProcessW(g_real_ps, cmdLine, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
	{
		if (_wgetenv(L"POWERSHELL_SHIM_DEBUG"))
			fwprintf(stderr, L"shim: CreateProcess failed err=%lu cmd=%s\n", GetLastError(), cmdLine);
		return 9009;
	}
	WaitForSingleObject(pi.hProcess, INFINITE);
	DWORD exitCode = 1;
	GetExitCodeProcess(pi.hProcess, &exitCode);
	CloseHandle(pi.hProcess);
	CloseHandle(pi.hThread);
	return (int)exitCode;
}

static int run_detached(int argc, wchar_t** argv)
{
	STARTUPINFOW si = { 0 };
	PROCESS_INFORMATION pi = { 0 };
	wchar_t cmdLine[MAX_PATH * 4 + 512];
	int i;

	/* Drop any console ownership we inherited from the TUI console. */
	FreeConsole();

	wchar_t quotedReal[MAX_PATH + 4];
	swprintf(quotedReal, MAX_PATH + 4, L"\"%s\"", g_real_ps);
	wcscpy(cmdLine, quotedReal);
	for (i = 1; i < argc; i++)
	{
		BOOL hasSpace = wcschr(argv[i], L' ') != NULL;
		BOOL hasQuote = wcschr(argv[i], L'"') != NULL;
		if (hasSpace || hasQuote)
		{
			wcscat(cmdLine, L" \"");
			wcscat(cmdLine, argv[i]);
			wcscat(cmdLine, L"\"");
		}
		else
		{
			wcscat(cmdLine, L" ");
			wcscat(cmdLine, argv[i]);
		}
	}

	si.cb = sizeof(si);
	si.dwFlags = STARTF_USESTDHANDLES;
	si.hStdInput  = GetStdHandle(STD_INPUT_HANDLE);
	si.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
	si.hStdError  = GetStdHandle(STD_ERROR_HANDLE);

	/* DETACHED_PROCESS: real PS runs headless, keeps opencode's pipes as
	 * stdio, and never hosts the TUI console's terminal state. */
	if (!CreateProcessW(g_real_ps, cmdLine, NULL, NULL, TRUE,
	                    DETACHED_PROCESS | CREATE_UNICODE_ENVIRONMENT,
	                    NULL, NULL, &si, &pi))
	{
		if (_wgetenv(L"POWERSHELL_SHIM_DEBUG"))
			fwprintf(stderr, L"shim: CreateProcess(detached) failed err=%lu cmd=%s\n", GetLastError(), cmdLine);
		return 9009;
	}

	WaitForSingleObject(pi.hProcess, INFINITE);
	DWORD exitCode = 1;
	GetExitCodeProcess(pi.hProcess, &exitCode);
	CloseHandle(pi.hProcess);
	CloseHandle(pi.hThread);
	return (int)exitCode;
}

int wmain(int argc, wchar_t** argv)
{
	find_real_powershell();

	wchar_t* cmdLine = GetCommandLineW();
	if (looks_like_clipboard_call(cmdLine))
		return run_detached(argc, argv);
	return run_passthrough(argc, argv);
}
