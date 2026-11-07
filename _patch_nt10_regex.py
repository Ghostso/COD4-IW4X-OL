with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace dll_path check and encode
old_part = """    if not os.path.isfile(dll_path):
        log("-- [NATIVE-SERVER] 找不到 DLL: %s" % dll_path)
        return
    
    raw_path = dll_path.encode("latin1", "replace") + b"\\x00" """

# Let's inspect what lines are actually there
import re
pattern = r'def native_server_inject_thread\(h, log, page, slot_index, stop, dll_path, deadline=60\.0\):.*?(?=k32_mod =)'
replacement = """def native_server_inject_thread(h, log, page, slot_index, stop, dll_path, deadline=60.0):
    cave = page + slot_index * SLOT
    data_str = cave + 0x100
    flag_addr = cave + 0x200
    hmod_addr = cave + 0x204
    
    # 使用纯 ASCII 相对文件名，由 Windows DLL 加载器直接从游戏当前目录加载
    dll_name = "CodolGameServer.dll"
    raw_path = dll_name.encode("ascii") + b"\\x00"
    wpm(h, data_str, raw_path)
    wpm(h, flag_addr, b"\\x00\\x00\\x00\\x00")
    wpm(h, hmod_addr, b"\\x00\\x00\\x00\\x00")
    
    """

new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
assert count == 1, f"Pattern match count: {count}"

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(new_text)

print("Updated native_server_inject_thread to use CodolGameServer.dll ASCII name!")
