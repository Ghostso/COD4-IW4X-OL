"""Frida 重定向验证用的小客户端。

它先等 5 秒（给 Frida attach 留时间），然后向真实目录服务器 IP/端口发
一个真实的 33 字节 DIRTREERQ，最后打印收到的字节数。

这不是游戏组件，只是用于验证 CODOLServer/frida_tcls_dir_redirect.js 的
connect 重定向逻辑。
"""
import os
import socket
import struct
import sys
import time

REQ = bytes.fromhex(
    '0a09641a000000072a9e542600001771'
    '0000000100000000000000000002300000'
)


def main():
    print('pid=%d' % os.getpid(), flush=True)
    print('sleeping 5s before connect...', flush=True)
    time.sleep(5)
    print('connecting to 116.130.229.168:10009 ...', flush=True)
    s = socket.create_connection(('116.130.229.168', 10009), 8)
    s.sendall(REQ)
    s.settimeout(5)
    buf = b''
    while True:
        try:
            chunk = s.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    s.close()
    print('received=%d' % len(buf), flush=True)
    if len(buf) >= 26:
        print('head=%s' % buf[:26].hex(' '), flush=True)
        print('body_len=%d' % struct.unpack_from('>I', buf, 4)[0], flush=True)
        print('dir_root_at=%d' % buf.find(b'dir_root'), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
