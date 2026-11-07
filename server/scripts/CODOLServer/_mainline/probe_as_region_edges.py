"""验证: AS_* 名字是否通过"名字字符串地址"被引用。

之前搜 dword 引用得 0，但那只覆盖"绝对地址立即数"。
运行期注册常用的是:
    - 结构体数组 { name_ptr, handler }  —— dword 引用，已排除
    - 按名查找: 传字符串指针 —— 也是 dword 引用
    - 名字从别处拷贝/拼接 —— 无静态引用

第三种情况会让静态搜索完全失效。

本脚本：在快照里看 0xE76C00 这块**前后紧邻**是什么，
判断它是不是一段连续的、独立的 RTTI 字符串池（而非注册表）。
"""
import json
import os
import struct

RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
snap = 'snap_003'
meta = json.load(open(os.path.join(RUN, snap + '.json'), encoding='utf-8'))
lo = meta['lo']
cov = open(os.path.join(RUN, snap + '_cover.bin'), 'r+b')
f = open(os.path.join(RUN, snap + '.bin'), 'rb')


def read(va, n):
    off = va - lo
    if off < 0:
        return None
    cov.seek(off)
    if cov.read(n) != b'\x01' * n:
        return None
    f.seek(off)
    d = f.read(n)
    return d if len(d) == n else None


# 检查 snap_003 里这块的边界：往前/往后各看 0x800
for base in (0x00E74000, 0x00E75000, 0x00E75800, 0x00E77000, 0x00E77800):
    d = read(base, 0x100)
    if not d:
        print('0x%08X 不可读' % base)
        continue
    # 判断这块是字符串还是别的
    printable = sum(1 for c in d if 32 <= c < 127 or c == 0) / len(d)
    first = d[:24]
    print('0x%08X 可打印率=%.0f%% 前24B=%s' % (base, printable * 100, first.hex()))

# 关键: 看 AS_* 块之后紧接的是什么
print()
print('=== 0xE76E00 之后（AS_* 块结束处）===')
d = read(0x00E76E00, 0x400)
if d:
    cur, cs = bytearray(), None
    for i, c in enumerate(d):
        if 32 <= c < 127:
            if cs is None:
                cs = i
            cur.append(c)
        else:
            if len(cur) >= 4:
                print('   0x%08X  %s' % (0x00E76E00 + cs, cur.decode()))
            cur, cs = bytearray(), None

print()
print('=== 0xE75C00（AS_* 块之前）===')
d = read(0x00E75C00, 0x400)
if d:
    cur, cs = bytearray(), None
    for i, c in enumerate(d):
        if 32 <= c < 127:
            if cs is None:
                cs = i
            cur.append(c)
        else:
            if len(cur) >= 4:
                print('   0x%08X  %s' % (0x00E75C00 + cs, cur.decode()))
            cur, cs = bytearray(), None

cov.close()
f.close()
