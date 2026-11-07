# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wt
import struct

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Launch suspended, read PE header at 0x00400000
class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD)] + [("pad", ctypes.c_byte)] * 64

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]

si = STARTUPINFOW()
si.cb = 68
pi = PROCESS_INFORMATION()

game_dir = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
exe_path = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"

k32.CreateProcessW(None, f'"{exe_path}" -qa', None, None, False, 4, None, game_dir, ctypes.byref(si), ctypes.byref(pi))
hProc = pi.hProcess

buf = ctypes.create_string_buffer(0x1000)
n = ctypes.c_size_t(0)
k32.ReadProcessMemory(hProc, ctypes.c_void_p(0x00400000), buf, 0x1000, ctypes.byref(n))

k32.TerminateProcess(hProc, 0)
k32.CloseHandle(pi.hThread)
k32.CloseHandle(hProc)

data = buf.raw
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
print(f"e_lfanew = 0x{e_lfanew:X}")

sig = struct.unpack_from("<I", data, e_lfanew)[0]
ts = struct.unpack_from("<I", data, e_lfanew + 4 + 4)[0]
soi = struct.unpack_from("<I", data, e_lfanew + 4 + 20 + 56)[0]

print(f"PE Signature: 0x{sig:08X} (expected 0x00004550)")
print(f"TimeDateStamp: 0x{ts:08X} (expected 0x6096930A)")
print(f"SizeOfImage: 0x{soi:08X} (expected 0x0E659000)")