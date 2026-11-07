with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Line 88 (index 87)
lines[87] = '    log("-- [NATIVE-SERVER] 32位 kernel32=0x%08X, LoadLibraryA=0x%08X (目标=%s)" % (k32_base, p_load_lib, dll_name))\n'

# Line 101 (index 100)
lines[100] = '    log("-- [NATIVE-SERVER] 注入桩机器码已写入 @ 0x%08X (DLL=%s)" % (cave, dll_name))\n'

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Fixed line 88 and line 101 in nt10.py successfully!")
