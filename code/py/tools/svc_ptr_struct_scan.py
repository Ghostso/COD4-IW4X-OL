#!/usr/bin/env python3
"""本地硬证据: 在 E 镜像里找指向服务名 C 串的指针, 检验是否有 {u32 id, char* name} 注册表。
E 镜像 VA = file_off + 0x400000 (RVA==offset 对前 3 节成立)。
"""
import struct
E = r"E:\codol_re\client_image_20261027.bin"
data = open(E, "rb").read()
N = len(data)
BASE = 0x400000

def find_nullstr(name):
    """返回所有 null-terminated name 的文件偏移"""
    nb = name + b"\x00"
    res = []; i = 0
    while True:
        p = data.find(nb, i)
        if p < 0: break
        res.append(p); i = p + 1
    return res

targets = ["messaging", "marketplace", "matchmaking", "storage", "profiles",
           "titleutilities", "tencent", "teams", "friends", "mail",
           "eventlog", "pooledstorage", "stats", "reward", "group", "tags",
           "contentunlock", "richpresence"]

print("=== 每个服务名: 出现次数 + VA ===")
all_offsets = {}
for t in targets:
    offs = find_nullstr(t.encode())
    all_offsets[t] = offs
    print("  %-16s n=%d  %s" % (t, len(offs), ["0x%X(VA 0x%X)"%(o, o+BASE) for o in offs[:6]]))

# 收集所有服务名的 VA
va_set = set()
va_map = {}
for t, offs in all_offsets.items():
    for o in offs:
        va = o + BASE
        va_set.add(va)
        va_map[va] = t

print("\n=== 搜指针 (u32==服务名VA), 并看邻域有无 u32 小整数 (id) ===")
# 指针表通常连续; 扫描整个镜像的 u32
found_pairs = []
step = 4
for off in range(0, N-4, step):
    v = struct.unpack_from("<I", data, off)[0]
    if v in va_set:
        # 看前面 4 字节是否小整数 (1..300) 或 后面
        prev = struct.unpack_from("<I", data, off-4)[0] if off >= 4 else 0
        nxt  = struct.unpack_from("<I", data, off+4)[0] if off+8 <= N else 0
        found_pairs.append((off, va_map[v], v, prev, nxt))

print("命中指针数:", len(found_pairs))
for off, name, va, prev, nxt in found_pairs[:80]:
    print("  @0x%08X  name=%-14s ptrVA=0x%X  prev_u32=%-6d next_u32=0x%X" %
          (off+BASE, name, va, prev if prev < 100000 else -1, nxt))
