"""任务6：全 .text 的 socket/网络 API 调用点普查（同时扫 FF 15 与 FF 25）。

铁律：
  * PE 里 `call dword ptr [abs]` = FF 15，`jmp dword ptr [abs]` = FF 25（跳转桩）。
    importmap.xrefs 只扫 FF 15，经桩表的调用会被整片漏掉。
  * 上界必须用 len(img.data)-5，否则 E8 命中落在文件末尾会 struct.error。
  * 所有地址一律 **RVA**；img.read/cstr 收 RVA。
"""
import struct
import sys
import collections

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
from pe import Image
import importmap

IMAGE_BASE = 0x10000000
img = Image()
slots = importmap.build(img)
sec = [s for s in img.sections if s['name'] == '.text'][0]
TEXT_LO = sec['raw']                      # 文件偏移
TEXT_HI = sec['raw'] + sec['rawsize']
FEND = len(img.data) - 5

# ---------- 1) FF 15 直接调用 ----------
direct = collections.defaultdict(list)     # slot_rva -> [site_rva]
i = img.data.find(b'\xff\x15', TEXT_LO, TEXT_HI)
while i >= 0:
    tgt = struct.unpack_from('<I', img.data, i + 2)[0] - IMAGE_BASE
    if tgt in slots:
        direct[tgt].append(img.voff(i))
    i = img.data.find(b'\xff\x15', i + 1, TEXT_HI)

# ---------- 2) FF 25 跳转桩 ----------
thunks = collections.defaultdict(list)     # slot_rva -> [thunk_rva]
thunk_addr = {}                            # thunk_rva -> slot_rva
i = img.data.find(b'\xff\x25', TEXT_LO, TEXT_HI)
while i >= 0:
    tgt = struct.unpack_from('<I', img.data, i + 2)[0] - IMAGE_BASE
    if tgt in slots:
        r = img.voff(i)
        thunks[tgt].append(r)
        thunk_addr[r] = tgt
    i = img.data.find(b'\xff\x25', i + 1, TEXT_HI)

# ---------- 3) 桩的 E8 调用者 ----------
viacall = collections.defaultdict(list)    # slot_rva -> [(caller_rva, thunk_rva)]
if thunk_addr:
    # 只扫 .text 内部（E8 在别的节里不是 x86 代码）；上界仍留 5 字节余量
    i = img.data.find(b'\xe8', TEXT_LO, min(TEXT_HI, FEND))
    n = 0
    while i >= 0:
        n += 1
        here = img.voff(i)
        if here is not None:
            rel = struct.unpack_from('<i', img.data, i + 1)[0]
            tgt = here + 5 + rel
            if tgt in thunk_addr:
                viacall[thunk_addr[tgt]].append((here, tgt))
        i = img.data.find(b'\xe8', i + 1, min(TEXT_HI, FEND))
    print('# E8 扫描指令数（粗）: %d' % n)

# ---------- 4) 合并 ----------
allpts = collections.defaultdict(set)
for s, pts in direct.items():
    allpts[s].update(pts)
for s, pts in viacall.items():
    allpts[s].update(p for p, _ in pts)

WANT = ('socket', 'WSASocket', 'accept', 'WSAAccept', 'connect', 'bind', 'listen',
        'send', 'recv', 'WSAEventSelect', 'WSAWaitForMultipleEvents', 'select',
        'ioctlsocket', 'WSAEnumNetworkEvents', 'WSAIoctl', 'getaddrinfo',
        'gethostbyname', 'WSAStartup', 'closesocket', 'shutdown', 'setsockopt',
        'getsockopt', 'getpeername', 'getsockname', 'GetAddrInfo',
        'WSARecv', 'WSASend', 'WSACreateEvent')

print('\n=== 目标 API 调用点（direct=FF15 / via=FF25桩） ===')
for rva in sorted(allpts):
    lab = slots.get(rva)
    if not lab:
        continue
    if not any(k in lab for k in WANT):
        continue
    d = sorted(set(direct.get(rva, [])))
    v = sorted(set(p for p, _ in viacall.get(rva, [])))
    print('\n%-38s slot 0x%06x  direct=%d via=%d' % (lab, rva, len(d), len(v)))
    for p in d:
        print('    D 0x%06x' % p)
    for p in v:
        print('    V 0x%06x' % p)

# ---------- 5) 每个槽的汇总（含非目标） ----------
print('\n=== 有调用点的槽汇总 ===')
tot = 0
for rva in sorted(allpts):
    n = len(allpts[rva])
    tot += n
    print('  %-40s 0x%06x  %3d' % (slots.get(rva, '?'), rva, n))
print('槽 %d 个，调用点合计 %d' % (len(allpts), tot))
