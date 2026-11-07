# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wt
import time, capstone

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD)] + [("pad", ctypes.c_byte)] * 64

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]

si = STARTUPINFOW()
si.cb = 68
pi = PROCESS_INFORMATION()

game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
exe_path = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"

k32.CreateProcessW(None, f'"{exe_path}"', None, None, False, 4, None, game_dir, ctypes.byref(si), ctypes.byref(pi))
hProc = pi.hProcess
hThread = pi.hThread

k32.ResumeThread(hThread)
k32.CloseHandle(hThread)

# Wait for unpack gate 0x0077F6EF
t0 = time.time()
while time.time() - t0 < 8.0:
    buf = ctypes.create_string_buffer(2)
    n = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(hProc, ctypes.c_void_p(0x0077F6EF), buf, 2, ctypes.byref(n)):
        if buf.raw[0] == 0x75:
            old = wt.DWORD(0)
            k32.VirtualProtectEx(hProc, ctypes.c_void_p(0x0077F6EF), 2, 0x40, ctypes.byref(old))
            k32.WriteProcessMemory(hProc, ctypes.c_void_p(0x0077F6EF), b"\xEB\x36", 2, ctypes.byref(n))
            k32.VirtualProtectEx(hProc, ctypes.c_void_p(0x0077F6EF), 2, old.value, ctypes.byref(old))
            break
    time.sleep(0.02)

time.sleep(0.8)

# Find prologue before 0x4AA8E3
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
buf = ctypes.create_string_buffer(256)
k32.ReadProcessMemory(hProc, ctypes.c_void_p(0x004AA880), buf, 256, ctypes.byref(n))

print("=== Disassembly around 0x004AA880 ===")
for ins in md.disasm(buf.raw[:n.value], 0x004AA880):
    print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))

k32.TerminateProcess(hProc, 0)
k32.CloseHandle(hProc)