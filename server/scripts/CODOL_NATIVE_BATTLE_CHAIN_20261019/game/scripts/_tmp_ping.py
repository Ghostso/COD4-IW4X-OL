"""临时（只读）：全量转储 0x22exxx-0x236xxx 网络客户端簇，并找其调用者。

由来：_tmp_thunk.py 修正了 importmap 的桩漏检（FF 25 / jmp [slot]）。
修正后暴露出一整簇旧普查看不见的代码：
  inet_addr   0x22ea85, 0x22ec04        (旧普查 0 直接点)
  gethostbyname 0x2363fd                (旧普查 0 直接点)
  WSAStartup  0x22e7f3, 0x2321b2, 0x235d4a
  closesocket 0x23111c, 0x235dc8
  setsockopt  0x23a202, 0x23af07
  WSACleanup  0x231134, 0x232368, 0x235ddd
  WSAGetLastError 0x231fe6
  sendto 0x235ec9 / recvfrom 0x235f7e / WSAWaitForMultipleEvents 0x235f23,0x23602f
  WSAEnumNetworkEvents 0x235f4c

任务2「sin_addr UNKNOWN」的候选来源就在这一簇（inet_addr 是**唯一**把
点分十进制串转成 sin_addr 的 API；gethostbyname 是唯一的主机名解析）。

用法: python scripts/_tmp_ping.py
输出: scripts/_out/ping.txt
"""
import sys, os, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000

DIS = [
    (0x22e600, 0x22e900),
    (0x22e900, 0x22ed00),
    (0x2310c0, 0x231400),
    (0x232100, 0x232600),
    (0x235b00, 0x236500),
    (0x23a1a0, 0x23a300),
    (0x23aed0, 0x23b000),
    (0x23a000, 0x23a1a0),
]

# 需要找调用者的目标（这些函数的「谁在用它」决定它的角色）
CALL_TARGETS = [
    0x22e7f3, 0x22ea85, 0x22ec04,          # WSAStartup / inet_addr x2
    0x23111c, 0x23112e, 0x231134, 0x231fe6,
    0x2321b2, 0x232368,
    0x235cd0, 0x235dc0, 0x235d4a, 0x235ec9, 0x235f7e, 0x2363fd,
    0x23a202, 0x23af07,
]


def main():
    img = Image()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    sec = [s for s in img.sections if s['name'] == '.text'][0]
    start, end = sec['raw'], sec['raw'] + sec['rawsize']

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'ping.txt'), 'w', encoding='utf-8')
    def P(s=''):
        out.write(s + '\n')

    for (lo_rva, hi_rva) in DIS:
        P('--- disasm 0x%08x - 0x%08x' % (IMAGE_BASE + lo_rva, IMAGE_BASE + hi_rva))
        buf = img.read(lo_rva, hi_rva - lo_rva)
        if not buf:
            P('    <read failed>')
            continue
        i = 0
        while i < len(buf):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(buf[i:], IMAGE_BASE + lo_rva + i):
                got = (addr - (IMAGE_BASE + lo_rva + i)) + size
                P('  %08x  %-10s %s' % (addr, mn, ops))
            if got == 0:
                P('  %08x  <bad byte>' % (IMAGE_BASE + lo_rva + i))
                i += 1
            else:
                i += got
        P()

    # ---- 找调用者：E8 rel32 落在目标上，或 push imm32 == 目标（取地址/间接调用） ----
    P('=== 调用者 ===')
    for tgt in CALL_TARGETS:
        hits = []
        for (lo_rva, hi_rva) in DIS:
            lo = IMAGE_BASE + lo_rva
            buf = img.read(lo_rva, hi_rva - lo_rva)
            if not buf:
                continue
            i = 0
            while i < len(buf):
                got = 0
                for (addr, size, mn, ops) in md.disasm_lite(buf[i:], lo + i):
                    got = (addr - (lo + i)) + size
                    if (mn == 'call' or mn == 'jmp') and ops.startswith('0x%x' % tgt):
                        hits.append('%s@%08x' % (mn, addr))
                    elif m_imm(ops, tgt):
                        hits.append('imm@%08x' % addr)
                if got == 0:
                    i += 1
                else:
                    i += got
        P('  0x%08x  <- %s' % (tgt, ', '.join(hits) or '(本簇内无)'))

    # ---- 全 .text 找 `E8 rel32` 指向本簇**函数入口**的调用者（簇外调用者） ----
    P()
    P('=== 全 .text 中 call 本簇地址的调用点 ===')
    for tgt in CALL_TARGETS:
        hits = []
        i = img.data.find(b'\xe8', start, end)
        while i >= 0:
            rel = struct.unpack_from('<i', img.data, i + 1)[0]
            caller = img.voff(i)
            if caller + 5 + rel == tgt:
                hits.append('0x%06x' % caller)
            i = img.data.find(b'\xe8', i + 1, end)
        if hits:
            P('  0x%08x  <- %s' % (tgt, ', '.join(hits)))
    P()
    out.close()
    print('-> scripts/_out/ping.txt')


def m_imm(ops, tgt):
    import re
    for m in re.finditer(r'0x([0-9a-f]{6,8})\b', ops or ''):
        if int(m.group(1), 16) == tgt:
            return True
    return False


if __name__ == '__main__':
    main()
