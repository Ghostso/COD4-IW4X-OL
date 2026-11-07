with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# Update native_server_inject_thread definition
old_func = """def native_server_inject_thread(h, log, page, slot_index, stop, dll_path, deadline=60.0):
    cave = page + slot_index * SLOT
    data_str = cave + 0x100
    flag_addr = cave + 0x200
    hmod_addr = cave + 0x204
    
    if not os.path.isfile(dll_path):
        log("-- [NATIVE-SERVER] 找不到 DLL: %s" % dll_path)
        return
    
    raw_path = dll_path.encode("latin1", "replace") + b"\\x00" """

new_func = """def native_server_inject_thread(h, log, page, slot_index, stop, dll_name, root_dir, deadline=60.0):
    cave = page + slot_index * SLOT
    data_str = cave + 0x100
    flag_addr = cave + 0x200
    hmod_addr = cave + 0x204
    
    full_path = os.path.join(root_dir, dll_name)
    if not os.path.isfile(full_path):
        log("-- [NATIVE-SERVER] 找不到 DLL: %s" % full_path)
        return
    
    raw_path = dll_name.encode("ascii") + b"\\x00" """

assert old_func in text, "old_func not found"
text = text.replace(old_func, new_func, 1)

# Update thread launch call
old_spawn = """        native_dll = os.path.join(a.root, "Ayria", "Plugins", "CodolGameServer.Localnet32")
        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, native_dll),
                         daemon=True).start()
        log("-- [NATIVE-SERVER] 晚期注入监控线程已启动 (槽 %d, 目标=%s)" % (len(apis) + 5, native_dll))"""

new_spawn = """        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, "CodolGameServer.dll", a.root),
                         daemon=True).start()
        log("-- [NATIVE-SERVER] 晚期注入监控线程已启动 (槽 %d, 目标=CodolGameServer.dll)" % (len(apis) + 5))"""

assert old_spawn in text, "old_spawn not found"
text = text.replace(old_spawn, new_spawn, 1)

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated nt10.py to inject pure ASCII CodolGameServer.dll from game root!")
