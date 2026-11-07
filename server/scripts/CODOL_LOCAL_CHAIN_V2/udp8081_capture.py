# -*- coding: utf-8 -*-
"""监听 UDP 8081，记录客户端发来的每个原始包（hex + 长度 + 源），
并按可配置策略决定是否回应。

不改任何系统配置：只绑 0.0.0.0:8081，等客户端自己发过来。
"""
import argparse
import socket
import sys
import time

BIN = sys.argv[4] if len(sys.argv) > 4 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--secs", type=float, default=90.0)
    ap.add_argument("--out", default="udp8081.log")
    ap.add_argument("--reply", default="none", choices=("none", "echo", "oneresp"))
    a = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", a.port))
    s.settimeout(1.0)

    fh = open(a.out, "w", encoding="utf-8", buffering=1)
    print("listening UDP 0.0.0.0:%d  reply=%s  secs=%g" % (a.port, a.reply, a.secs))
    fh.write("# listening UDP :%d reply=%s\n" % (a.port, a.reply))

    t0 = time.time()
    n = 0
    while time.time() - t0 < a.secs:
        try:
            data, addr = s.recvfrom(65535)
        except socket.timeout:
            continue
        except Exception as e:
            print("recv err", e)
            continue
        n += 1
        line = "[%7.2fs] from %s:%d len=%d  %s" % (
            time.time() - t0, addr[0], addr[1], len(data), data.hex(" "))
        print(line)
        fh.write(line + "\n")
        if a.reply == "echo":
            s.sendto(data, addr)
            fh.write("        -> echoed %d B\n" % len(data))
        elif a.reply == "oneresp":
            # 回一个最小的 4 字节，试探它是否只要求"有回应"
            rsp = bytes([0x01, len(data) & 0xFF, 0x00, 0x00])
            s.sendto(rsp, addr)
            fh.write("        -> replied %s\n" % rsp.hex(" "))

    fh.write("# total %d packets\n" % n)
    fh.close()
    print("done, %d packets" % n)


if __name__ == "__main__":
    main()
