with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# Update native_server_inject_thread to capture GetLastError
start_marker = "p_load_lib = (k32_base + 0x20E70) & 0xFFFFFFFF"
end_marker = "_wpm_code(h, cave, bytes(code))"

start_pos = text.find(start_marker)
end_pos = text.find(end_marker)

assert start_pos != -1, "start_marker not found"
assert end_pos != -1, "end_marker not found"

new_code_block = """p_load_lib = (k32_base + 0x20E70) & 0xFFFFFFFF
    p_get_last_err = (k32_base + 0x1E2B0) & 0xFFFFFFFF
    err_addr = cave + 0x208
    wpm(h, err_addr, b"\\x00\\x00\\x00\\x00")
    log("-- [NATIVE-SERVER] 32位 kernel32=0x%08X, LoadLibraryA=0x%08X, GetLastError=0x%08X (目标=%s)"
        % (k32_base, p_load_lib, p_get_last_err, dll_name))
    
    code = bytearray()
    code += b"\\x83\\x3d" + struct.pack("<I", flag_addr) + b"\\x01" # cmp dword ptr [flag_addr], 1
    code += b"\\x74\\x25"                                         # je +0x25 (to ret 4)
    code += b"\\xc7\\x05" + struct.pack("<II", flag_addr, 1)       # mov dword ptr [flag_addr], 1
    code += b"\\x68" + struct.pack("<I", data_str)               # push data_str
    code += b"\\xb8" + struct.pack("<I", p_load_lib)             # mov eax, p_load_lib
    code += b"\\xff\\xd0"                                         # call eax (LoadLibraryA)
    code += b"\\xa3" + struct.pack("<I", hmod_addr)              # mov [hmod_addr], eax
    code += b"\\xb8" + struct.pack("<I", p_get_last_err)         # mov eax, p_get_last_err
    code += b"\\xff\\xd0"                                         # call eax (GetLastError)
    code += b"\\xa3" + struct.pack("<I", err_addr)               # mov [err_addr], eax
    code += b"\\xc2\\x04\\x00"                                     # ret 4
    """

text = text[:start_pos] + new_code_block + text[end_pos:]

# Update the log line after CreateRemoteThread
target_log = 'log("-- [NATIVE-SERVER] ★ 原生服务端 DLL 注入成功! HMODULE=0x%08X (tid=%d)" % (hmod, tid.value))'
new_log = """err_bytes = rpm(h, err_addr, 4)
                last_err = struct.unpack("<I", err_bytes)[0] if len(err_bytes) == 4 else 0
                log("-- [NATIVE-SERVER] ★ 注入线程返回! HMODULE=0x%08X, GetLastError=%d (tid=%d)" % (hmod, last_err, tid.value))"""

assert target_log in text, "target_log not found"
text = text.replace(target_log, new_log, 1)

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated nt10.py to capture GetLastError from remote LoadLibraryA!")
