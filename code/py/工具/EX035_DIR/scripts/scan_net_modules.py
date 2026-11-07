"""全目录扫描：哪些二进制**真的能建 socket**。

判据分层（避免把只导入 htonl/ntohl 的序列化模块误判为网络层）：

  CREATE  = WSASocketA/W、socket  —— 能创建套接字，最强证据
  IO      = connect/WSAConnect、send/WSASend/sendto/WSASendTo、
            recv/WSARecv/recvfrom/WSARecvFrom  —— 能收发包
  CTRL    = bind/listen/accept/select/WSAEventSelect/WSAPoll  —— 服务器侧或事件驱动
  ORDER   = htonl/htons/ntohl/ntohs  —— 只做字节序转换，**不算网络层**
  INIT    = WSAStartup/WSACleanup    —— 只是初始化

只导入 ORDER/INIT 的模块是**协议编解码器**，不是连接方。

用法：
    python scripts/scan_net_modules.py [根目录] [--min-io]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imports_of import PE, imports

CREATE = {'socket', 'WSASocketA', 'WSASocketW', 'WSASocketEx'}
IO_CONN = {'connect', 'WSAConnect', 'WSAConnectByList', 'WSAConnectByNameA',
           'WSAConnectByNameW'}
IO_SEND = {'send', 'WSASend', 'sendto', 'WSASendTo', 'WSASendMsg'}
IO_RECV = {'recv', 'WSARecv', 'recvfrom', 'WSARecvFrom', 'WSARecvMsg'}
IO = IO_CONN | IO_SEND | IO_RECV
CTRL = {'bind', 'listen', 'accept', 'select', 'WSAEventSelect', 'WSAPoll',
        'WSAAsyncSelect', 'getsockname', 'getpeername', 'setsockopt',
        'getsockopt', 'shutdown', 'closesocket', 'ioctlsocket', 'WSAIoctl'}
ORDER = {'htonl', 'htons', 'ntohl', 'ntohs', '__WSAFDIsSet',
         'WSANtohl', 'WSANtohs'}
INIT = {'WSAStartup', 'WSACleanup', 'WSAGetLastError', 'WSASetLastError'}
RESOLVE = {'getaddrinfo', 'GetAddrInfoW', 'getnameinfo', 'freeaddrinfo',
           'gethostbyname', 'gethostbyaddr', 'gethostname', 'getservbyname',
           'getservbyport', 'getprotobyname'}

# ws2_32 经典序数（只有名字缺失时才用得上）
ORD = {1: 'accept', 2: 'bind', 3: 'closesocket', 4: 'connect', 5: 'getpeername',
       6: 'getsockname', 7: 'getsockopt', 8: 'htonl', 9: 'htons',
       10: 'inet_addr', 11: 'inet_ntoa', 12: 'ioctlsocket', 13: 'listen',
       14: 'ntohl', 15: 'ntohs', 16: 'recv', 17: 'recvfrom', 18: 'select',
       19: 'send', 20: 'sendto', 21: 'setsockopt', 22: 'shutdown',
       23: 'socket', 52: 'gethostbyname', 57: 'gethostname',
       111: 'WSAGetLastError', 112: 'WSAIoctl', 115: 'WSAStartup',
       116: 'WSACleanup', 151: '__WSAFDIsSet'}

NET_DLLS = ('ws2_32', 'wsock32', 'ws2help', 'mswsock', 'iphlpapi',
            'winhttp', 'wininet', 'urlmon', 'dnsapi')


def classify(path):
    imps = imports(path)
    found = {'CREATE': set(), 'IO': set(), 'CTRL': set(), 'ORDER': set(),
             'INIT': set(), 'RESOLVE': set()}
    dlls = set()
    for dll, names in imps.items():
        low = dll.lower()
        for n in names:
            api = n
            if n.startswith('ORD#'):
                num = int(n[4:])
                api = ORD.get(num, n)
            if not any(k in low for k in NET_DLLS):
                # 非网络 DLL 也可能有同名导出，只在网络 DLL 里统计
                continue
            if api in CREATE:
                found['CREATE'].add(api)
            elif api in IO:
                found['IO'].add(api)
            elif api in CTRL:
                found['CTRL'].add(api)
            elif api in ORDER:
                found['ORDER'].add(api)
            elif api in INIT:
                found['INIT'].add(api)
            elif api in RESOLVE:
                found['RESOLVE'].add(api)
            if low.startswith(('ws2_32', 'wsock32', 'mswsock', 'winhttp',
                               'wininet', 'urlmon', 'dnsapi')):
                dlls.add(dll)
    return found, sorted(dlls), sum(len(v) for v in imps.values())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    root = args[0] if args else '.'
    min_io = '--min-io' in sys.argv

    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ('__pycache__', 'docs', 'scripts')]
        for fn in filenames:
            if not fn.lower().endswith(('.dll', '.exe')):
                continue
            p = os.path.join(dirpath, fn)
            try:
                f, dlls, nimps = classify(p)
            except Exception:
                continue
            score = (len(f['CREATE']), len(f['IO']), len(f['CTRL']))
            if not any(score):
                if min_io:
                    continue
                if not (f['ORDER'] or f['INIT'] or f['RESOLVE']):
                    continue
            rel = os.path.relpath(p, root)
            rows.append((score, rel, f, dlls, nimps))

    rows.sort(key=lambda r: r[0], reverse=True)
    print('%-46s %-5s %-5s %-5s %s' % ('二进制', 'CREA', 'IO', 'CTRL', '网络 DLL'))
    print('-' * 110)
    for score, rel, f, dlls, nimps in rows:
        print('%-46s %-5d %-5d %-5d %s' % (
            rel[:45], score[0], score[1], score[2], ','.join(dlls)[:40]))
        for k in ('CREATE', 'IO', 'CTRL', 'RESOLVE'):
            if f[k]:
                print('      %-8s %s' % (k, ', '.join(sorted(f[k]))))
        if f['ORDER'] and not (f['CREATE'] or f['IO']):
            print('      %-8s %s   <-- 仅字节序/序列化，不是连接方'
                  % ('ORDER', ', '.join(sorted(f['ORDER']))))
    print()
    print('共 %d 个二进制有网络相关导入' % len(rows))


if __name__ == '__main__':
    main()
