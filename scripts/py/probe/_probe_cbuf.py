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

game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
exe_path = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"

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
            # write EB
            old = wt.DWORD(0)
            k32.VirtualProtectEx(hProc, ctypes.c_void_p(0x0077F6EF), 2, 0x40, ctypes.byref(old))
            k32.WriteProcessMemory(hProc, ctypes.c_void_p(0x0077F6EF), b"\xEB\x36", 2, ctypes.byref(n))
            k32.VirtualProtectEx(hProc, ctypes.c_void_p(0x0077F6EF), 2, old.value, ctypes.byref(old))
            print(f"[+] Unpack gate unlocked at t={time.time() - t0:.2f}s!")
            break
    time.sleep(0.02)

time.sleep(0.8)

# Now read memory at 0x00406C20 and 0x0040833B
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

for va, name in [(0x00406C20, "Cbuf_AddText"), (0x0040833B, "Cmd_ExecuteSingleCommand")]:
    buf = ctypes.create_string_buffer(32)
    k32.ReadProcessMemory(hProc, ctypes.c_void_p(va), buf, 32, ctypes.byref(n))
    print(f"\n--- Disassembly of {name} @ 0x{va:08X} ---")
    for ins in md.disasm(buf.raw[:n.value], va):
        print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))

k32.TerminateProcess(hProc, 0)
k32.CloseHandle(hProc)