import shutil

src = r"REF_LOBBY_KIT\nt10.py"
bak = r"REF_LOBBY_KIT\nt10.py.bak_before_native_inject"
shutil.copy2(src, bak)
print(f"Backed up {src} to {bak}")

with open(src, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add k32.CreateRemoteThread and WaitForSingleObject definitions
target_def = 'k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]'
extra_defs = """k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
k32.CreateRemoteThread.restype = wintypes.HANDLE
k32.CreateRemoteThread.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                   ctypes.POINTER(wintypes.DWORD)]
k32.WaitForSingleObject.restype = wintypes.DWORD
k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

def inject_dll_late(h, log, dll_path):
    if not os.path.isfile(dll_path):
        log("-- [NATIVE-INJECT] 找不到 DLL: %s" % dll_path)
        return False
    raw = dll_path.encode("latin1") + b"\\x00"
    p_str = k32.VirtualAllocEx(h, None, len(raw) + 16, MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    if not p_str:
        log("-- [NATIVE-INJECT] VirtualAllocEx 远程路径失败 err=%d" % ctypes.get_last_error())
        return False
    wpm(h, p_str, raw)
    k32_mod = ctypes.windll.kernel32.GetModuleHandleA(b"kernel32.dll")
    p_load = ctypes.windll.kernel32.GetProcAddress(k32_mod, b"LoadLibraryA")
    tid = wintypes.DWORD(0)
    th = k32.CreateRemoteThread(h, None, 0, p_load, ctypes.c_void_p(p_str), 0, ctypes.byref(tid))
    if th:
        k32.WaitForSingleObject(th, 3000)
        k32.CloseHandle(th)
        log("-- [NATIVE-INJECT] ★ LoadLibraryA 远程线程执行完成! tid=%d dll=%s" % (tid.value, os.path.basename(dll_path)))
        return True
    else:
        err = ctypes.get_last_error()
        log("-- [NATIVE-INJECT] CreateRemoteThread 失败 err=%d" % err)
        return False
"""
assert target_def in text, "target_def not found"
text = text.replace(target_def, extra_defs, 1)

# 2. Add injection call at the end of compat_patch_thread
target_log = 'log("-- [兼容补丁] %d/%d 全部成功 (用时 %.1fs)" % (target_count, target_count, time.time() - t0))'
extra_inject = """log("-- [兼容补丁] %d/%d 全部成功 (用时 %.1fs)" % (target_count, target_count, time.time() - t0))
        # ★ 原生服务端晚期注入: 等 .tp3 解壳完毕且补丁打完后再加载 CodolGameServer.Localnet32
        time.sleep(0.5)
        dll_candidate = r"D:\\BaiduNetdiskDownload\\使命召唤OL\\run_codol_001\\sandbox_datafix_20260929\\Ayria\\Plugins\\CodolGameServer.Localnet32"
        inject_dll_late(h, log, dll_candidate)"""
assert target_log in text, "target_log not found"
text = text.replace(target_log, extra_inject, 1)

with open(src, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully updated nt10.py with late DLL injection hook!")
