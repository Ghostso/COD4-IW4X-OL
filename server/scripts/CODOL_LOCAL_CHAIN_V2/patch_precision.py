# -*- coding: utf-8 -*-
"""运行时 patch：把 0x00C4A5D0 处的精度常量 8 改成 20。

背景：
  崩溃 0xC0000005 @ 0x00C4A7A1
    cmp byte ptr [eax], 0    (eax=8)
  原因：CRT 数字格式化在 8 位精度耗尽后仍继续除法，
        写指针 esi 越过 17 字节缓冲区，破坏 [ebp-0x220]，
        随后 strlen(NULL=8) 崩溃。

  修复点 0x00C4A5D0:
    C7 85 E8 FD FF FF 08 00 00 00    mov dword ptr [ebp-0x218], 8
    -> 改 imm32 为 20 (0x14)

注意：该地址在 .tp3 加密段，磁盘态不可改，必须运行时 patch。
      必须在客户端解壳后、到达该代码前执行。

用法：
  python patch_precision.py --pid <pid>
  python patch_precision.py --pid <pid> --restore    # 还原为 8
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import struct
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
PAGE_EXECUTE_READWRITE = 0x40

k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                 wt.DWORD, ctypes.POINTER(wt.DWORD)]

SITE = 0x00C4A5D0
# 期望的原始字节（含 8 与 20 两种状态）
PATTERN_LO = bytes.fromhex("C785E8FDFFFF")   # mov [ebp-0x218], imm32
ORIG_IMM = 8
PATCH_IMM = 20


def find_pid(name="codoMP_client_shipRetail.exe"):
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + name, "/FO", "CSV", "/NH"],
                         capture_output=True, text=True, errors="replace").stdout
    pids = []
    for line in out.splitlines():
        parts = [x.strip('"') for x in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def rd(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def wr(h, addr, data):
    old = wt.DWORD()
    if not k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data),
                                PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        return False, "VirtualProtectEx failed err=%d" % ctypes.get_last_error()
    got = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data),
                                ctypes.byref(got))
    err = ctypes.get_last_error()
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value,
                         ctypes.byref(wt.DWORD()))
    k32.FlushInstructionCache(h, ctypes.c_void_p(addr), len(data))
    if not ok:
        return False, "WriteProcessMemory failed err=%d" % err
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--restore", action="store_true", help="还原为 8")
    ap.add_argument("--wait", type=float, default=0.0, help="等待进程出现的秒数")
    a = ap.parse_args()

    pid = a.pid
    if not pid and a.wait > 0:
        t0 = time.time()
        while time.time() - t0 < a.wait:
            ps = find_pid()
            if ps:
                pid = max(ps)
                break
            time.sleep(0.3)
    if not pid:
        ps = find_pid()
        if not ps:
            print("!! 找不到客户端进程")
            return 2
        pid = max(ps)

    h = k32.OpenProcess(PROCESS_ALL, False, pid)
    if not h:
        print("!! OpenProcess 失败 err=%d（需要管理员）" % ctypes.get_last_error())
        return 2

    cur = rd(h, SITE, 10)
    if cur is None:
        print("!! 读 0x%08X 失败（可能尚未解壳）" % SITE)
        k32.CloseHandle(h)
        return 3

    want = ORIG_IMM if a.restore else PATCH_IMM
    print("pid=%d" % pid)
    print("当前 0x%08X: %s" % (SITE, " ".join("%02X" % x for x in cur)))

    if cur[:6] != PATTERN_LO:
        print("!! 前缀不匹配（期望 C7 85 E8 FD FF FF），当前不是预期指令")
        k32.CloseHandle(h)
        return 4

    old_imm = struct.unpack("<I", cur[6:10])[0]
    print("当前 imm32 = %d" % old_imm)

    if old_imm == want:
        print("已经是 %d，无需修改" % want)
        k32.CloseHandle(h)
        return 0

    newbytes = PATTERN_LO + struct.pack("<I", want)
    ok, msg = wr(h, SITE, newbytes)
    print("写入 %d: %s" % (want, msg))

    back = rd(h, SITE, 10)
    print("回读 0x%08X: %s" % (SITE, " ".join("%02X" % x for x in back) if back else "FAIL"))
    if back and struct.unpack("<I", back[6:10])[0] == want:
        print("✓ patch 生效（精度 = %d）" % want)
        rc = 0
    else:
        print("✗ patch 未生效")
        rc = 5

    k32.CloseHandle(h)
    return rc


if __name__ == "__main__":
    sys.exit(main())
