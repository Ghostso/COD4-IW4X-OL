"""通用 PE 导入表转储器 —— 用来看**任意** DLL 依赖了哪些网络 API。

与 importmap.py 不同：那个专门解 codoMP_client_shipRetailBase.dll 的
非标准 .idata2；本脚本走标准 IMAGE_IMPORT_DESCRIPTOR 数组，适用于
Cross/Tenio/*.dll、TenRpcs.dll、GameRpcs.dll 这类未加固的常规 DLL。

用法：
    python scripts/imports_of.py <dll路径> [<dll路径> ...]
    python scripts/imports_of.py --net <dll路径>     # 只打印网络相关导入
"""
import struct
import sys

NET_KEY = ('socket', 'connect', 'send', 'recv', 'bind', 'listen', 'accept',
           'select', 'WSASocket', 'WSAConnect', 'WSASend', 'WSARecv', 'WSA',
           'hton', 'ntoh', 'inet_', 'getaddrinfo', 'getnameinfo', 'freeaddrinfo',
           'gethost', 'getserv', 'setsockopt', 'getsockopt', 'shutdown',
           'closesocket', 'ioctlsocket', 'DnsQuery', 'WinHttp', 'InternetOpen',
           'HttpSend', 'HttpOpen', 'Snmp', 'stun', 'Stun', 'STUN')


class PE:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.data = f.read()
        d = self.data
        self.pe = struct.unpack_from('<I', d, 0x3c)[0]
        assert d[self.pe:self.pe + 4] == b'PE\0\0', '不是 PE 文件'
        nsec, = struct.unpack_from('<H', d, self.pe + 6)
        optsz, = struct.unpack_from('<H', d, self.pe + 0x14)[0:1]
        self.opt = self.pe + 0x18
        self.magic, = struct.unpack_from('<H', d, self.opt)
        self.is64 = self.magic == 0x20b
        # 数据目录里 Import 的 RVA/size（32 位：目录表从 opt+0x60 起，第 1 项）
        # 64 位：从 opt+0x70 起，第 1 项
        dd = self.opt + (0x70 if self.is64 else 0x60)
        self.imp_rva, self.imp_size = struct.unpack_from('<II', d, dd + 8)
        # 节表
        self.secs = []
        sp = self.pe + 0x18 + optsz
        for i in range(nsec):
            o = sp + i * 40
            name = d[o:o + 8].rstrip(b'\0').decode('latin1')
            vsz, va, rsz, raw = struct.unpack_from('<IIII', d, o + 8)
            self.secs.append((name, va, vsz, raw, rsz))

    def off(self, rva):
        for name, va, vsz, raw, rsz in self.secs:
            if va <= rva < va + max(vsz, rsz):
                return raw + (rva - va)
        return None

    def cstr(self, rva, n=200):
        o = self.off(rva)
        if o is None:
            return None
        e = self.data.find(b'\0', o, o + n)
        if e < 0:
            return None
        try:
            return self.data[o:e].decode('latin1')
        except Exception:
            return None


def imports(path):
    p = PE(path)
    out = {}
    if not p.imp_rva:
        return out
    o = p.off(p.imp_rva)
    if o is None:
        return out
    i = 0
    while True:
        oft, ts, fwd, name_rva, ft = struct.unpack_from('<IIIII', p.data, o + i * 20)
        if not (oft or ts or fwd or name_rva or ft):
            break
        dll = p.cstr(name_rva) or '<bad>'
        names = []
        walk = oft or ft
        if walk:
            j = 0
            while True:
                so = p.off(walk + j * (8 if p.is64 else 4))
                if so is None:
                    break
                v, = struct.unpack_from('<Q' if p.is64 else '<I', p.data, so)
                if v == 0:
                    break
                if p.is64:
                    # 64 位高位为 1 表示序数
                    if v >> 63:
                        names.append('ORD#%d' % (v & 0xffff))
                    else:
                        names.append(p.cstr((v & 0x7fffffff) + 2) or '<bad>')
                else:
                    if v & 0x80000000:
                        names.append('ORD#%d' % (v & 0xffff))
                    else:
                        names.append(p.cstr(v + 2) or '<bad>')
                j += 1
        out[dll] = names
        i += 1
        if i > 200:
            break
    return out


def main():
    args = sys.argv[1:]
    net_only = '--net' in args
    if net_only:
        args.remove('--net')
    for path in args:
        try:
            imps = imports(path)
        except Exception as e:
            print('%-28s  !! %s' % (path.rsplit('\\', 1)[-1], e))
            continue
        nm = path.rsplit('\\', 1)[-1]
        total = sum(len(v) for v in imps.values())
        print('=== %s   (%d 个 DLL, %d 个导入)' % (nm, len(imps), total))
        for dll, names in imps.items():
            hit = [n for n in names if any(k in n for k in NET_KEY)]
            if net_only and not hit:
                continue
            if net_only:
                print('    %s: %s' % (dll, ', '.join(hit)))
            else:
                print('    %s (%d)  %s' % (dll, len(names),
                                           ', '.join(names[:14]) +
                                           (' ...' if len(names) > 14 else '')))
        print()


if __name__ == '__main__':
    main()
