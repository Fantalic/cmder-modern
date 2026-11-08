// Minimal winres.h shim for toolchains that do not ship the MSVC-provided
// resource header (used by resource.rc). Visual Studio remains unaffected.
#ifndef _WINRES_H_
#define _WINRES_H_
#include <winver.h>
#include <windows.h>
#endif
