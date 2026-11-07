"""找 dwRoomMatch::Init() 的调用点及其条件。

符号: ??Init@dwRoomMatch@@SAXXZ@  (static void)

策略:
  1. 该符号名字在 .rdata，函数体在 .text。
  2. 静态函数 Init 通常在某处被主动调用（启动 / 进大厅 / 建房时）。
  3. 先找函数体：搜特征（函数入口通常 push ebp; mov ebp,esp; ... 然后
     构造局部对象 MyEventHandler）。

更实际：直接搜 `MyEventHandler` 的 RTTI 名字地址被引用的位置，
那必然是 Init 内部（vtable 赋值）。
"""
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b'\x00').decode('latin1'), base + s.VirtualAddress,
         s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
data = open(EXE, 'rb').read()


def va_of(o):
    for n, va, vs, pr, rs in secs:
        if pr <= o < pr + rs:
            return va + (o - pr)
    return None


def off_of(va):
    for n, sva, vs, pr, rs in secs:
        if sva <= va < sva + vs:
            o = pr + (va - sva)
            if o < len(data):
                return o
    return None


# 1) MyEventHandler 的 RTTI 名
nm = b'.?AVMyEventHandler@?5??Init@dwRoomMatch@@SAXXZ@'
o = data.find(nm)
print('MyEventHandler RTTI 名 @ 文件偏移 0x%X, VA 0x%08X' % (o, va_of(o)))
td = va_of(o) - 9
print('TD = 0x%08X' % td)

# 2) 引用该 TD 的位置 -> COL
needle = struct.pack('<I', td)
hits = []
i = data.find(needle)
while i >= 0 and len(hits) < 20:
    hits.append(i)
    i = data.find(needle, i + 1)
print('TD 被引用 %d 处: %s' % (len(hits), [hex(h) for h in hits[:8]]))

md = Cs(CS_ARCH_X86, CS_MODE_32)

# 3) 对每个引用点判断：是在 .text（代码立即数）还是 .rdata（COL）
for h in hits:
    va = va_of(h)
    sec = None
    for n, sva, vs, pr, rs in secs:
        if pr <= h < pr + rs:
            sec = n
            break
    print()
    print('--- 引用 @ 文件 0x%X, VA 0x%08X, 节 %s ---' % (h, va, sec))
    if sec == '.tp3':
        # 可能是 COL（pTD 在 +0x0C，所以 COL 起点 = h - 12）
        col_off = h - 12
        if col_off >= 0:
            sig, off_, cd, ptd = struct.unpack_from('<IIII', data, col_off)
            if sig == 0:
                col_va = va_of(col_off)
                print('  ✓ 像 COL: VA=0x%08X (sig=0, off=%d, cd=%d, pTD=0x%08X)'
                      % (col_va, off_, cd, ptd))
                # 找 vtable
                cn = struct.pack('<I', col_va)
                j = data.find(cn)
                while j >= 0:
                    vt = j + 4
                    v0, v1 = struct.unpack_from('<II', data, vt)
                    if 0x400000 <= v0 < 0x1000000:
                        print('     vtable @ VA 0x%08X  slots[0]=0x%08X slots[1]=0x%08X'
                              % (va_of(j), v0, v1))
                        break
                    j = data.find(cn, j + 1)
