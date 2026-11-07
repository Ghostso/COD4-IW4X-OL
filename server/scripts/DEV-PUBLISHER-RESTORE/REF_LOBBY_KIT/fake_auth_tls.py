# -*- coding: utf-8 -*-
"""127.0.0.1:3074 上的 /auth/ 假服务 —— 用 Python 自己做 TLS。

端口/地址来源(三方已验证可用):
  Run-Session.ps1 把 hosts 写成
      127.0.0.1 formal-zone-auth.codol.qq.com
      127.0.0.2 formal-zone-lsg.codol.qq.com
  并把 dwauth.ini 写成
      formal-zone-lsg.codol.qq.com 3074
      formal-zone-auth.codol.qq.com 3074
      0x03EA
  即: 【auth(auth服务, TLS) 在 127.0.0.1:3074】, 【lsg(大厅明文) 在 127.0.0.2:3074】。
  以前我们用 8443/8446 —— 那两个端口客户端根本不会去连。

为什么不用 fake_auth_https.ps1(http.sys):
  实测 http.sys 关闭连接时【不发 TLS close-notify】(客户端会看到
  SSLEOFError: EOF occurred in violation of protocol)。这里用 Python 的 ssl
  自己收尾, close_notify 一定会发出去。

证书: _leaf2.cer(由受信任的本地 root CA 签发) + _rsa.txt(导出的 RSA 私钥参数)
     —— 两者由 make_local_ca.ps1 生成, leaf 的 SAN = localhost +
     formal-zone-auth.codol.qq.com + formal-zone-lsg.codol.qq.com
"""
import base64
import json
import os
import socket
import ssl
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGF = os.path.join(ROOT, "auth3074.log")
PORT = 3074
BIND = "127.0.0.1"

# ---- 契约常量 ----
# 票据公式来自三方 CodolLocalLobbyServer.cs:
#   ticket[0..3] = DE AD BD EF ; ticket[k] = (k*31 + 7) & 0xFF  (k = 4..127)
# (旧版我们写成 DE AD BD EF + 04 05 06..., 与三方不同)
TICKET = bytes([0xDE, 0xAD, 0xBD, 0xEF]) + bytes((k * 31 + 7) & 0xFF for k in range(4, 128))
TICKET_B64 = base64.b64encode(TICKET).decode()
TASK_MAP = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}

# ★ 2026-10-03 多客户端改造: 客户端真正用的会话密钥是 **ticket[97:121]**(实测, 见
#   HANDOFF §10.9) —— 所以让每个 /auth/ 请求拿到**不同的 24B**, 一举解决两件事:
#     1) 每个客户端的 KDF 派生密钥天然不同("共享一把密钥"在协议上本来就不成立);
#     2) 大厅服务端能靠"从 0x82 帧里读出的 ticket[97:121]"把连接与该客户端的密钥配对。
#   已记录到 auth_sessions.txt, 便于排障与核对。
AUTH_SESS = os.path.join(ROOT, "auth_sessions.txt")


def make_ticket(session_key24):
    """按三方公式造 128B 票据, 但把偏移 97..120 换成传入的 24B 会话密钥。"""
    t = bytearray(TICKET)
    t[97:121] = session_key24[:24].ljust(24, b"\x00")
    return bytes(t)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---- 把 RSA 参数拼成 PKCS#1 PEM ----
def _der_len(n):
    if n < 0x80:
        return bytes([n])
    e = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(e)]) + e


def _der_int(b):
    b = b.lstrip(b"\x00") or b"\x00"
    if b[0] & 0x80:
        b = b"\x00" + b
    return b"\x02" + _der_len(len(b)) + b


def _pem(tag, der):
    b = base64.b64encode(der).decode()
    return ("-----BEGIN %s-----\n" % tag
            + "\n".join(b[i:i + 64] for i in range(0, len(b), 64))
            + "\n-----END %s-----\n" % tag)


def build_pem_files():
    key = {}
    with open(os.path.join(ROOT, "_rsa.txt")) as f:
        for ln in f:
            if "=" in ln:
                k, _, v = ln.strip().partition("=")
                key[k] = base64.b64decode(v)
    body = _der_int(b"\x00") + b"".join(
        _der_int(key[n]) for n in
        ("Modulus", "Exponent", "D", "P", "Q", "DP", "DQ", "InverseQ"))
    key_pem = _pem("RSA PRIVATE KEY", b"\x30" + _der_len(len(body)) + body)
    leaf = open(os.path.join(ROOT, "_leaf2.cer"), "rb").read()
    chain = _pem("CERTIFICATE", leaf)
    ca = os.path.join(ROOT, "_ca.pem")
    if os.path.exists(ca):
        chain += open(ca, "r").read()
    kp = os.path.join(ROOT, "_leaf2.key")
    cp = os.path.join(ROOT, "_leaf2_chain.pem")
    open(kp, "wb").write(key_pem.encode())      # 二进制写, 强制 LF
    open(cp, "wb").write(chain.encode())
    return cp, kp


def make_context(certfile, keyfile):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except Exception:
        pass
    # 客户端只提供老的 RSA/DHE-CBC 套件(AES128-SHA/AES256-SHA 等)
    for cs in ("ALL:@SECLEVEL=0", "DEFAULT:@SECLEVEL=0"):
        try:
            ctx.set_ciphers(cs)
            break
        except Exception:
            continue
    ctx.load_cert_chain(certfile, keyfile)
    return ctx


def _get_str(body, key):
    """从请求 JSON 里粗取一个字段值(不依赖严格 JSON 解析)。"""
    i = body.find(('"%s"' % key).encode())
    if i < 0:
        return ""
    j = body.find(b":", i)
    if j < 0:
        return ""
    k = j + 1
    while k < len(body) and body[k:k + 1] in (b" ", b"\t"):
        k += 1
    if body[k:k + 1] == b'"':
        e = k + 1
        while e < len(body):
            if body[e] == 0x5C:
                e += 2
                continue
            if body[e] == 0x22:
                break
            e += 1
        return body[k + 1:e].decode("utf-8", "replace")
    e = k
    while e < len(body) and body[e:e + 1] not in (b",", b"}", b"\r", b"\n"):
        e += 1
    return body[k:e].decode("utf-8", "replace").strip()


def build_response(body):
    """★ 完全照抄三方 CodolLocalLobbyServer.cs 的 200 应答形态:
       - 顶层有 ret/code/auth_task/status/success
       - 票据字段同时放顶层与 data 内层, 且都以【字符串】给 _size
       - 额外带 DW-* 响应头(校验器会读)
       - iv_seed 回显请求里的值(三方就是回显)
       - 【不含 extra_data】(三方没有; 我们也拿不到那个 749B 模板)
    """
    task = _get_str(body, "auth_task")
    iv_seed = _get_str(body, "iv_seed") or "0"
    resp_task = TASK_MAP.get(int(task), 1) if task.isdigit() else 1

    # ★ 每次 /auth/ 发一张**会话密钥唯一**的票据(见 make_ticket 注释)
    sk = os.urandom(24)
    tk_b64 = base64.b64encode(make_ticket(sk)).decode()
    try:
        with open(AUTH_SESS, "a", encoding="utf-8") as f:
            f.write("%d %s\n" % (int(time.time()), sk.hex()))
    except Exception:
        pass
    log("  会话密钥(本次) = %s  (写入 %s)" % (sk.hex(), os.path.basename(AUTH_SESS)))

    fields = ('"member_position":"1","estimated_wait_time":"0","next_poll_after":"1",'
              '"iv_seed":"%s",'
              '"client_ticket":"%s","client_ticket_size":"128",'
              '"server_ticket":"%s","server_ticket_size":"128",'
              '"lsg_server_ticket":"%s","lsg_server_ticket_size":"128"'
              % (iv_seed, tk_b64, tk_b64, tk_b64))

    js = ('{"ret":0,"code":700,"auth_task":%d,"status":0,"success":true,%s,'
          '"data":{%s},"profile":{"id":1,"name":"Offline"}}'
          % (resp_task, fields, fields)).encode()

    head = ("HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "DW-Ticket-Seed: %s\r\n"
            "DW-Client-Ticket-Size: 128\r\n"
            "DW-Client-Ticket: %s\r\n"
            "DW-Server-Ticket-Size: 128\r\n"
            "DW-Server-Ticket: %s\r\n"
            "Connection: close\r\n"
            "X-Local-Emulator: unsigned-protocol-experiment\r\n\r\n"
            % (len(js), iv_seed, tk_b64, tk_b64)).encode()
    return head + js, task, resp_task


def handle(conn, addr):
    try:
        conn.settimeout(30)
        ss = CONTEXT.wrap_socket(conn, server_side=True)
    except Exception as e:
        log("TLS 握手失败 %s: %r" % (addr, e))
        try:
            conn.close()
        except Exception:
            pass
        return
    try:
        log("=== TLS 就绪 %s 版本=%s 套件=%s ===" % (addr, ss.version(), ss.cipher()[0]))
        data = b""
        while b"\r\n\r\n" not in data:
            c = ss.recv(4096)
            if not c:
                break
            data += c
        head, _, rest = data.partition(b"\r\n\r\n")
        clen = 0
        for ln in head.split(b"\r\n")[1:]:
            k, _, v = ln.partition(b":")
            if k.strip().lower() == b"content-length":
                try:
                    clen = int(v.strip())
                except Exception:
                    clen = 0
        body = rest
        # Expect: 100-continue -> 先回 100, 再收 body
        if b"100-continue" in head.lower() and len(body) < clen:
            ss.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        while len(body) < clen:
            c = ss.recv(4096)
            if not c:
                break
            body += c
        log("[%s] %s  Host=%s  blen=%d" % (head.split(b"\r\n")[0].decode("latin1", "replace"),
                                           addr, addr, len(body)))
        for ln in head.split(b"\r\n")[1:]:
            if ln:
                log("      " + ln.decode("latin1", "replace"))
        if body:
            log("      body: " + body.decode("utf-8", "replace"))
        resp, task, rtask = build_response(body)
        ss.sendall(resp)
        log("  -> 200 task=%s->%s (%d 字节)" % (task, rtask, len(resp)))
        # ★ 关键: 发 TLS close-notify (http.sys 不发, 这是契约的一部分)
        try:
            ss.settimeout(1.5)
            ss.unwrap()
            log("  TLS close-notify 已发")
        except Exception as e:
            log("  close-notify: %r" % (e,))
    except Exception as e:
        log("处理异常 %s: %r" % (addr, e))
    finally:
        try:
            ss.close()
        except Exception:
            pass


if __name__ == "__main__":
    certfile, keyfile = build_pem_files()
    CONTEXT = make_context(certfile, keyfile)
    log("==== fake_auth_tls 启动 %s:%d (cert=%s) ====" % (BIND, PORT, os.path.basename(certfile)))
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((BIND, PORT))
    srv.listen(16)
    log("[*] 监听 %s:%d" % (BIND, PORT))
    while True:
        try:
            c, ad = srv.accept()
        except Exception:
            continue
        threading.Thread(target=handle, args=(c, ad), daemon=True).start()
