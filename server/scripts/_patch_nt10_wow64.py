with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update native_server_inject_thread to take k32_base and use (k32_base + 0x20E70)
start_marker = "def native_server_inject_thread("
end_marker = "code = bytearray()"

start_pos = text.find(start_marker)
end_pos = text.find(end_marker)

assert start_pos != -1, "start_marker not found"
assert end_pos != -1, "end_marker not found"

new_head = """def native_server_inject_thread(h, log, page, slot_index, stop, dll_name, root_dir, k32_base, deadline=60.0):
    cave = page + slot_index * SLOT
    data_str = cave + 0x100
    flag_addr = cave + 0x200
    hmod_addr = cave + 0x204
    
    # 纯 ASCII 相对文件名，由 Windows DLL 加载器直接从游戏根目录加载
    raw_path = dll_name.encode("ascii") + b"\\x00"
    wpm(h, data_str, raw_path)
    wpm(h, flag_addr, b"\\x00\\x00\\x00\\x00")
    wpm(h, hmod_addr, b"\\x00\\x00\\x00\\x00")
    
    # 32位 kernel32.dll 的 LoadLibraryA RVA 是 0x20E70
    p_load_lib = (k32_base + 0x20E70) & 0xFFFFFFFF
    log("-- [NATIVE-SERVER] 32位 kernel32=0x%08X, LoadLibraryA=0x%08X" % (k32_base, p_load_lib))
    
    """

text = text[:start_pos] + new_head + text[end_pos:]

# 2. Update thread call site to pass k32_base
call_marker = 'threading.Thread(target=native_server_inject_thread,'
call_pos = text.find(call_marker)
assert call_pos != -1, "call_marker not found"

# Find lines around call_pos
call_end = text.find(".start()", call_pos) + len(".start()")
old_call_block = text[call_pos:call_end]

new_call_block = """k32_wow64 = next((b for n, b, s in ml if n.lower().startswith("kernel32")), 0)
        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, "CodolGameServer.dll", a.root, k32_wow64),
                         daemon=True).start()"""

text = text[:call_pos] + new_call_block + text[call_end:]

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully updated nt10.py with 32-bit LoadLibraryA RVA calculation!")
