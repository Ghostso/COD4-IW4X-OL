with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix line 101
old_line = 'log("-- [NATIVE-SERVER] 注入桩已就绪 @ 0x%08X (DLL=%s)" % (cave, os.path.basename(dll_path)))'
# Check if encoded or with special chars
pattern = 'log("-- [NATIVE-SERVER]'
pos = text.find(pattern)
print("Found log at pos:", pos)
if pos != -1:
    line_end = text.find("\n", pos)
    print("Old line:", text[pos:line_end])
    new_line = 'log("-- [NATIVE-SERVER] 注入桩已就绪 @ 0x%08X (DLL=%s)" % (cave, dll_name))'
    text = text[:pos] + new_line + text[line_end:]

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed line 101 successfully!")
