# -*- coding: utf-8 -*-
"""CODOL 目录级 PE 导入面普查（**只读**）。

对应「新指令」的 1-6 步：
  1) 枚举 CODOL 目录下所有 PE（不按扩展名过滤 —— flash.ocx 之类也要抓到）
  2) 找出所有 WS2_32 / WinSock / IOCP / socket 相关导入
  3) 找出所有含 connect/send/recv/socket 语义的模块
  4) 启动时实际加载的 DLL 面（由 TCLSCheck.lst / EXE 第6节名单 / Base.dll IAT 提供，
     本脚本只负责把 PE 侧那条腿测准）
  5) 交叉两张表
  6) 列出「启动即加载 + 有游戏网络 API」的候选模块

铁律（本脚本遵守）：
  * 地址一律 **RVA**。本脚本只做「文件偏移 <-> RVA」，不碰 ImageBase，
    唯一例外是**延迟导入目录**：其 Attributes 位决定字段是 RVA 还是 VA（VA 才减 ImageBase）。
  * **普通导入目录（dir 1）与延迟导入目录（dir 13）都要解析** —— 只扫 dir 1 会整片漏。
  * 序号导入（高位 1<<31）单独标注，不得 cstr。
  * 不修改任何文件；报告只写到本仓库 docs/ 下。
"""
import os
import struct
import sys
import collections

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'docs', 'dirscan-net-report.md')

# ---------------------------------------------------------------- 判据表
SOCK_DLLS = {
    'ws2_32.dll', 'wsock32.dll', 'mswsock.dll', 'ws2help.dll', 'wship6.dll', 'wshtcpip.dll',
    'ws2_32', 'wsock32', 'mswsock', 'ws2help',
    'wininet.dll', 'winhttp.dll', 'iphlpapi.dll', 'dnsapi.dll', 'urlmon.dll', 'wldap32.dll',
    'wininet', 'winhttp', 'iphlpapi', 'dnsapi', 'urlmon', 'wldap32',
}

NET_FUNCS = {
    # ws2_32 / wsock32 全家族（含重叠 I/O）
    'socket', 'WSASocketA', 'WSASocketW', 'bind', 'connect', 'listen', 'accept', 'WSAAccept',
    'send', 'sendto', 'WSASend', 'WSASendTo', 'recv', 'recvfrom', 'WSARecv', 'WSARecvFrom',
    'shutdown', 'closesocket', 'select', 'ioctlsocket', 'WSAIoctl', 'getsockopt', 'setsockopt',
    'getpeername', 'getsockname', 'gethostbyname', 'gethostbyaddr', 'gethostname',
    'getaddrinfo', 'GetAddrInfoW', 'GetAddrInfoExW', 'freeaddrinfo', 'FreeAddrInfoW',
    'WSAStartup', 'WSACleanup', 'WSAGetLastError', 'WSASetLastError', '__WSAFDIsSet',
    'WSAEventSelect', 'WSAWaitForMultipleEvents', 'WSAEnumNetworkEvents', 'WSACreateEvent',
    'WSACloseEvent', 'WSAResetEvent', 'WSASetEvent', 'WSAConnect', 'WSAConnectByList',
    'AcceptEx', 'ConnectEx', 'DisconnectEx', 'TransmitFile', 'GetAcceptExSockaddrs',
    'WSALookupServiceBeginW', 'WSAAddressToStringW', 'WSAStringToAddressW',
    'inet_addr', 'inet_ntoa', 'htonl', 'htons', 'ntohl', 'ntohs',
    'WSAPoll', 'WSADuplicateSocketW', 'WSAGetOverlappedResult',
    # 名字里带 WSA / sock 的兜底（下面另有子串规则）
}

# KERNEL32 / ntdll 侧：完成端口与线程
IOCP_FUNCS = {
    'CreateIoCompletionPort', 'GetQueuedCompletionStatus', 'GetQueuedCompletionStatusEx',
    'PostQueuedCompletionStatus', 'SetFileCompletionNotificationModes',
    'CreateThread', '_beginthreadex', '_beginthread', 'CreateRemoteThread',
    'GetOverlappedResult', 'WSAGetOverlappedResult', 'CancelIo', 'CancelIoEx',
}


def net_reason(name):
    """函数名 -> 归类理由（None 表示不算网络面）"""
    if name in IOCP_FUNCS:
        return 'IOCP/thread'
    if name in NET_FUNCS:
        return 'winsock'
    if name.startswith('WSA'):
        return 'winsock'
    if name in ('socket', 'connect', 'send', 'recv'):
        return 'winsock'
    return None


# ---------------------------------------------------------------- PE 读取
class PE(object):
    MAXDESC = 4096
    MAXTHUNK = 65536

    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        head = self.f.read(0x400)
        if len(head) < 0x40 or head[:2] != b'MZ':
            raise ValueError('no MZ')
        pe = struct.unpack_from('<I', head, 0x3c)[0]
        if pe + 0x18 > len(head):
            self.f.seek(0)
            head = self.f.read(pe + 0x400)
        if head[pe:pe + 4] != b'PE\0\0':
            raise ValueError('no PE')
        self.pe = pe
        nsec, = struct.unpack_from('<H', head, pe + 6)
        optsz, = struct.unpack_from('<H', head, pe + 0x14)
        opt = pe + 0x18
        magic, = struct.unpack_from('<H', head, opt)
        self.is64 = (magic == 0x20b)
        if magic not in (0x10b, 0x20b):
            raise ValueError('bad magic 0x%x' % magic)
        self.machine, = struct.unpack_from('<H', head, pe + 4)
        self.chars, = struct.unpack_from('<H', head, pe + 0x16)
        self.subsys, = struct.unpack_from('<H', head, opt + 0x44)
        if self.is64:
            self.imagebase, = struct.unpack_from('<Q', head, opt + 0x18)
            dd = opt + 0x70
        else:
            self.imagebase, = struct.unpack_from('<I', head, opt + 0x1c)
            dd = opt + 0x60
        self.namedir, = struct.unpack_from('<I', head, opt + (0x6c if self.is64 else 0x5c))
        self.dd = []
        for i in range(min(self.namedir, 16)):
            self.dd.append(struct.unpack_from('<II', head, dd + i * 8))
        # 节表
        sp = pe + 0x18 + optsz
        self.f.seek(sp)
        raw = self.f.read(nsec * 40)
        self.secs = []
        for i in range(nsec):
            o = i * 40
            nm = raw[o:o + 8].rstrip(b'\0').decode('latin1')
            vsz, va, rsz, roff = struct.unpack_from('<IIII', raw, o + 8)
            self.secs.append((nm, va, vsz, roff, rsz))

    def off(self, rva):
        for nm, va, vsz, roff, rsz in self.secs:
            if va <= rva < va + max(vsz, rsz):
                o = roff + (rva - va)
                return o if o < rsz + roff else None
        return None

    def rd(self, rva, n):
        o = self.off(rva)
        if o is None:
            return None
        self.f.seek(o)
        return self.f.read(n)

    def u32(self, rva):
        b = self.rd(rva, 4)
        return struct.unpack('<I', b)[0] if b and len(b) == 4 else None

    def cstr(self, rva, n=256):
        b = self.rd(rva, n)
        if b is None:
            return None
        z = b.find(b'\0')
        if z < 0:
            z = len(b)
        try:
            return b[:z].decode('latin1')
        except Exception:
            return None

    def import_descs(self, rva, size):
        """通用：走 IMAGE_IMPORT_DESCRIPTOR 数组（20 字节/项）"""
        out = []
        o = self.off(rva)
        if o is None:
            return out
        for i in range(self.MAXDESC):
            self.f.seek(o + i * 20)
            b = self.f.read(20)
            if len(b) < 20:
                break
            oft, ts, fc, name_rva, fthunk = struct.unpack('<IIIII', b)
            if oft == 0 and name_rva == 0 and fthunk == 0:
                break
            nm = self.cstr(name_rva) if name_rva else None
            ilt = oft or fthunk
            funcs = self.thunk_names(ilt)
            out.append((nm, funcs))
        return out

    def delay_descs(self, rva, size):
        """IMAGE_DELAYLOAD_DESCRIPTOR，32 字节/项"""
        out = []
        o = self.off(rva)
        if o is None:
            return out
        for i in range(self.MAXDESC):
            self.f.seek(o + i * 32)
            b = self.f.read(32)
            if len(b) < 32:
                break
            attrs, name, hmod, iat, int_, biat, uiat, ts = struct.unpack('<IIIIIIII', b)
            if attrs == 0 and name == 0 and iat == 0:
                break
            if attrs & 1:          # 字段是 RVA
                nr, ir = name, int_
            else:                  # 字段是 VA
                nr = name - self.imagebase if name else 0
                ir = int_ - self.imagebase if int_ else 0
            nm = self.cstr(nr) if nr else None
            out.append((nm, self.thunk_names(ir)))
        return out

    def thunk_names(self, ilt_rva):
        """ILT 条目 -> 名字或 ORD#n。PE32 条目 4 字节，PE32+ 8 字节。"""
        funcs = []
        if not ilt_rva:
            return funcs
        w = 8 if self.is64 else 4
        hi = 1 << (63 if self.is64 else 31)
        for i in range(self.MAXTHUNK):
            b = self.rd(ilt_rva + i * w, w)
            if not b or len(b) < w:
                break
            v = struct.unpack('<Q' if self.is64 else '<I', b)[0]
            if v == 0:
                break
            if v & hi:
                funcs.append('ORD#%d' % (v & 0xffff))
            else:
                s = self.cstr(v + 2, 128)
                funcs.append(s if s else '?')
        return funcs

    def close(self):
        try:
            self.f.close()
        except Exception:
            pass


# ---------------------------------------------------------------- 主扫描
def main():
    targets = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # 跳过脚本自己的 docs/scripts 无关目录不算 PE，但保留
        for fn in filenames:
            targets.append(os.path.join(dirpath, fn))
    targets.sort()

    mods = []
    nope = 0
    for p in targets:
        try:
            pe = PE(p)
        except Exception:
            nope += 1
            continue
        try:
            imps = pe.import_descs(*pe.dd[1]) if pe.dd[1][0] else []
            try:
                dly = pe.delay_descs(*pe.dd[13]) if len(pe.dd) > 13 and pe.dd[13][0] else []
            except Exception:
                dly = []
            mods.append({
                'rel': os.path.relpath(p, ROOT),
                'name': os.path.basename(p),
                'is64': pe.is64,
                'machine': pe.machine,
                'subsys': pe.subsys,
                'base': pe.imagebase,
                'secs': len(pe.secs),
                'imps': imps,
                'dly': dly,
                'dir13': pe.dd[13] if len(pe.dd) > 13 else (0, 0),
            })
        except Exception as e:
            mods.append({'rel': os.path.relpath(p, ROOT), 'name': os.path.basename(p),
                         'err': repr(e)})
        finally:
            pe.close()

    ok = [m for m in mods if 'err' not in m]
    print('# 枚举文件 %d，PE 解析成功 %d，非 PE %d，解析失败 %d'
          % (len(targets), len(ok), nope, len(mods) - len(ok)))
    for m in mods:
        if 'err' in m:
            print('  !! %s : %s' % (m['rel'], m['err']))

    # ---------- A) 直接导入 socket DLL 的模块 ----------
    A = []
    # ---------- B) 任何导入里含网络函数名的模块（含代理 DLL 转发） ----------
    B = []
    # ---------- C) IOCP / 线程面 ----------
    C = []
    # ---------- D) 延迟导入里有网络面的 ----------
    D = []

    for m in ok:
        sockdll = {}
        netfn = collections.defaultdict(list)
        for dllname, funcs in m['imps']:
            dl = (dllname or '').lower()
            if dl in SOCK_DLLS:
                sockdll[dl] = funcs
            for f in funcs:
                r = net_reason(f)
                if r:
                    netfn[r].append('%s!%s' % (dllname or '?', f))
        if sockdll:
            A.append((m, sockdll))
        if netfn:
            B.append((m, netfn))
        if any(k in netfn for k in ('IOCP/thread',)):
            C.append((m, netfn['IOCP/thread']))
        dsock = {}
        dnet = []
        for dllname, funcs in m['dly']:
            dl = (dllname or '').lower()
            if dl in SOCK_DLLS:
                dsock[dl] = funcs
            for f in funcs:
                if net_reason(f):
                    dnet.append('%s!%s' % (dllname or '?', f))
        if dsock or dnet:
            D.append((m, dsock, dnet))
        m['_sockdll'] = sockdll
        m['_netfn'] = netfn

    def show(title, lines):
        print('\n' + '=' * 78)
        print(title)
        print('=' * 78)
        for l in lines:
            print(l)

    show('【A】直接导入 WinSock 家族 DLL 的模块 —— %d 个' % len(A), [])
    for m, sd in sorted(A, key=lambda x: x[0]['rel']):
        for dl in sorted(sd):
            fx = sd[dl]
            print('\n%s  [%s]' % (m['rel'], dl))
            print('    n=%d : %s' % (len(fx), ' '.join(sorted(set(fx)))))

    show('【C】含 IOCP / 重叠 I/O / 线程创建 的模块 —— %d 个' % len(C), [])
    for m, fx in sorted(C, key=lambda x: x[0]['rel']):
        uniq = sorted(set(fx))
        iocp = [f for f in uniq if not f.endswith(('CreateThread', '_beginthreadex',
                                                   '_beginthread', 'CreateRemoteThread'))]
        mark = '★IOCP' if iocp else '  thread'
        print('%s %-58s n=%d %s' % (mark, m['rel'], len(uniq), ' '.join(uniq)[:150]))

    show('【D】延迟导入目录里有网络面的模块 —— %d 个' % len(D), [])
    for m, sd, dn in sorted(D, key=lambda x: x[0]['rel']):
        print('%s' % m['rel'])
        for dl in sorted(sd):
            print('    DELAY %s n=%d : %s' % (dl, len(sd[dl]), ' '.join(sorted(set(sd[dl])))))
        for e in sorted(set(dn)):
            print('    DELAYfn %s' % e)

    # ---------- 汇总：谁最像「真正的 socket 用户」 ----------
    show('【B】按网络面丰富度排序（所有含网络函数名的模块）', [])
    rank = []
    for m in ok:
        nf = m.get('_netfn') or {}
        if not nf:
            continue
        flat = set()
        for k, v in nf.items():
            flat.update(v)
        # 评分：socket 创建点权重最高
        score = 0
        names = set()
        for e in flat:
            fn = e.split('!', 1)[1]
            names.add(fn)
        for k, w in (('socket', 100), ('WSASocketA', 100), ('WSASocketW', 100),
                     ('connect', 40), ('WSAConnect', 40), ('bind', 30), ('listen', 30),
                     ('accept', 30), ('WSAAccept', 30), ('send', 10), ('recv', 10),
                     ('sendto', 10), ('recvfrom', 10), ('WSARecv', 25), ('WSASend', 25),
                     ('select', 15), ('ioctlsocket', 15), ('WSAIoctl', 15),
                     ('CreateIoCompletionPort', 60), ('GetQueuedCompletionStatus', 60)):
            if k in names:
                score += w
        rank.append((score, m, sorted(names)))
    rank.sort(key=lambda x: (-x[0], x[1]['rel']))
    for score, m, names in rank[:80]:
        print('%4d  %-56s  %s' % (score, m['rel'], ' '.join(names)[:170]))

    # ---------- 落盘 ----------
    import io
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    print('# CODOL 目录级 PE 网络导入面普查（只读）\n')
    print('根目录：`%s`\n' % ROOT)
    print('枚举 %d 个文件，PE 解析成功 %d，非 PE %d\n' % (len(targets), len(ok), nope))
    sys.stdout = old
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())
    print('\n[报告已写] %s' % OUT)


if __name__ == '__main__':
    main()
