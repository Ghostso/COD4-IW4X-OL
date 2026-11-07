with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

old_inject_tramp = """    if inject_pending and inject_work:
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

new_inject_tramp = """    if inject_pending and inject_work:
        c += b"\\x9C"                                       # pushfd
        c += b"\\x60"                                       # pushad
        c += b"\\x80\\x3D" + struct.pack("<I", inject_pending) + b"\\x00"  # cmp byte [inj_pend], 0
        je_pos2 = len(c) + 1
        c += b"\\x74\\x00"                                  # je skip
        call_pos2 = len(c) + 1
        c += b"\\xE8\\x00\\x00\\x00\\x00"                      # call <inject_work>
        c[call_pos2:call_pos2 + 4] = struct.pack(
            "<i", inject_work - (cave_addr + call_pos2 + 4))
        c[je_pos2] = len(c) - (je_pos2 + 1)
        c += b"\\x61"                                       # popad
        c += b"\\x9D"                                       # popfd"""

assert old_inject_tramp in text, "old_inject_tramp not found"
text = text.replace(old_inject_tramp, new_inject_tramp, 1)

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully updated inject_pending to cmp byte ptr [inj_pend], 0 in nt10.py!")
