with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

target = 'log("  [SCAN] %-22s 命中 VA 0x%08X (RVA 0x%X)" % (name, va, va - base))'
# Check if encoded or with special chars
pos = text.find('found[name] = va')
print("Found 'found[name] = va' at pos:", pos)
if pos != -1:
    line_end = text.find("\n", pos)
    # The next line is the log statement
    log_end = text.find("\n", line_end + 1)
    old_stmt = text[pos:log_end]
    print("Old stmt repr:", repr(old_stmt))
    
    new_stmt = old_stmt + """\n                        if name == "SV_UnlinkEntity":
                            dump_block = rpm(h, va - 0x800, 0x1000)
                            if dump_block:
                                open("unpacked_link_chunk.bin", "wb").write(dump_block)
                                log("  [DUMP] 已落盘 SV_UnlinkEntity 前后 4KB 内存 -> unpacked_link_chunk.bin (VA 0x%08X)" % (va - 0x800))"""
    text = text[:pos] + new_stmt + text[log_end:]
    with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Successfully added 4KB memory dump around SV_UnlinkEntity to nt10.py!")
else:
    print("Not found found[name] = va!")
