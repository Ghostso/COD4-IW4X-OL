/*
===========================================================================
    sh1x server - Call of Duty Online Closed Alpha Server

    Last-resort crash reporting for the Win32 dedicated server.

    IW4OL only ever wrote a diagnostic when the engine itself decided to die
    (Com_Error -> Sys_Error -> sys_error.txt).  A genuine fault - an access
    violation, a stack overflow, an int3 from a debug assert, a CRT abort()
    or a bare exit() - unwound straight into the default Win32 handler, which
    on a dedicated server with no interactive desktop silently terminates the
    process.  The console log simply stopped mid-line and nothing on disk said
    why, which cost hours per incident.

    This file installs the missing top level handlers:

      * SetUnhandledExceptionFilter  - real faults (AV, int3, illegal insn,
                                       FP errors, stack overflow).
      * signal()                     - the CRT's own abort()/raise() paths,
                                       which never reach the SEH filter.
      * atexit()                     - distinguishes "someone called exit()"
                                       from "the process faulted".

    The report is written with raw Win32 file calls (no engine allocator, no
    FS layer, no critical sections) so it survives a corrupted heap, and names
    the faulting address as <module>+0xRVA so it can be translated against the
    build's map file without a debugger attached.

    It also exposes Sys_CaptureBacktrace()/Sys_SymbolizeAddress() so ordinary
    engine code can record who called it; Com_Quit_f and Cmd_ExecuteString use
    them to log the provenance of a server shutdown or map change.
===========================================================================
*/

#include "../q_shared.h"
#include "../qcommon_io.h"
#include "../sys_main.h"
#include "../qcommon_logprint.h"
#include "sys_win32.h"

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <string.h>

#define CODOL_CRASH_FILE "codol_crash.txt"
#define CODOL_CRASH_MAXFRAMES 64
/* Raised on the main thread by the map-load watchdog (sys_main.c). */
#define CODOL_LOAD_WATCHDOG_EXCEPTION 0xE0574447u

static volatile LONG crashReportEntered;
static LPTOP_LEVEL_EXCEPTION_FILTER previousFilter;
static qboolean quitExpected;

/*
==============
CrashSafe_IsReadable / CrashSafe_IsCode

VirtualQuery based probes.  Never dereference a candidate pointer from a
corrupted stack without one of these first.
==============
*/
static qboolean CrashSafe_IsReadable(const void *addr, SIZE_T len)
{
    MEMORY_BASIC_INFORMATION mbi;
    SIZE_T got;

    if (addr == NULL)
        return qfalse;

    got = VirtualQuery(addr, &mbi, sizeof(mbi));
    if (got != sizeof(mbi))
        return qfalse;
    if (mbi.State != MEM_COMMIT)
        return qfalse;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
        return qfalse;
    if (!(mbi.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
                         PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE |
                         PAGE_EXECUTE_WRITECOPY)))
        return qfalse;

    /* Make sure the whole span sits inside this region. */
    if ((const byte *)addr + len >
        (const byte *)mbi.BaseAddress + mbi.RegionSize)
        return qfalse;

    return qtrue;
}

static qboolean CrashSafe_IsCode(const void *addr)
{
    MEMORY_BASIC_INFORMATION mbi;

    if (addr == NULL)
        return qfalse;

    if (VirtualQuery(addr, &mbi, sizeof(mbi)) != sizeof(mbi))
        return qfalse;
    if (mbi.State != MEM_COMMIT)
        return qfalse;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
        return qfalse;
    if (!(mbi.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ |
                         PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)))
        return qfalse;
    /* Only module code, not JIT/anonymous pages. */
    if (mbi.Type != MEM_IMAGE)
        return qfalse;

    return qtrue;
}

/*
==============
Sys_SymbolizeAddress

"<module>+0x<rva> (0x<absolute>)".  The RVA is what a .map file is keyed on,
so this is enough to name the function without shipping symbols.
==============
*/
const char *Sys_SymbolizeAddress(const void *addr, char *out, int outlen)
{
    MEMORY_BASIC_INFORMATION mbi;
    char modulepath[MAX_OSPATH];
    const char *modulename;
    char *sep;

    if (out == NULL || outlen < 2)
        return "";

    out[0] = '\0';

    if (addr == NULL)
    {
        Com_sprintf(out, outlen, "(null)");
        return out;
    }

    if (VirtualQuery(addr, &mbi, sizeof(mbi)) != sizeof(mbi) ||
        mbi.AllocationBase == NULL)
    {
        Com_sprintf(out, outlen, "0x%08x (unmapped)", (unsigned int)(size_t)addr);
        return out;
    }

    modulepath[0] = '\0';
    if (GetModuleFileNameA((HMODULE)mbi.AllocationBase, modulepath,
                           sizeof(modulepath) - 1) == 0)
    {
        Com_sprintf(out, outlen, "0x%08x (base 0x%08x)",
                    (unsigned int)(size_t)addr,
                    (unsigned int)(size_t)mbi.AllocationBase);
        return out;
    }
    modulepath[sizeof(modulepath) - 1] = '\0';

    modulename = modulepath;
    sep = strrchr(modulepath, '\\');
    if (sep != NULL)
        modulename = sep + 1;
    sep = strrchr((char *)modulename, '/');
    if (sep != NULL)
        modulename = sep + 1;

    Com_sprintf(out, outlen, "%s+0x%x (0x%08x)", modulename,
                (unsigned int)((const byte *)addr - (const byte *)mbi.AllocationBase),
                (unsigned int)(size_t)addr);
    return out;
}

/*
==============
Sys_CaptureBacktrace

Return addresses of the callers of the caller, newest first.  Uses
RtlCaptureStackBackTrace when the OS exposes it (accurate even without frame
pointers for the first frames) and otherwise walks the EBP chain.
==============
*/
typedef USHORT(WINAPI *captureStackBackTrace_t)(ULONG, ULONG, PVOID *, PULONG);

int Sys_CaptureBacktrace(void **frames, int maxframes)
{
    static captureStackBackTrace_t capture;
    static qboolean captureResolved;
    int count = 0;
    void **ebp;

    if (frames == NULL || maxframes <= 0)
        return 0;

    if (!captureResolved)
    {
        HMODULE ntdll = GetModuleHandleA("ntdll.dll");
        captureResolved = qtrue;
        if (ntdll != NULL)
        {
            capture = (captureStackBackTrace_t)(void *)GetProcAddress(
                ntdll, "RtlCaptureStackBackTrace");
        }
    }

    if (capture != NULL)
    {
        count = (int)capture(1, (ULONG)maxframes, frames, NULL);
        if (count > 0)
            return count;
    }

    /* Fallback: EBP chain of this frame. */
    ebp = (void **)__builtin_frame_address(0);
    while (count < maxframes && CrashSafe_IsReadable(ebp, sizeof(void *) * 2))
    {
        void *ret = ebp[1];
        if (!CrashSafe_IsCode(ret))
            break;
        frames[count++] = ret;
        if ((void **)ebp[0] <= ebp)
            break;
        ebp = (void **)ebp[0];
    }
    return count;
}

/*
==============
CrashReport_Write

Appends one report to CODOL_CRASH_FILE next to the executable's working
directory (the same place Sys_Error drops sys_error.txt) and echoes it to the
console.  Raw WriteFile: no engine allocator, no logfile critical section.
==============
*/
static void CrashReport_Open(HANDLE *fh)
{
    *fh = CreateFileA(CODOL_CRASH_FILE, FILE_APPEND_DATA, FILE_SHARE_READ,
                      NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
}

static void CrashReport_Line(HANDLE fh, const char *fmt, ...)
{
    char line[1024];
    va_list argptr;
    DWORD written;
    int len;

    va_start(argptr, fmt);
    Q_vsnprintf(line, sizeof(line) - 2, fmt, argptr);
    va_end(argptr);

    line[sizeof(line) - 3] = '\0';
    len = (int)strlen(line);
    line[len++] = '\r';
    line[len++] = '\n';
    line[len] = '\0';

    if (fh != INVALID_HANDLE_VALUE)
        WriteFile(fh, line, (DWORD)len, &written, NULL);

    /* Best effort echo.  Sys_Print only touches the console window buffer
     * and stdout, both safe enough after a fault. */
    Sys_Print(line);
}

static const char *CrashReport_ExceptionName(DWORD code)
{
    switch (code)
    {
        case EXCEPTION_ACCESS_VIOLATION: return "EXCEPTION_ACCESS_VIOLATION";
        case EXCEPTION_ARRAY_BOUNDS_EXCEEDED: return "EXCEPTION_ARRAY_BOUNDS_EXCEEDED";
        case EXCEPTION_BREAKPOINT: return "EXCEPTION_BREAKPOINT (int3)";
        case EXCEPTION_DATATYPE_MISALIGNMENT: return "EXCEPTION_DATATYPE_MISALIGNMENT";
        case EXCEPTION_FLT_DENORMAL_OPERAND: return "EXCEPTION_FLT_DENORMAL_OPERAND";
        case EXCEPTION_FLT_DIVIDE_BY_ZERO: return "EXCEPTION_FLT_DIVIDE_BY_ZERO";
        case EXCEPTION_FLT_INEXACT_RESULT: return "EXCEPTION_FLT_INEXACT_RESULT";
        case EXCEPTION_FLT_INVALID_OPERATION: return "EXCEPTION_FLT_INVALID_OPERATION";
        case EXCEPTION_FLT_OVERFLOW: return "EXCEPTION_FLT_OVERFLOW";
        case EXCEPTION_FLT_STACK_CHECK: return "EXCEPTION_FLT_STACK_CHECK";
        case EXCEPTION_FLT_UNDERFLOW: return "EXCEPTION_FLT_UNDERFLOW";
        case EXCEPTION_ILLEGAL_INSTRUCTION: return "EXCEPTION_ILLEGAL_INSTRUCTION";
        case EXCEPTION_IN_PAGE_ERROR: return "EXCEPTION_IN_PAGE_ERROR";
        case EXCEPTION_INT_DIVIDE_BY_ZERO: return "EXCEPTION_INT_DIVIDE_BY_ZERO";
        case EXCEPTION_INT_OVERFLOW: return "EXCEPTION_INT_OVERFLOW";
        case EXCEPTION_INVALID_DISPOSITION: return "EXCEPTION_INVALID_DISPOSITION";
        case EXCEPTION_NONCONTINUABLE_EXCEPTION: return "EXCEPTION_NONCONTINUABLE_EXCEPTION";
        case EXCEPTION_PRIV_INSTRUCTION: return "EXCEPTION_PRIV_INSTRUCTION";
        case EXCEPTION_SINGLE_STEP: return "EXCEPTION_SINGLE_STEP";
        case EXCEPTION_STACK_OVERFLOW: return "EXCEPTION_STACK_OVERFLOW";
        case 0xE06D7363: return "C++ exception";
        case CODOL_LOAD_WATCHDOG_EXCEPTION: return "sh1x load watchdog: the main thread was stuck in a map load";
        default: break;
    }
    return "unknown exception";
}

static void CrashReport_Header(HANDLE fh, const char *what)
{
    SYSTEMTIME st;
    char exepath[MAX_OSPATH];

    GetLocalTime(&st);
    exepath[0] = '\0';
    GetModuleFileNameA(NULL, exepath, sizeof(exepath) - 1);
    exepath[sizeof(exepath) - 1] = '\0';

    CrashReport_Line(fh, "");
    CrashReport_Line(fh, "============================================================");
    CrashReport_Line(fh, "sh1x server fatal: %s", what);
    CrashReport_Line(fh, "time    %04d-%02d-%02d %02d:%02d:%02d",
                     st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
    CrashReport_Line(fh, "module  %s (base 0x%08x)", exepath,
                     (unsigned int)(size_t)GetModuleHandleA(NULL));
    CrashReport_Line(fh, "pid     %u  thread %u",
                     (unsigned int)GetCurrentProcessId(),
                     (unsigned int)GetCurrentThreadId());
}

static void CrashReport_StackScan(HANDLE fh, const byte *esp)
{
    MEMORY_BASIC_INFORMATION mbi;
    const byte *limit;
    const void **p;
    char sym[MAX_OSPATH + 64];
    int printed = 0;

    if (esp == NULL || VirtualQuery(esp, &mbi, sizeof(mbi)) != sizeof(mbi))
        return;

    limit = (const byte *)mbi.BaseAddress + mbi.RegionSize;
    if (limit > esp + 0x8000)
        limit = esp + 0x8000; /* 32 KiB of stack is plenty. */

    CrashReport_Line(fh, "stack scan (return addresses found on the stack):");
    for (p = (const void **)esp; (const byte *)p + sizeof(void *) <= limit; p++)
    {
        if (!CrashSafe_IsReadable(p, sizeof(void *)))
            break;
        if (!CrashSafe_IsCode(*p))
            continue;
        CrashReport_Line(fh, "  [esp+0x%04x] %s",
                         (unsigned int)((const byte *)p - esp),
                         Sys_SymbolizeAddress(*p, sym, sizeof(sym)));
        if (++printed >= CODOL_CRASH_MAXFRAMES)
            break;
    }
    if (printed == 0)
        CrashReport_Line(fh, "  (none)");
}

static LONG WINAPI CODOL_UnhandledExceptionFilter(EXCEPTION_POINTERS *info)
{
    HANDLE fh;
    char sym[MAX_OSPATH + 64];
    const EXCEPTION_RECORD *rec;
    const CONTEXT *ctx;

    /* One report only; a fault inside the reporter must not loop. */
    if (InterlockedExchange(&crashReportEntered, 1) != 0)
        return EXCEPTION_EXECUTE_HANDLER;

    rec = (info != NULL) ? info->ExceptionRecord : NULL;
    ctx = (info != NULL) ? info->ContextRecord : NULL;

    CrashReport_Open(&fh);
    CrashReport_Header(fh, rec ? CrashReport_ExceptionName(rec->ExceptionCode)
                               : "unhandled exception (no record)");
    if (rec != NULL && rec->ExceptionCode == CODOL_LOAD_WATCHDOG_EXCEPTION &&
        Sys_LoadWatchdogFiredMessage() != NULL)
    {
        /* The frames below the watchdog trap are where the load was spinning. */
        CrashReport_Line(fh, "%s", Sys_LoadWatchdogFiredMessage());
    }

    if (rec != NULL)
    {
        CrashReport_Line(fh, "code    0x%08x  flags 0x%08x",
                         (unsigned int)rec->ExceptionCode,
                         (unsigned int)rec->ExceptionFlags);
        CrashReport_Line(fh, "at      %s",
                         Sys_SymbolizeAddress(rec->ExceptionAddress, sym, sizeof(sym)));
        if (rec->ExceptionCode == EXCEPTION_ACCESS_VIOLATION &&
            rec->NumberParameters >= 2)
        {
            static const char *ops[] = {"read", "write", "execute"};
            unsigned int op = (unsigned int)rec->ExceptionInformation[0];
            CrashReport_Line(fh, "access  %s of 0x%08x",
                             op < 3 ? ops[op] : "?",
                             (unsigned int)rec->ExceptionInformation[1]);
        }
    }

#if defined(_M_IX86) || defined(__i386__)
    if (ctx != NULL)
    {
        CrashReport_Line(fh, "eip %08x esp %08x ebp %08x eflags %08x",
                         (unsigned int)ctx->Eip, (unsigned int)ctx->Esp,
                         (unsigned int)ctx->Ebp, (unsigned int)ctx->EFlags);
        CrashReport_Line(fh, "eax %08x ebx %08x ecx %08x edx %08x",
                         (unsigned int)ctx->Eax, (unsigned int)ctx->Ebx,
                         (unsigned int)ctx->Ecx, (unsigned int)ctx->Edx);
        CrashReport_Line(fh, "esi %08x edi %08x",
                         (unsigned int)ctx->Esi, (unsigned int)ctx->Edi);
        CrashReport_Line(fh, "eip     %s",
                         Sys_SymbolizeAddress((const void *)(size_t)ctx->Eip,
                                              sym, sizeof(sym)));

        /* EBP chain first: exact when the frame pointer survived. */
        {
            void **ebp = (void **)(size_t)ctx->Ebp;
            int depth = 0;
            CrashReport_Line(fh, "frame chain:");
            while (depth < CODOL_CRASH_MAXFRAMES &&
                   CrashSafe_IsReadable(ebp, sizeof(void *) * 2))
            {
                void *ret = ebp[1];
                if (!CrashSafe_IsCode(ret))
                    break;
                CrashReport_Line(fh, "  #%02d %s", depth,
                                 Sys_SymbolizeAddress(ret, sym, sizeof(sym)));
                depth++;
                if ((void **)ebp[0] <= ebp)
                    break;
                ebp = (void **)ebp[0];
            }
            if (depth == 0)
                CrashReport_Line(fh, "  (no frame pointer chain)");
        }

        CrashReport_StackScan(fh, (const byte *)(size_t)ctx->Esp);
    }
#endif

    CrashReport_Line(fh, "============================================================");

    if (fh != INVALID_HANDLE_VALUE)
    {
        FlushFileBuffers(fh);
        CloseHandle(fh);
    }

    /* Flush whatever the engine still holds so qconsole.log ends with this. */
    Com_CloseLogFiles();

    if (previousFilter != NULL)
        return previousFilter(info);

    return EXCEPTION_EXECUTE_HANDLER;
}

/* Map-load watchdog (sys_main.c). The watchdog thread cannot unwind another
 * thread, so it makes the stuck main thread fault by itself: suspend it,
 * push its current EIP as if it had called CODOL_LoadWatchdogTrap from where
 * it was spinning, and resume it there. The unhandled-exception report above
 * then records that thread's registers, frame chain and stack scan. */
static void CODOL_LoadWatchdogTrap(void)
{
    RaiseException(CODOL_LOAD_WATCHDOG_EXCEPTION, EXCEPTION_NONCONTINUABLE, 0, NULL);
}

qboolean Sys_LoadWatchdogInterruptMain(void)
{
#if defined(_M_IX86) || defined(__i386__)
    extern threadid_t mainthread;
    HANDLE th;
    CONTEXT ctx;
    BOOL ok = FALSE;

    th = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_SET_CONTEXT,
                    FALSE, mainthread);
    if (th == NULL)
        return qfalse;
    if (SuspendThread(th) == (DWORD)-1)
    {
        CloseHandle(th);
        return qfalse;
    }
    memset(&ctx, 0, sizeof(ctx));
    ctx.ContextFlags = CONTEXT_CONTROL;
    if (GetThreadContext(th, &ctx) && CrashSafe_IsReadable((const void *)(size_t)(ctx.Esp - 4), 4))
    {
        *(DWORD *)(size_t)(ctx.Esp - 4) = ctx.Eip;
        ctx.Esp -= 4;
        ctx.Eip = (DWORD)(size_t)CODOL_LoadWatchdogTrap;
        ok = SetThreadContext(th, &ctx);
    }
    ResumeThread(th);
    CloseHandle(th);
    return ok ? qtrue : qfalse;
#else
    return qfalse;
#endif
}

static void CODOL_CrashSignalHandler(int sig)
{
    HANDLE fh;
    void *frames[CODOL_CRASH_MAXFRAMES];
    char sym[MAX_OSPATH + 64];
    int count, i;
    const char *name;

    if (InterlockedExchange(&crashReportEntered, 1) != 0)
        _exit(3);

    switch (sig)
    {
        case SIGABRT: name = "SIGABRT (abort/assert)"; break;
        case SIGSEGV: name = "SIGSEGV"; break;
        case SIGILL:  name = "SIGILL"; break;
        case SIGFPE:  name = "SIGFPE"; break;
        case SIGINT:  name = "SIGINT"; break;
        case SIGTERM: name = "SIGTERM"; break;
        default:      name = "signal"; break;
    }

    CrashReport_Open(&fh);
    CrashReport_Header(fh, name);

    count = Sys_CaptureBacktrace(frames, CODOL_CRASH_MAXFRAMES);
    CrashReport_Line(fh, "frame chain:");
    for (i = 0; i < count; i++)
        CrashReport_Line(fh, "  #%02d %s", i,
                         Sys_SymbolizeAddress(frames[i], sym, sizeof(sym)));
    if (count == 0)
        CrashReport_Line(fh, "  (unavailable)");

    CrashReport_Line(fh, "============================================================");

    if (fh != INVALID_HANDLE_VALUE)
    {
        FlushFileBuffers(fh);
        CloseHandle(fh);
    }

    Com_CloseLogFiles();
    _exit(3);
}

/*
==============
CODOL_CrashAtExit

Reached for a plain exit()/return from main.  Sys_Quit marks the quit as
expected first, so anything that lands here without that marker is an
unannounced exit() somewhere in the tree and worth a line on disk.
==============
*/
static void CODOL_CrashAtExit(void)
{
    HANDLE fh;
    void *frames[CODOL_CRASH_MAXFRAMES];
    char sym[MAX_OSPATH + 64];
    int count, i;

    if (quitExpected)
        return;
    if (InterlockedExchange(&crashReportEntered, 1) != 0)
        return;

    CrashReport_Open(&fh);
    CrashReport_Header(fh, "unexpected exit() - process left without Com_Quit_f/Sys_Error");

    count = Sys_CaptureBacktrace(frames, CODOL_CRASH_MAXFRAMES);
    CrashReport_Line(fh, "frame chain:");
    for (i = 0; i < count; i++)
        CrashReport_Line(fh, "  #%02d %s", i,
                         Sys_SymbolizeAddress(frames[i], sym, sizeof(sym)));
    if (count == 0)
        CrashReport_Line(fh, "  (unavailable)");

    CrashReport_Line(fh, "============================================================");

    if (fh != INVALID_HANDLE_VALUE)
    {
        FlushFileBuffers(fh);
        CloseHandle(fh);
    }
}

void Sys_MarkQuitExpected(void)
{
    quitExpected = qtrue;
}

/*
==============
Sys_InstallCrashHandler

Called as early as possible from WinMain, before any engine subsystem runs.
==============
*/
void Sys_InstallCrashHandler(void)
{
    static qboolean installed;

    if (installed)
        return;
    installed = qtrue;

    /* No "the application stopped working" modal on a headless box: it would
     * hang the process instead of letting our filter write the report. */
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX |
                 SEM_NOOPENFILEERRORBOX);

    previousFilter = SetUnhandledExceptionFilter(CODOL_UnhandledExceptionFilter);

    signal(SIGABRT, CODOL_CrashSignalHandler);
    signal(SIGSEGV, CODOL_CrashSignalHandler);
    signal(SIGILL, CODOL_CrashSignalHandler);
    signal(SIGFPE, CODOL_CrashSignalHandler);

    atexit(CODOL_CrashAtExit);
}
