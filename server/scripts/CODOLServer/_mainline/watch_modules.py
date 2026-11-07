"""只读: 轮询客户端进程的模块清单, 用于对比本体/沙箱加载差异。"""
import ctypes, ctypes.wintypes as wt, sys, time, os

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
                ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260)]


def modules(pid):
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if h == -1:
        return []
    out = []
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    ok = k32.Module32First(h, ctypes.byref(me))
    while ok:
        out.append((me.szModule.decode(errors="replace"),
                    ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value or 0,
                    me.szExePath.decode(errors="replace")))
        ok = k32.Module32Next(h, ctypes.byref(me))
    k32.CloseHandle(h)
    return out


def main():
    target = sys.argv[1].casefold()
    out_path = sys.argv[2]
    best = {}
    t0 = time.time()
    seen_pid = None
    while time.time() - t0 < 90:
        pid = None
        h = k32.CreateToolhelp32Snapshot(0x00000002, 0)
        if h != -1:
            class PE(ctypes.Structure):
                _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                            ("th32ProcessID", wt.DWORD),
                            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                            ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                            ("th32ParentProcessID", wt.DWORD),
                            ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                            ("szExeFile", ctypes.c_char * 260)]
            pe = PE()
            pe.dwSize = ctypes.sizeof(PE)
            ok = k32.Process32First(h, ctypes.byref(pe))
            while ok:
                if pe.szExeFile.decode(errors="replace").casefold() == target:
                    pid = pe.th32ProcessID
                    break
                ok = k32.Process32Next(h, ctypes.byref(pe))
            k32.CloseHandle(h)
        if pid:
            seen_pid = pid
            ml = modules(pid)
            for name, base, path in ml:
                if name not in best:
                    best[name] = (base, path, time.time() - t0)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("pid=%d elapsed=%.1f count=%d\n" % (pid, time.time() - t0, len(ml)))
                for name, base, path in sorted(ml):
                    f.write("  %-40s 0x%08X %s\n" % (name, base, path))
                f.write("\n--- 曾出现过的全部 (累积) ---\n")
                for name in sorted(best):
                    b, p, t = best[name]
                    f.write("  %-40s 0x%08X t=%.1fs %s\n" % (name, b, t, p))
        time.sleep(0.1)
        if pid is None and seen_pid:
            break


main()
