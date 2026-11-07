"""临时（只读）：修正 importmap.xrefs 的**桩漏检**，重做全 .text 调用点普查。

问题：importmap.xrefs() 只扫 `FF 15 <abs32>`（call dword ptr [abs]）。
      `FF 25 <abs32>`（jmp dword ptr [abs]）形式的**跳转桩**被完全漏掉。
      实例：0x104530e0-0x10453160 是一整块 `jmp [slot]` 桩表，
      任何经由这些桩调用 socket/connect/closesocket/WSAStartup 的代码
      在旧普查里**根本不存在**。

本脚本做三件事：
  1. 扫 FF 15  -> 直接调用点 (caller, slot)
  2. 扫 FF 25  -> 桩地址 (thunk_va, slot)
  3. 对每个桩，扫全 .text 找 `E8 rel32` 落在桩上的直接调用点，
     得到 (caller, slot, via_thunk) 的完整调用关系。

用法: python scripts/_tmp_thunk.py
输出: scripts/_out/thunk.txt
"""
import sys, os, struct, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from importmap import build, IAT_RVA, IAT_SIZE

IMAGE_BASE = 0x10000000


def main():
    img = Image()
    slots = build(img)
    sec = [s for s in img.sections if s['name'] == '.text'][0]
    start, end = sec['raw'], sec['raw'] + sec['rawsize']
    tlo, thi = IMAGE_BASE + sec['va'], IMAGE_BASE + sec['va'] + sec['vsize']

    # --- 1/2. 扫 FF 15 / FF 25 ---
    direct = collections.defaultdict(list)   # slot_rva -> [call_va]
    thunks = collections.defaultdict(list)   # slot_rva -> [thunk_va]
    for op, table in ((b'\xff\x15', direct), (b'\xff\x25', thunks)):
        i = img.data.find(op, start, end)
        while i >= 0:
            tgt = struct.unpack_from('<I', img.data, i + 2)[0] - IMAGE_BASE
            if tgt in slots:
                table[tgt].append(img.voff(i))
            i = img.data.find(op, i + 1, end)

    # --- 3. 桩的调用者 ---
    via = collections.defaultdict(list)      # slot_rva -> [(caller_va, thunk_va)]
    thunk_of = {}                            # thunk_va -> slot_rva
    for slot, ts in thunks.items():
        for t in ts:
            thunk_of[t] = slot

    i = img.data.find(b'\xe8', start, end)
    while i >= 0:
        rel = struct.unpack_from('<i', img.data, i + 1)[0]
        caller = img.voff(i)
        tgt = caller + 5 + rel
        if tgt in thunk_of:
            via[thunk_of[tgt]].append((caller, tgt))
        i = img.data.find(b'\xe8', i + 1, end)

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'thunk.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    P('=== 桩表（jmp dword ptr [slot]）===')
    allt = sorted((t, s) for s, ts in thunks.items() for t in ts)
    for t, s in allt:
        P('  0x%08x  -> slot 0x%06x  %s' % (t, s, slots[s]))
    P()
    P('桩总数 %d   覆盖 %d 个槽' % (len(allt), len(thunks)))
    P()

    KEY = ('socket', 'connect', 'send', 'recv', 'bind', 'listen', 'accept',
           'select', 'closesocket', 'hton', 'ntoh', 'inet_', 'getaddrinfo',
           'getnameinfo', 'freeaddrinfo', 'setsockopt', 'getsockopt',
           'shutdown', 'WSA', 'gethost')
    P('=== 网络 API 完整调用点（direct + via thunk）===')
    for rva in sorted(set(direct) | set(via)):
        lab = slots[rva]
        if not any(k in lab for k in KEY):
            continue
        d = sorted(direct.get(rva, []))
        v = sorted(via.get(rva, []))
        P('  %-34s slot 0x%06x  direct %2d  via-thunk %2d'
          % (lab, rva, len(d), len(v)))
        if d:
            P('      direct : %s' % ', '.join('0x%06x' % p for p in d[:20]))
        if v:
            P('      thunk  : %s' % ', '.join('0x%06x(->0x%06x)' % p for p in v[:20]))
    P()
    out.close()
    print('-> scripts/_out/thunk.txt')


if __name__ == '__main__':
    main()
