import shutil, os

src = r"REF_LOBBY_KIT\nt10.py"
clean_bak = r"REF_LOBBY_KIT\nt10.py.bak_before_native_inject"
shutil.copy2(clean_bak, src)
print(f"Restored {src} from clean backup")

with open(src, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add definitions for CreateRemoteThread and WaitForSingleObject
target_def = 'k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]'
extra_defs = """k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
k32.CreateRemoteThread.restype = wintypes.HANDLE
k32.CreateRemoteThread.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                   ctypes.POINTER(wintypes.DWORD)]
k32.WaitForSingleObject.restype = wintypes.DWORD
k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

def native_server_inject_thread(h, log, page, slot_index, stop, dll_path, deadline=60.0):
    cave = page + slot_index * SLOT
    data_str = cave + 0x100
    flag_addr = cave + 0x200
    hmod_addr = cave + 0x204
    
    if not os.path.isfile(dll_path):
        log("-- [NATIVE-SERVER] 找不到 DLL: %s" % dll_path)
        return
    
    raw_path = dll_path.encode("latin1", "replace") + b"\\x00"
    wpm(h, data_str, raw_path)
    wpm(h, flag_addr, b"\\x00\\x00\\x00\\x00")
    wpm(h, hmod_addr, b"\\x00\\x00\\x00\\x00")
    
    k32_mod = k32.GetModuleHandleA(b"kernel32.dll")
    p_load_lib = k32.GetProcAddress(k32_mod, b"LoadLibraryA")
    
    code = bytearray()
    code += b"\\x83\\x3d" + struct.pack("<I", flag_addr) + b"\\x01" # cmp dword ptr [flag_addr], 1
    code += b"\\x74\\x19"                                         # je +0x19 (to ret 4)
    code += b"\\xc7\\x05" + struct.pack("<II", flag_addr, 1)       # mov dword ptr [flag_addr], 1
    code += b"\\x68" + struct.pack("<I", data_str)               # push data_str
    code += b"\\xb8" + struct.pack("<I", p_load_lib)             # mov eax, p_load_lib
    code += b"\\xff\\xd0"                                         # call eax
    code += b"\\xa3" + struct.pack("<I", hmod_addr)              # mov [hmod_addr], eax
    code += b"\\xc2\\x04\\x00"                                     # ret 4
    
    _wpm_code(h, cave, bytes(code))
    log("-- [NATIVE-SERVER] 注入桩已就绪 @ 0x%08X (DLL=%s)" % (cave, os.path.basename(dll_path)))
    
    t0 = time.time()
    while not stop.is_set() and time.time() - t0 < deadline:
        b = rpm(h, 0x0077F6EF, 2)
        if b == b"\\xeb\\x36":
            time.sleep(0.8) # 等待 0.8s 确保全部代码页解密完成
            tid = wintypes.DWORD(0)
            th = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(cave), None, 0, ctypes.byref(tid))
            if th:
                k32.WaitForSingleObject(th, 3000)
                k32.CloseHandle(th)
                hmod_bytes = rpm(h, hmod_addr, 4)
                hmod = struct.unpack("<I", hmod_bytes)[0] if len(hmod_bytes) == 4 else 0
                log("-- [NATIVE-SERVER] ★ 原生服务端 DLL 注入成功! HMODULE=0x%08X (tid=%d)" % (hmod, tid.value))
                break
            else:
                err = ctypes.get_last_error()
                log("-- [NATIVE-SERVER] CreateRemoteThread 失败 err=%d, 稍后重试..." % err)
        time.sleep(0.3)
"""
assert target_def in text, "target_def not found"
text = text.replace(target_def, extra_defs, 1)

# 2. Add thread spawn in run_client right beside kdf_hook_thread
target_kdf_spawn = 'log("-- [KDF] 抓取线程已启动 (hook 0x%08X, 槽 %d)" % (KDF_HMAC_VA, len(apis) + 6))'
extra_native_spawn = """log("-- [KDF] 抓取线程已启动 (hook 0x%08X, 槽 %d)" % (KDF_HMAC_VA, len(apis) + 6))
    try:
        native_dll = os.path.join(a.root, "Ayria", "Plugins", "CodolGameServer.Localnet32")
        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, native_dll),
                         daemon=True).start()
        log("-- [NATIVE-SERVER] 晚期注入监控线程已启动 (槽 %d, 目标=%s)" % (len(apis) + 5, native_dll))
    except Exception as _e:
        log("-- [NATIVE-SERVER] 注入线程启动异常: %r" % (_e,))"""
assert target_kdf_spawn in text, "target_kdf_spawn not found"
text = text.replace(target_kdf_spawn, extra_native_spawn, 1)

with open(src, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully injected native_server_inject_thread into nt10.py!")
