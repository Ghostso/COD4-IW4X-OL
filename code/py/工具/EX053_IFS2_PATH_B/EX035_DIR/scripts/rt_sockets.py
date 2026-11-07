"""进程外 socket 枚举器 —— 第一/二/三/四阶段的**零注入**实现。

为什么不用 Frida：本客户端随包携带 ACE-DRV32 / TerSafe / TP3 / TGuard，
向受保护进程注入会被检测。本脚本只调用系统的
`GetExtendedTcpTable` / `GetExtendedUdpTable`（iphlpapi），
**不写目标进程内存、不装载 DLL、不改线程上下文**，
因此拿到的每一条都是「实际运行时参数」——满足「必须从实际运行时参数确认」。

代价（必须诚实记录为已知缺口）：
  * 轮询有采样间隔，短命连接可能整个错过；
  * **看不到调用栈**（第六阶段必须靠 Frida 或 ETW）；
  * **看不到 send/recv 的载荷与次数**（第七阶段必须靠 Frida 或 pktmon）。

用法：
    python scripts/rt_sockets.py --watch                 # 监视全部进程
    python scripts/rt_sockets.py --pid 1234 --watch
    python scripts/rt_sockets.py --name codoMP           # 按进程名模糊匹配
    python scripts/rt_sockets.py --pid 1234 --dump       # 打印当前快照后退出
    python scripts/rt_sockets.py --watch --interval 200
"""
import argparse
import ctypes
import ctypes.wintypes as w
import socket
import struct
import sys
import time

iphlp = ctypes.WinDLL('iphlpapi', use_last_error=True)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)

TCP_TABLE_OWNER_PID_ALL = 5
UDP_TABLE_OWNER_PID = 1
AF_INET = 2
AF_INET6 = 23
NO_ERROR = 0
ERROR_INSUFFICIENT_BUFFER = 122

TCP_STATE = {
    1: 'CLOSED', 2: 'LISTEN', 3: 'SYN_SENT', 4: 'SYN_RCVD', 5: 'ESTABLISHED',
    6: 'FIN_WAIT1', 7: 'FIN_WAIT2', 8: 'CLOSE_WAIT', 9: 'CLOSING',
    10: 'LAST_ACK', 11: 'TIME_WAIT', 12: 'DELETE_TCB',
}

for fn in (iphlp.GetExtendedTcpTable, iphlp.GetExtendedUdpTable):
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.DWORD), w.BOOL,
                   w.ULONG, ctypes.c_int, w.ULONG]
    fn.restype = w.DWORD

# ---- Toolhelp：pid -> 进程名 -------------------------------------------------
TH32CS_SNAPPROCESS = 0x2


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD),
                ('th32ProcessID', w.DWORD),
                ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                ('th32ModuleID', w.DWORD), ('cntThreads', w.DWORD),
                ('th32ParentProcessID', w.DWORD), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', w.DWORD), ('szExeFile', ctypes.c_char * 260)]


def proc_names():
    k32.CreateToolhelp32Snapshot.restype = w.HANDLE
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = {}
    if h == w.HANDLE(-1).value or not h:
        return out
    e = PROCESSENTRY32()
    e.dwSize = ctypes.sizeof(PROCESSENTRY32)
    ok = k32.Process32First(h, ctypes.byref(e))
    while ok:
        out[e.th32ProcessID] = e.szExeFile.decode('latin1', 'ignore')
        ok = k32.Process32Next(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


# ---- 表读取 -----------------------------------------------------------------
def _read_table(fn, af, cls):
    size = w.DWORD(0)
    r = fn(None, ctypes.byref(size), False, af, cls, 0)
    if r != ERROR_INSUFFICIENT_BUFFER or size.value == 0:
        return None, 0
    buf = ctypes.create_string_buffer(size.value)
    r = fn(buf, ctypes.byref(size), False, af, cls, 0)
    if r != NO_ERROR:
        return None, 0
    n = struct.unpack_from('<I', buf.raw, 0)[0]
    return buf.raw, n


def _p(port_word):
    return socket.ntohs(port_word & 0xFFFF)


def _v4(dw):
    return socket.inet_ntoa(struct.pack('<L', dw & 0xFFFFFFFF))


def _v6(b):
    try:
        return socket.inet_ntop(socket.AF_INET6, b)
    except Exception:
        return '?'


def tcp_rows():
    """-> {(proto,pid,lip,lport,rip,rport): state_str}"""
    out = {}
    raw, n = _read_table(iphlp.GetExtendedTcpTable, AF_INET, TCP_TABLE_OWNER_PID_ALL)
    if raw:
        for i in range(n):
            o = 4 + i * 24
            st, la, lp, ra, rp, pid = struct.unpack_from('<6I', raw, o)
            out[('TCP', pid, _v4(la), _p(lp), _v4(ra), _p(rp))] = TCP_STATE.get(st, '?%d' % st)
    raw, n = _read_table(iphlp.GetExtendedTcpTable, AF_INET6, TCP_TABLE_OWNER_PID_ALL)
    if raw:
        for i in range(n):
            o = 4 + i * 56
            la = raw[o:o + 16]
            lscope, lp = struct.unpack_from('<II', raw, o + 16)
            ra = raw[o + 24:o + 40]
            rscope, rp = struct.unpack_from('<II', raw, o + 40)
            st, pid = struct.unpack_from('<II', raw, o + 48)
            out[('TCP6', pid, _v6(la), _p(lp), _v6(ra), _p(rp))] = \
                TCP_STATE.get(st, '?%d' % st)
    return out


def udp_rows():
    out = {}
    raw, n = _read_table(iphlp.GetExtendedUdpTable, AF_INET, UDP_TABLE_OWNER_PID)
    if raw:
        for i in range(n):
            o = 4 + i * 12
            la, lp, pid = struct.unpack_from('<3I', raw, o)
            out[('UDP', pid, _v4(la), _p(lp), '0.0.0.0', 0)] = 'BOUND'
    raw, n = _read_table(iphlp.GetExtendedUdpTable, AF_INET6, UDP_TABLE_OWNER_PID)
    if raw:
        for i in range(n):
            o = 4 + i * 28
            la = raw[o:o + 16]
            lscope, lp, pid = struct.unpack_from('<III', raw, o + 16)
            out[('UDP6', pid, _v6(la), _p(lp), '::', 0)] = 'BOUND'
    return out


def snapshot():
    r = tcp_rows()
    r.update(udp_rows())
    return r


def fmt(key):
    proto, pid, lip, lport, rip, rport = key
    return '%s %d:%s -> %s:%s' % (proto, lport, lip, rport, rip)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, action='append', default=[])
    ap.add_argument('--name', action='append', default=[])
    ap.add_argument('--watch', action='store_true')
    ap.add_argument('--dump', action='store_true')
    ap.add_argument('--interval', type=int, default=400)
    a = ap.parse_args()

    want_pids = set(a.pid)

    def selected(pid):
        if want_pids:
            return pid in want_pids
        if a.name:
            return nm.get(pid, '').lower().find(a.name[0].lower()) >= 0
        return True

    global nm
    nm = proc_names()

    if a.name and not want_pids:
        hits = [p for p, n in nm.items()
                if all(x.lower() in n.lower() for x in a.name)]
        if not hits:
            print('[!] 没有进程名匹配 %r；当前进程名样本：%s'
                  % (a.name, ', '.join(sorted(set(nm.values()))[:25])))
            return 2
        want_pids.update(hits)
        print('[i] 匹配到 pid: %s' % ', '.join('%d(%s)' % (p, nm[p]) for p in hits))

    if not a.watch:
        snap = snapshot()
        rows = [(k, v) for k, v in snap.items() if selected(k[1])]
        rows.sort(key=lambda kv: (kv[0][1], kv[0][3]))
        print('%-6s %-18s %-46s %s' % ('PID', '进程', '套接字', '状态'))
        for k, st in rows:
            print('%-6d %-18s %-46s %s' % (k[1], nm.get(k[1], '?')[:17], fmt(k), st))
        print('共 %d 条（全部进程 %d 条）' % (len(rows), len(snap)))
        return 0

    print('[i] 轮询中，间隔 %d ms；只显示目标进程。Ctrl-C 退出。' % a.interval)
    prev = {}
    t0 = time.time()
    while True:
        try:
            fresh = proc_names()
            nm.update(fresh)
            snap = {k: v for k, v in snapshot().items() if selected(k[1])}
        except KeyboardInterrupt:
            return 0
        ts = time.time() - t0
        for k, st in snap.items():
            if k not in prev:
                # 新出现的连接：远端非 0 视为 connect 已发生，否则是建了 socket
                kind = 'CONNECT' if k[4] not in ('0.0.0.0', '::') else 'OPEN'
                print('[%8.3f] %-7s pid=%-6d %-17s %-44s %s'
                      % (ts, kind, k[1], nm.get(k[1], '?')[:16], fmt(k), st))
            elif prev[k] != st:
                print('[%8.3f] %-7s pid=%-6d %-17s %-44s %s -> %s'
                      % (ts, 'STATE', k[1], nm.get(k[1], '?')[:16], fmt(k), prev[k], st))
        for k, st in prev.items():
            if k not in snap:
                print('[%8.3f] %-7s pid=%-6d %-17s %-44s (原状态 %s)'
                      % (ts, 'CLOSE', k[1], nm.get(k[1], '?')[:16], fmt(k), st))
        prev = snap
        time.sleep(a.interval / 1000.0)


if __name__ == '__main__':
    sys.exit(main())
