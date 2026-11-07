"""诊断用 UDP 监听: 绑本机若干"客户端会去连但没有服务"的端口, 记下 payload。
目的: 判定客户端在"等待连接"期间往 mm/其它服务发了什么(尤其是 mmbook)。
用法: python -I udp_tap.py <outdir> [port ...]
"""
import socket
import sys
import os
import time

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
PORTS = [int(x) for x in sys.argv[2:]] or [10001, 10053, 10054, 10113, 8011, 8081]
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "udp_tap.log"), "a", encoding="utf-8", buffering=1)

socks = []
for p in PORTS:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", p))
        s.settimeout(1.0)
        socks.append((p, s))
        LOG.write("[tap] bound UDP 0.0.0.0:%d\n" % p)
    except Exception as e:
        LOG.write("[tap] bind %d failed: %r\n" % (p, e))

t0 = time.time()
while True:
    for p, s in socks:
        try:
            d, a = s.recvfrom(4096)
        except socket.timeout:
            continue
        except Exception:
            continue
        LOG.write("[t=%6.1fs] UDP:%d <- %s:%d  %dB  %s\n"
                  % (time.time() - t0, p, a[0], a[1], len(d), d[:200].hex(" ")))
        try:
            LOG.write("           ascii=%r\n" % d[:120])
        except Exception:
            pass
