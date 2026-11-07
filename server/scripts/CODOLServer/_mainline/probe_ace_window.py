"""测 ACE 拦截的精确时间点。

已知（项目记忆 + 本轮实测）:
    t+23.8s 转储成功
    t+32.2s 转储失败
    之后永久 err=5

但那是"转储"的整体耗时。真实问题可能是:
    A. 句柄在某个时刻被 ACE 吊销
    B. 一直能读，只是某段内存不可读了

本脚本: 抢到早期句柄后，每 0.5 秒读一次固定的 4 字节，
    持续 200 秒，记录**第一次** err=5 的时刻，以及之后是否恢复。

用法（提权 agent 内）:
    python -X utf8 -u probe_ace_window.py <outdir> <secs>
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PE32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL

TARGET = "codoMP_client_shipRetail.exe"
PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400


def find_pid():
    sh = k32.CreateToolhelp32Snapshot(2, 0)
    e = PE32W()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(sh, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            k32.CloseHandle(sh)
            return int(e.th32ProcessID)
        ok = k32.Process32NextW(sh, ctypes.byref(e))
    k32.CloseHandle(sh)
    return None


def rpm(h, va, n=4):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got))
    return ok, buf.raw[:got.value], ctypes.get_last_error()


def main():
    outdir = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0
    out = os.path.join(outdir, 'ace_window.jsonl')

    # 抢早期句柄
    t0 = time.time()
    pid = h = None
    while time.time() - t0 < 120:
        pid = find_pid()
        if pid:
            h = k32.OpenProcess(PROC_ALL, False, pid)
            if h:
                print('句柄 pid=%d handle=0x%X (t+%.2fs)' % (pid, h, time.time() - t0))
                break
        time.sleep(0.05)
    if not h:
        print('未抢到句柄')
        return 2

    # 读三个位置做对比：PE 头、vtable、随机的堆区
    TARGETS = {
        'PE_head 0x400000': 0x00400000,
        'vtable  0xDE07A4': 0x00DE07A4,
        'code    0x634870': 0x00634870,
    }

    first_fail = {}
    recovered = {}
    with open(out, 'w', encoding='utf-8') as f:
        while time.time() - t0 < secs:
            t = round(time.time() - t0, 2)
            rec = {'t': t, 'r': {}}
            for name, va in TARGETS.items():
                ok, data, err = rpm(h, va)
                rec['r'][name] = {'ok': bool(ok), 'err': err, 'v': data.hex()}
                if not ok:
                    if name not in first_fail:
                        first_fail[name] = t
                        print('  [t=%.2fs] ★ %s 首次失败 err=%d' % (t, name, err))
                else:
                    if name in first_fail and name not in recovered:
                        recovered[name] = t
                        print('  [t=%.2fs] ★ %s 恢复可读' % (t, name))
            f.write(json.dumps(rec) + '\n')
            f.flush()
            time.sleep(0.5)

    print()
    print('=== 结果 ===')
    for name in TARGETS:
        ff = first_fail.get(name)
        rc = recovered.get(name)
        if ff is None:
            print('  %-20s 全程可读' % name)
        else:
            print('  %-20s 从 t+%.1fs 起失败%s'
                  % (name, ff, ('，t+%.1fs 恢复' % rc) if rc else '，从未恢复'))
    k32.CloseHandle(h)
    print('done -> %s' % out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
