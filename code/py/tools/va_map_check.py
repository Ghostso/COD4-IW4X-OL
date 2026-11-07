#!/usr/bin/env python3
"""决定性检验: 字符串 file offset 与 VA 的映射。
  lobby_server 说 0x8435D0 = 'c3' 是被编空的断言。
  若 VA = file + 0x400000:
     0x883500(file) -> VA 0xC83500
     0x883D50(file) -> VA 0xC83D50
     CLIENTCHAL file 0x95A4E8 -> VA 0xD5A4E8 (与 memory 记录一致 -> 命中!)
  那么 0x8435D0 反推 file = 0x4435D0。看那里是什么。
  另外看: 0x8435D0 附近, 和 0x4435D0 附近。
"""
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read()
def dump(lo,hi,label):
    print("=== %s file0x%X (VAfile+0x400000=0x%X) ==="%(label,lo,lo+0x400000))
    for i in range(lo,hi,16):
        c=d[i:i+16]
        print("  file0x%08X  %-47s  %s"%(i," ".join("%02x"%b for b in c),
              "".join(chr(b) if 32<=b<127 else "." for b in c)))

dump(0x4435C0,0x4435F0,"若VA=file+0x400000 则 0x8435D0 对应此处")
dump(0x8435C0,0x8435F0,"file 0x8435D0 本身")

# 更: 0x8435D0 若在 .text 且是代码地址, file=0x4435D0 应是某函数的 ret
print("\n若 0x8435D0 是 VA: file=0x%X"%0x4435D0)
print("  file[0x4435D0] = %02x"%(d[0x4435D0] if 0x4435D0<len(d) else -1))

# 检查 CLIENTCHAL VA 0xD5A4E8 反推: 若 VA=file+0x400000, file=0x95A4E8 ✓ (已命中 memory)
print("\n验证: CLIENTCHAL file 0x95A4E8 -> +0x400000 = 0x%X (memory 记录 0xD5A4E8)"%(0x95A4E8+0x400000))
