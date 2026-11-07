"""`.text` 网络 / IPC API caller 扫描（只读）。

与 importmap.xrefs 的关键区别：xrefs 按原始字节找 FF 15，**不验证指令边界**；
本脚本用与 tvm0iat.sweep 相同的「线性解码 + 遇非法字节跳 1 再同步」，
只统计 capstone 真解出的 `call dword ptr [imm32]`。

归属：函数起点用启发式（E8 直接调用落点 + 典型 prologue）。
参数恢复：**只解码 [函数起点, 调用点) 这一段** —— 起点是真指令边界，
因此线性解码合法；不看调用点之前的任意 140 字节（那会跨函数 / 落进指令中部）。

用法:
    python scripts/netcallers.py
输出:
    scripts/_out/net_text.txt
"""
import sys, os, re, struct, collections, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import importmap
import x86callers as X
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE_BASE = 0x10000000
IAT_LO, IAT_HI = 0xb02000, 0xb07000

# ---- 第一任务要求的 17 个 API（按名字匹配，任何 DLL 槽）----
NET17 = [
    'socket', 'WSASocketA', 'WSASocketW',
    'connect', 'WSAConnect',
    'send', 'WSASend', 'sendto', 'WSASendTo',
    'recv', 'WSARecv', 'recvfrom', 'WSARecvFrom',
    'select', 'getaddrinfo', 'gethostbyname', 'WSAStartup',
]
# 扩充分类用
NET_EXTRA = [
    'bind', 'listen', 'accept', 'closesocket', 'shutdown',
    'inet_addr', 'inet_ntoa', 'inet_pton', 'WSAStringToAddressA',
    'WSAStringToAddressW', 'gethostbyaddr', 'getnameinfo', 'freeaddrinfo',
    'setsockopt', 'getsockopt', 'ioctlsocket', 'WSAIoctl', 'WSACleanup',
    'WSAGetLastError', 'WSASetLastError', 'htons', 'htonl', 'ntohs', 'ntohl',
    'WSAAsyncSelect', 'WSAEventSelect', 'WSACreateEvent', 'WSAWaitForMultipleEvents',
    'WSAGetOverlappedResult', 'WSAAddressToStringA', 'WSADuplicateSocketA',
]
IPC_APIS = [
    'OpenFileMappingA', 'OpenFileMappingW', 'CreateFileMappingA', 'CreateFileMappingW',
    'MapViewOfFile', 'UnmapViewOfFile', 'CreateEventA', 'CreateEventW',
    'OpenEventA', 'OpenEventW', 'SetEvent', 'CreateMutexA', 'CreateMutexW',
    'OpenMutexA', 'OpenMutexW', 'FindWindowA', 'FindWindowW',
    'PostMessageA', 'PostMessageW', 'SendMessageA', 'SendMessageW',
    'SendMessageTimeoutA', 'SendMessageTimeoutW', 'DeviceIoControl',
]

RE_DW = re.compile(r'^dword ptr \[(.*?)\], (0x[0-9a-f]+)$')
RE_W = re.compile(r'^word ptr \[(.*?)\], (0x[0-9a-f]+)$')
RE_B = re.compile(r'^byte ptr \[(.*?)\], (0x[0-9a-f]+)$')

# sockaddr 家族判定
AF = {2: 'AF_INET', 23: 'AF_INET6', 1: 'AF_UNIX', 6: 'AF_IPX', 0: 'AF_UNSPEC'}
SOCKTYPE = {1: 'SOCK_STREAM', 2: 'SOCK_DGRAM', 3: 'SOCK_RAW',
            4: 'SOCK_RDM', 5: 'SOCK_SEQPACKET'}
PROTO = {0: 'IPPROTO_IP(默认)', 6: 'IPPROTO_TCP', 17: 'IPPROTO_UDP',
         1: 'IPPROTO_ICMP', 58: 'IPPROTO_ICMPV6'}


def scan_calls(img, sec, slots, md, chunk=1 << 16):
    """线性解码整节，返回 (call[slot] 列表, 统计)。"""
    start = sec['raw']
    buf = img.data[start:start + sec['rawsize']]
    base = sec['va']
    n = len(buf)
    calls = []          # (call_rva, slot_rva, api)
    total_insn = 0
    covered = 0
    bad = 0
    t0 = time.time()
    pos = 0
    while pos < n:
        end = min(pos + chunk, n)
        blob = buf[pos:end]
        i = 0
        last_good = 0
        while i < len(blob):
            got = 0
            for (addr, size, mn, ops) in md.disasm_lite(blob[i:], base + pos + i):
                total_insn += 1
                covered += size
                got = (addr - (base + pos + i)) + size
                if mn == 'call' and ops.startswith('dword ptr [0x'):
                    v = int(ops[13:-1], 16)
                    if v >= IMAGE_BASE:
                        r = v - IMAGE_BASE
                        if r in slots:
                            calls.append((addr, r, slots[r]))
            if got == 0:
                i += 1
                bad += 1
            else:
                i += got
                last_good = i
        pos += last_good if last_good else chunk
    return calls, dict(total_insn=total_insn, covered=covered, bad=bad,
                       secs=time.time() - t0)


def func_body(img, fstart, call_va, limit=0x8000):
    """从函数真入口线性解码到调用点之前。返回指令列表（指令边界合法）。"""
    if call_va <= fstart or call_va - fstart > limit:
        return None
    out = []
    for ins in X.dis(img, fstart, call_va - fstart + 1):
        if ins.address >= call_va:
            break
        out.append(ins)
    return out


def tail_args(body, call_va, n_ins=16):
    """调用点附近 n_ins 条指令。"""
    if body is None:
        return []
    pre = [i for i in body if i.address < call_va]
    return pre[-n_ins:]


def extract(tail):
    """从尾部指令窗口抽取 push 立即数 / 内存立即数存 / 寄存器传送 / lea。"""
    pushes, stores, leas, calls = [], [], [], []
    for ins in tail:
        m, ops = ins.mnemonic, ins.op_str
        if m == 'push':
            pushes.append((ins.address, ops))
        elif m == 'lea':
            leas.append((ins.address, ops))
        elif m == 'call':
            calls.append((ins.address, ops))
        for rx, sz in ((RE_DW, 4), (RE_W, 2), (RE_B, 1)):
            mm = rx.match(ops)
            if mm:
                stores.append((ins.address, sz, mm.group(1), int(mm.group(2), 16)))
                break
    return dict(pushes=pushes, stores=stores, leas=leas, calls=calls)


def cstr_safe(img, rva, limit=96):
    try:
        return img.cstr(rva, limit)
    except Exception:
        return None


def looks_str(s):
    if not s or len(s) < 3:
        return False
    good = sum(1 for ch in s if 32 <= ord(ch) < 127)
    return good >= len(s) * 0.85


def main():
    img = Image()
    slots = importmap.build(img)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False

    sec = [s for s in img.sections if s['name'] == '.text'][0]
    calls, st = scan_calls(img, sec, slots, md)
    print('.text 解码指令 %d  覆盖 %.1f%%  重同步 %d  边界验证 call[slot] %d  (%.1fs)'
          % (st['total_insn'], 100.0 * st['covered'] / max(1, sec['rawsize']),
             st['bad'], len(calls), st['secs']))

    calls = sorted(set(calls))

    # ---- 函数归属 ----
    dct = X.direct_call_targets(img)
    starts = X.func_starts(img, dct)
    import bisect

    def owner(va):
        i = bisect.bisect_right(starts, va) - 1
        return starts[i] if i >= 0 else None

    def fend(s):
        i = bisect.bisect_right(starts, s)
        return starts[i] if i < len(starts) else s + 0x10000

    # 反向: api 短名 -> slot
    by_api = collections.defaultdict(list)
    for rva, lab in slots.items():
        by_api[lab.split('!', 1)[1].lstrip('?')].append(rva)

    def sites_for(api):
        out = []
        for sr in by_api.get(api, []):
            for c in calls:
                if c[1] == sr:
                    out.append(c)
        return out

    out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '_out', 'net_text.txt'), 'w', encoding='utf-8')

    def P(s=''):
        out.write(s + '\n')

    P('=' * 78)
    P('# .text 网络/IPC caller 扫描  (指令边界感知)')
    P('=' * 78)
    P('解码指令 %d  覆盖 %d/%d = %.1f%%  重同步字节 %d'
      % (st['total_insn'], st['covered'], sec['rawsize'],
         100.0 * st['covered'] / max(1, sec['rawsize']), st['bad']))
    P('边界已验证 call[slot] 总数: %d' % len(calls))
    P('')

    # ---------- 全局: 所有 WS2_32 / WSOCK32 调用点 ----------
    # 注意: c[2] 形如 'WS2_32.dll!socket' -> split('!')[0] = 'WS2_32.dll'（带后缀）。
    # 旧版拿它和 'WS2_32' 比，永远为假 => 表头假零。用整串比。
    ws = [c for c in calls if c[2].split('!')[0].lstrip('?') in ('WS2_32.dll', 'WSOCK32.dll')]
    P('## 所有 WS2_32/WSOCK32 调用点  %d 个' % len(ws))
    cnt = collections.Counter(c[2] for c in ws)
    for a, n in cnt.most_common():
        P('   %-44s %4d' % (a, n))
    P('')

    # ---------- 槽映射实证（不再靠参数猜哪个槽叫什么） ----------
    P('## WS2_32 / WSOCK32 槽映射实证 (0xb02a40..0xb02b70)')
    for rva in sorted(slots):
        if 0xb02a40 <= rva < 0xb02b70:
            P('   slot 0x%06x  %s' % (rva, slots[rva]))
    P('')

    # ---------- 第一任务: 17 API 明细 ----------
    P('=' * 78)
    P('## 第一任务: 17 个 API 的调用点 / caller / 参数来源')
    P('=' * 78)
    interesting = NET17 + ['bind', 'listen', 'accept', 'closesocket', 'shutdown',
                           'inet_addr', 'inet_pton', 'WSAStringToAddressA',
                           'getnameinfo', 'freeaddrinfo', 'setsockopt', 'getsockopt']
    for api in interesting:
        sl = by_api.get(api, [])
        if not sl:
            # 尝试宽松匹配（WSASocketA -> WSASocket）
            alt = [k for k in by_api if k.lower().startswith(api.lower())]
            if alt:
                P('%-24s  [槽中为: %s]' % (api, ', '.join(alt)))
            else:
                P('%-24s  [导入槽中不存在]' % api)
            continue
        all_sites = sites_for(api)
        P('-' * 78)
        P('%-22s slots=%s  调用点 %d'
          % (api, ','.join('0x%06x' % x for x in sl), len(all_sites)))
        for (cva, sr, lab) in all_sites:
            f = owner(cva)
            body = func_body(img, f, cva) if f is not None else None
            tail = tail_args(body, cva)
            ex = extract(tail)
            P('   call 0x%08x  slot 0x%06x  func 0x%08x [%s]  %s'
              % (cva, sr, f,
                 ('body %d insn' % len(body)) if body is not None else 'BODY过大/未知',
                 lab))
            if tail:
                for ins in tail:
                    P('        %08x  %-20s %s %s'
                      % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                # 解释
                note = []
                tailpushes = [p for p in ex['pushes']]
                for (a, o) in tailpushes:
                    if o.startswith('0x') and '[' not in o:
                        v = int(o, 16)
                        small = v if v < 0x10000 else None
                        if small is not None:
                            note.append('push imm 0x%x(=%d)' % (v, v))
                        elif 0x10000000 <= v < 0x14000000:
                            s = cstr_safe(img, v - IMAGE_BASE)
                            note.append('push &0x%08x "%s"' % (v, s) if looks_str(s)
                                        else 'push &0x%08x' % v)
                        else:
                            note.append('push imm 0x%x' % v)
                for (a, sz, mem, v) in ex['stores']:
                    note.append('store%d [%s]=0x%x' % (sz * 8, mem, v))
                if note:
                    P('        >> ' + ' | '.join(note))
            P('')

    # ---------- socket 参数分类 ----------
    P('=' * 78)
    P('## 第二任务: socket / WSASocket 的 (af, type, protocol) 分类')
    P('=' * 78)
    def imm_of(ops):
        """capstone 把 `push 0` / `push 1` 渲染成十进制 '0'/'1'，大的才给 '0x..'。
        旧版只认 '0x' 前缀 => 0/1 全被丢掉 => 表头 push序列=[]。
        这里统一用 int(o, 0) 认两种写法；含 '[' 或寄存器名的一律判 None。"""
        o = ops.strip()
        if '[' in o:
            return None
        try:
            return int(o, 0)
        except ValueError:
            return None

    for api in ['socket', 'WSASocketA', 'WSASocketW']:
        for (cva, sr, lab) in sites_for(api):
            f = owner(cva)
            body = func_body(img, f, cva) if f is not None else None
            tail = tail_args(body, cva, 24)
            # 参数压栈区 = 从调用点往前直到上一条 call
            argwin = []
            for ins in reversed(tail):
                if ins.mnemonic == 'call':
                    break
                argwin.append(ins)
            argwin.reverse()
            nargs = 6 if api.startswith('WSASocket') else 3
            last = [i for i in argwin if i.mnemonic == 'push'][-nargs:]
            vals = [imm_of(i.op_str) for i in last]
            shown = ['%s(=0x%x)' % (i.op_str, v) if v is not None else i.op_str
                     for i, v in zip(last, vals)]
            regs = [i.op_str for i, v in zip(last, vals) if v is None]
            if len(last) == nargs and not regs:
                # x86 参数从右往左压 => 最后一个 push 才是第 1 个参数 (af)
                args = vals[::-1]
                af, ty, pr = args[0], args[1], args[2]
                tag = '(af=%s, type=%s, proto=%s)' % (
                    AF.get(af, hex(af)), SOCKTYPE.get(ty, hex(ty)), PROTO.get(pr, hex(pr)))
            elif regs:
                tag = 'UNKNOWN (第 %d 个参数来自寄存器: %s)' % (
                    nargs - regs.index(regs[0]), ','.join(regs[:3]))
            else:
                tag = 'UNKNOWN (窗口内只找到 %d 个 push，需 %d)' % (len(last), nargs)
            P('   %s call 0x%08x func 0x%08x  push序列=%s  -> %s'
              % (api, cva, f, shown, tag))
    P('')

    # ---------- 函数画像: 含网络调用的函数 ----------
    P('=' * 78)
    P('## 第六/九任务: 函数画像（含任一网络 API 调用的函数）')
    P('=' * 78)
    netset = set(NET17) | set(NET_EXTRA)
    fnet = collections.defaultdict(list)
    for (cva, sr, lab) in calls:
        api = lab.split('!', 1)[1].lstrip('?')
        if api in netset:
            fnet[owner(cva)].append((cva, api))
    P('含网络调用的函数数: %d' % len(fnet))
    for f in sorted(fnet):
        profile = collections.Counter(a for _, a in fnet[f])
        others = collections.Counter()
        for (cva, sr, lab) in calls:
            if owner(cva) == f:
                # '?' 现在是**名字侧**前缀（'WS2_32.dll!?socket'），必须 lstrip，
                # 否则 line 352 的 `k not in netset` 会把 ?socket 当成"非网络"漏进来。
                others[lab.split('!', 1)[1].lstrip('?')] += 1
        nonnet = {k: v for k, v in others.items() if k not in netset}
        P('   func 0x%08x [0x%08x-0x%08x]  网络: %s'
          % (f, f, fend(f),
             ', '.join('%s x%d' % (k, v) for k, v in sorted(profile.items()))))
        if nonnet:
            P('        同时调用: %s'
              % ', '.join('%s x%d' % (k, v) for k, v in
                          sorted(nonnet.items(), key=lambda x: -x[1])[:14]))
    P('')

    # ---------- IPC ----------
    P('=' * 78)
    P('## 第八任务: .text IPC / 窗口消息 API 调用点')
    P('=' * 78)
    for api in IPC_APIS:
        sl = by_api.get(api, [])
        if not sl:
            continue
        s = sites_for(api)
        P('%-26s slots=%s  %d 个调用点: %s'
          % (api, ','.join('0x%06x' % x for x in sl), len(s),
             ', '.join('0x%08x' % c[0] for c in s[:24])))
    P('')

    out.close()
    print('-> scripts/_out/net_text.txt')


if __name__ == '__main__':
    main()
