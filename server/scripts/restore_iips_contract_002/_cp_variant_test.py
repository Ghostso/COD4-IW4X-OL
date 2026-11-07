"""Which CreateProcess parameter makes codoMP_client_shipRetail.exe exit instantly?"""
import ctypes, os, sys, time
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class STARTUPINFO(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

k32.CreateProcessW.restype = wintypes.BOOL
k32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p,
                               ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
                               ctypes.c_void_p, wintypes.LPCWSTR,
                               ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)]

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "COD OL")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
ENVBLOCK = ctypes.create_unicode_buffer(
    "".join("%s=%s\0" % (k, v) for k, v in os.environ.items()) + "\0")
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NEW_CONSOLE = 0x00000010
DETACHED_PROCESS = 0x00000008


def run(name, app, cmd, inherit, flags, env, cwd, watch=6.0):
    si = STARTUPINFO(); si.cb = ctypes.sizeof(STARTUPINFO)
    pi = PROCESS_INFORMATION()
    arg_env = ctypes.cast(env, ctypes.c_void_p) if env is not None else None
    ok = k32.CreateProcessW(app, ctypes.create_unicode_buffer(cmd), None, None,
                            inherit, flags, arg_env, cwd, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("%-28s CREATE_FAIL err=%d" % (name, ctypes.get_last_error())); return None
    time.sleep(watch)
    code = wintypes.DWORD()
    k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    alive = (code.value == 259)
    if alive:
        k32.TerminateProcess(pi.hProcess, 0)
    print("%-28s alive_after_%.1fs=%-5s exitcode=0x%08X" % (name, watch, alive, code.value))
    k32.CloseHandle(pi.hProcess); k32.CloseHandle(pi.hThread)
    time.sleep(1.5)
    return alive


cmdline = '"%s" -q' % EXE
run("V1 observer-style",   EXE, cmdline, False, 0, None, GAME)
run("V2 appname=null",     None, cmdline, False, 0, None, GAME)
run("V3 inherit=true",     EXE, cmdline, True, 0, None, GAME)
run("V4 unicode_env",      EXE, cmdline, False, CREATE_UNICODE_ENVIRONMENT, ENVBLOCK, GAME)
run("V5 new_console",      EXE, cmdline, False, CREATE_NEW_CONSOLE, ENVBLOCK, GAME)
run("V6 detached",         EXE, cmdline, False, DETACHED_PROCESS, ENVBLOCK, GAME)
run("V7 no cwd",           EXE, cmdline, False, 0, None, None)
