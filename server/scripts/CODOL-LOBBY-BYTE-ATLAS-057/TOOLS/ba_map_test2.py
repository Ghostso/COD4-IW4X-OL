# -*- coding: utf-8 -*-
"""确定 image 的真实映射: 逐节寻找 header/节头声明的数据."""
import struct

IMG = r"E:\codol_re\client_image_20261027.bin"
d = open(IMG, "rb").read()
N = len(d)
BASE = 0x400000

# PE 解析
e = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, e + 6)[0]
optsz = struct.unpack_from("<H", d, e + 20)[0]
opt = e + 24
sizeimage = struct.unpack_from("<I", d, opt + 56)[0]
secoff = opt + optsz
secs = []
for i in range(nsec):
    o = secoff + i * 40
    name = d[o:o + 8].rstrip(b"\0")
    vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
    ch = struct.unpack_from("<I", d, o + 36)[0]
    secs.append(dict(i=i, name=name, vs=vs, va=va, rs=rs, rp=rp, ch=ch))

print("file size = 0x%08X   SizeOfImage = 0x%08X" % (N, sizeimage))
print()
print("%-3s %-10s %10s %10s %10s %10s %10s %s"
      % ("#", "name", "VA", "VSize", "RawPtr", "RawSize", "VA+VSize", "Chars"))
for s in secs:
    print("%-3d %-10s 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X"
          % (s["i"], s["name"].decode("latin1"), s["va"], s["vs"],
             s["rp"], s["rs"], s["va"] + s["vs"], s["ch"]))

print()
print("=== 关键: 检查每个节 VA 处 是否真的在 RawPtr 处 ===")
for s in secs:
    if s["vs"] < 16:
        continue
    print("\n节 %d %s: 声明 RawPtr=0x%08X, VA=0x%08X"
          % (s["i"], s["name"].decode("latin1"), s["rp"], s["va"]))
    for cand, lbl in ((s["rp"], "RawPtr"),
                      (s["va"], "VA"),
                      (s["va"] - BASE, "VA-BASE")):
        if 0 <= cand < N - 16:
            print("  @%-8s 0x%08X  %s" % (lbl, cand, d[cand:cand + 16].hex(" ")))
        else:
            print("  @%-8s 0x%08X  OUT" % (lbl, cand))

print()
print("=== 验证: 在整份文件中搜索入口点前的已知结构 ===")
# codoMP_client_shipRetailBase.dll 字符串
needle = b"codoMP_client_shipRetailBase.dll"
i = d.find(needle)
while i >= 0:
    print("  '%s' @ file_off 0x%08X" % (needle.decode(), i))
    i = d.find(needle, i + 1)

# 找入口点字节序列 ff 15 65 c6 9d 0e (VA 形式) 或 其它
print()
for pat, lbl in ((b"\xff\x15\x65\xc6\x9d\x0e", "call [0x0E9DC665] VA形式"),
                 (b"\xff\x15\x65\xc6\x5d\x0e", "call [0x0E5DC665] RVA形式"),
                 (b"\xff\x15\x69\xc6\x9d\x0e", "call [0x0E9DC669]")):
    i = d.find(pat)
    cnt = 0
    while i >= 0 and cnt < 5:
        print("  %-24s @ file_off 0x%08X" % (lbl, i))
        i = d.find(pat, i + 1)
        cnt += 1
    if cnt == 0:
        print("  %-24s 未找到" % lbl)
