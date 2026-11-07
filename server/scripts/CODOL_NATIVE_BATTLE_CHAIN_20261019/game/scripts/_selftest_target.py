"""rt_etw.py / rt_hook.py 的冒烟测试靶子。

不是逆向工具。目的是在**受控**条件下把 ws2_32 的全部基本动作走一遍，
好让采集侧把「事件 ID / Location 码 → 操作」的映射表确定下来：
    socket → bind → listen → accept → connect → send → recv → shutdown → closesocket
    以及 UDP 的 socket → sendto → recvfrom → closesocket
    以及一次域名解析（gethostbyname）

跑法：python -u scripts/_selftest_target.py
"""
import os
import socket
import threading
import time

PORT = 34567
UDP_PORT = 34568


def server(ready):
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(('127.0.0.1', PORT))
    ls.listen(4)
    ready.set()
    try:
        cs, peer = ls.accept()
        cs.recv(64)
        cs.send(b'PONG-FROM-SERVER')
        cs.close()
    except Exception as e:
        print('server err:', e)
    ls.close()


def main():
    print('target pid=%d' % os.getpid(), flush=True)

    # 1) 域名解析 → 验证 NameResolution 与 AFD 的解析事件
    try:
        print('resolved localhost ->', socket.gethostbyname('localhost'), flush=True)
    except Exception as e:
        print('resolve failed', e, flush=True)

    # 2) TCP 全流程：listen/accept/connect/send/recv/close
    ready = threading.Event()
    t = threading.Thread(target=server, args=(ready,), daemon=True)
    t.start()
    ready.wait(3)
    time.sleep(0.3)

    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.connect(('127.0.0.1', PORT))
    c.send(b'PING-FROM-CLIENT')
    got = c.recv(64)
    print('client got %r' % got, flush=True)
    c.shutdown(socket.SHUT_RDWR)
    c.close()

    # 3) 一次**失败**的 connect，验证 Status 非 0 的形态（WSAECONNREFUSED）
    f = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        f.connect(('127.0.0.1', 9))
    except Exception as e:
        print('connect err:', e, flush=True)
    f.close()

    # 4) UDP：sendto / recvfrom
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.bind(('127.0.0.1', UDP_PORT))
    u.sendto(b'UDP-PING', ('127.0.0.1', UDP_PORT))
    u.settimeout(2)
    try:
        data, frm = u.recvfrom(64)
        print('udp got %r from %s' % (data, frm), flush=True)
    except Exception as e:
        print('udp recv err:', e, flush=True)
    u.close()

    print('done, holding 6s', flush=True)
    time.sleep(6)


if __name__ == '__main__':
    main()
