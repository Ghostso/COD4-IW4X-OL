with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

old_k32_init = "        # kernel32 / user32 导出与基址 (选项 A)\n        k32_base = u32_base = 0"
# Search for this block
pos = text.find("k32_base = u32_base = 0")
print("Found k32_base = u32_base = 0 at pos:", pos)
assert pos != -1, "k32_base init not found"

new_k32_init = """        # 无论 apis 是否有 K32_APIS，k32_base 都必须从 ml 严格解析 (供原生注入跳板使用)
        k32_base = next((b for n, b, s in ml if n.lower().startswith("kernel32")), 0) or 0x76D70000
        u32_base = 0"""

text = text[:pos] + new_k32_init + text[pos + len("k32_base = u32_base = 0"):]

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully fixed k32_base resolution in nt10.py!")
