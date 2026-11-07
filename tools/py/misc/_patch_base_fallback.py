with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

old_block = """    base, size = get_module_base(pid, exe)
    if not base:
        log("-- [TRACE] 取模块基址失败(pid=%d) -> 放弃" % pid)
        return"""

# Check if encoded or with special chars
pos = text.find("base, size = get_module_base(pid, exe)")
print("Found get_module_base at pos:", pos)
if pos != -1:
    end_return = text.find("return", pos) + len("return")
    print("Old block repr:", repr(text[pos:end_return]))
    new_block = """base, size = get_module_base(pid, exe)
    if not base:
        base, size = 0x00400000, 0x0E659000
        log("-- [TRACE] Toolhelp 模块基址未取到，使用固定基址 0x%08X size=0x%X" % (base, size))"""
    text = text[:pos] + new_block + text[end_return:]
    with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Successfully patched trace_probe_thread base fallback!")
else:
    print("Not found get_module_base!")
