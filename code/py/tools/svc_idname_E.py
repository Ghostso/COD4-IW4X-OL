#!/usr/bin/env python3
"""在 E 镜像 (241MB) 里找 {u32 id, u32 nameptr} 记录表, 只报含 Service 名或 id 含 102 的。"""
import struct
PATH = r"E:\codol_re\client_image_20261027.bin"
data = open(PATH, "rb").read()
N = len(data)
BASE = 0x400000  # 假设镜像按 VA 布局, 指针直接是 VA; 也可能是 RVA

def str_at(o):
    if not (0 <= o < N): return None
    e = data.find(b"\x00", o)
    if e < 0 or not (2 <= e-o <= 48): return None
    seg = data[o:e]
    if not all(32<=c<127 for c in seg): return None
    return seg.decode("ascii")

# 先看镜像是不是按 VA 映射: 找 .text 里 "CommManager" 的 VA 是否等于偏移
# 已知字符串在偏移 0x352FA00 附近. 若镜像按 VA 且 imagebase=0x400000, 则文件偏移=VA-0x400000? 不对, 文件偏移=VA-imagebase.
# 先试两种解释: ptr 为 VA (offset=ptr-BASE) 或 ptr 为文件偏移 (offset=ptr)
def rec_at(p, mode):
    if p+8>N: return None
    idv, ptr = struct.unpack_from("<II", data, p)
    if not (0 <= idv <= 0x10000): return None
    o = ptr - BASE if mode=="va" else ptr
    s = str_at(o)
    if s is None: return None
    return (idv, s)

for mode in ("va","file"):
    print("=== mode=%s ==="%mode)
    p=0; found=0
    while p+8<=N:
        r=rec_at(p,mode)
        if r:
            seq=[r]; q=p+8
            while q+8<=N:
                r2=rec_at(q,mode)
                if not r2 or r2[0]<=seq[-1][0]: break
                seq.append(r2); q+=8
            if len(seq)>=5:
                # 只报含 Service 名 或 id==102 的表
                joined=" ".join(s for _,s in seq)
                if "Service" in joined or any(i==102 for i,_ in seq):
                    print("--- @0x%X %d条 ---"%(p,len(seq)))
                    for i,s in seq:
                        mark = " <==102" if i==102 else ""
                        print("   %5d %r%s"%(i,s,mark))
                p=q; found+=1; continue
        p+=4
    print("  总表数(>=5):",found)
