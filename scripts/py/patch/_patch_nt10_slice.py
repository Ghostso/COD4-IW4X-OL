with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

start_marker = "def native_server_inject_thread("
end_marker = "k32_mod = k32.GetModuleHandleA(b\"kernel32.dll\")"

start_pos = text.find(start_marker)
end_pos = text.find(end_marker)

assert start_pos != -1, "start_marker not found"
assert end_pos != -1, "end_marker not found"

new_block = """def native_server_inject_thread(h, log, page, slot_index, stop, dll_path, deadline=60.0):
    cave = page + slot_index * SLOT
    data_str = cave + 0x100
    flag_addr = cave + 0x200
    hmod_addr = cave + 0x204
    
    # 纯 ASCII 相对文件名，由 Windows DLL 加载器直接从游戏根目录加载
    dll_name = "CodolGameServer.dll"
    raw_path = dll_name.encode("ascii") + b"\\x00"
    wpm(h, data_str, raw_path)
    wpm(h, flag_addr, b"\\x00\\x00\\x00\\x00")
    wpm(h, hmod_addr, b"\\x00\\x00\\x00\\x00")
    
    """

text = text[:start_pos] + new_block + text[end_pos:]

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully replaced native_server_inject_thread with CodolGameServer.dll loader!")
