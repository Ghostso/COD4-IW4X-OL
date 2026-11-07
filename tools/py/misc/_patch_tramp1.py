with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update build_tramp signature and add inject_pending logic
old_tramp_head = 'def build_tramp(count_addr, arr_addr, stolen, back_addr, cave_addr, str_off, mode="ptr",\n                trace_pending=None, trace_work=None):'
new_tramp_head = 'def build_tramp(count_addr, arr_addr, stolen, back_addr, cave_addr, str_off, mode="ptr",\n                trace_pending=None, trace_work=None, inject_pending=None, inject_work=None):'
assert old_tramp_head in text, "old_tramp_head not found"
text = text.replace(old_tramp_head, new_tramp_head, 1)

# Add inject_pending logic inside build_tramp right after trace_pending logic
old_trace_tramp = """    if trace_pending and trace_work:
        c += b"\\x9C"                                       # pushfd
        c += b"\\x60"                                       # pushad
        c += b"\\xA1" + struct.pack("<I", trace_pending)    # mov eax, <pending>
        c += b"\\x80\\x38\\x00"                               # cmp byte [eax], 0
        je_pos = len(c) + 1
        c += b"\\x74\\x00"                                   # je skip
        call_pos = len(c) + 1
        c += b"\\xE8\\x00\\x00\\x00\\x00"                       # call <trace_work> (rel32 稍后填)
        # call_pos = E8 的偏移+1(即 rel 字段起点); 下一条指令 = cave + (call_pos-1) + 5
        c[call_pos:call_pos + 4] = struct.pack(
            "<i", trace_work - (cave_addr + call_pos + 4))
        c[je_pos] = len(c) - (je_pos + 1)
        c += b"\\x61"                                       # popad
        c += b"\\x9D"                                       # popfd"""

new_trace_tramp = old_trace_tramp + """
    if inject_pending and inject_work:
        c += b"\\x9C"                                       # pushfd
        c += b"\\x60"                                       # pushad
        c += b"\\xA1" + struct.pack("<I", inject_pending)   # mov eax, <pending>
        c += b"\\x80\\x38\\x00"                               # cmp byte [eax], 0
        je_pos2 = len(c) + 1
        c += b"\\x74\\x00"                                  # je skip
        call_pos2 = len(c) + 1
        c += b"\\xE8\\x00\\x00\\x00\\x00"                      # call <inject_work>
        c[call_pos2:call_pos2 + 4] = struct.pack(
            "<i", inject_work - (cave_addr + call_pos2 + 4))
        c[je_pos2] = len(c) - (je_pos2 + 1)
        c += b"\\x61"                                       # popad
        c += b"\\x9D"                                       # popfd"""

assert old_trace_tramp in text, "old_trace_tramp not found"
text = text.replace(old_trace_tramp, new_trace_tramp, 1)

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Step 1: build_tramp updated with inject_pending!")
