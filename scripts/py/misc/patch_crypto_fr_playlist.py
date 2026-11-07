with open("REF_LOBBY_KIT/codol_crypto.py", "r", encoding="utf-8") as f:
    content = f.read()

old_code = """    ob.string("localhost")                          # 8 hostname
    ob.i32(game_type); ob.i32(playlist if playlist is not None else 1); ob.i32(0)
    ob.u32(0xFFFFFFFF)                              # 12 LicenseType"""

new_code = """    ob.string("localhost")                          # 8 hostname
    pl_val = 1 if firing_range else (playlist if playlist is not None else 1)
    ob.i32(game_type); ob.i32(pl_val); ob.i32(0)
    ob.u32(0xFFFFFFFF)                              # 12 LicenseType"""

assert old_code in content, "old_code not found in codol_crypto.py"
content = content.replace(old_code, new_code, 1)

with open("REF_LOBBY_KIT/codol_crypto.py", "w", encoding="utf-8") as f:
    f.write(content)

print("codol_crypto.py updated: firing_range forces playlist=1!")
