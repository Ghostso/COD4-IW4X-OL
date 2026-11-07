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
QUEUE_COUNT = [0]  # global counter for queue replies

# ---- 契约常量 ----
# 票据公式来自三方 CodolLocalLobbyServer.cs:
#   ticket[0..3] = DE AD BD EF ; ticket[k] = (k*31 + 7) & 0xFF  (k = 4..127)
# (旧版我们写成 DE AD BD EF + 04 05 06..., 与三方不同)
TICKET = bytes([0xDE, 0xAD, 0xBD, 0xEF]) + bytes((k * 31 + 7) & 0xFF for k in range(4, 128))
TICKET_B64 = base64.b64encode(TICKET).decode()

# ------------------------------------------------------------------ extra_data
# ★ 2026-10-05(本轮): 这段是【必需】的, 之前被"三方没有"这个理由省掉了,
#   结果客户端拿不到身份 → 71/4 的三个字段全零 → 报 Address Fail。
#   契约来自 lobby_server\mklobby_response.py(反汇编 0xB88FC0 / 0xB89610):
#     objA(vtable 0xD59A7C, stage 32 = 真实大厅路径) -> 0xB88FC0
#       "username"                        string  -> [objA+0x35B4] (UI 名)
#       "encrypted_codoid"                base64 -> **正好 16 字节**(0xB891CB cmp edi,0x10)
#       "encrypted_register_codoid_data"  base64 -> <= 1024 字节
#       0xB8902E je 0xB891F8 → extra_data 缺失直接 return FALSE(735)
#     objB(vtable 0xD5A1F8, 回退路径) -> 0xB99610
#       "extended_data" / "cd_key" / "time_to_live"
#   一份合并载荷同时满足两个解析器。
CODOID_BYTES = b"CODOL-LOCAL-0001"                # 正好 16 字节
REGISTER_BYTES = bytes(range(0x20, 0x60)) * 2     # 128 字节
CD_KEY_BYTES = bytes(range(0x00, 0x40))           # 64 字节


def extra_data_json():
    """返回(内层 JSON 文本, 已 JSON 转义的 token)。"""
    inner = {
        "username": "CODOL_LOCAL",
        "encrypted_codoid": base64.b64encode(CODOID_BYTES).decode("ascii"),
        "encrypted_register_codoid_data": base64.b64encode(
            REGISTER_BYTES).decode("ascii"),
        "extended_data": '{"version":"0","extended_data":true}',
        "cd_key": base64.b64encode(CD_KEY_BYTES).decode("ascii"),
        "time_to_live": 3600,
    }
    text = json.dumps(inner, separators=(",", ":"), sort_keys=True)
    return text, json.dumps(text)


# ---------------------------------------------------------------- 749 字节模板
# F:\桌面\ol\大厅（当时真正进过大堂的那套）里，对 task 10 的应答是 **2239 字节**，
# 而我们现在这套只有 1340。归档里的 lobby_response.json（749 字节）就是那次的
# 应答模板，占位符 $AUTH_TASK / $IV_SEED / $EXTRA_DATA 由 lobby_server\
# mklobby_response.py 的 build() 填充。这里按同样的构造复现，走开关
# auth_template749.on，便于 A/B。
NULL_REF_BYTES = bytes([0xDE, 0xAD, 0xBD, 0xEF])
TICKET_LEN = 128


def _null_ref_ticket(mul, add):
    body = bytes((i * mul + add) & 0xFF for i in range(TICKET_LEN - 4))
    return NULL_REF_BYTES + body


def build_response_749(task, iv_seed):
    """按 mklobby_response.build() 的形状产出应答体(扁平 + extra_data)。"""
    ct_b64 = base64.b64encode(_null_ref_ticket(5, 17)).decode("ascii")
    st_b64 = base64.b64encode(_null_ref_ticket(11, 29)).decode("ascii")
    _text, ext_tok = extra_data_json()
    body = (
        '{"auth_task":%s,"code":700,"iv_seed":%s,'
        '"client_ticket":"%s","server_ticket":"%s",'
        '"next_poll_after":0,"estimated_wait_time":0,"member_position":0,'
        '"lsg_server_ticket_size":%d,"lsg_server_ticket":"%s",'
        '"extra_data":%s}'
        % (task, iv_seed, ct_b64, st_b64, TICKET_LEN, st_b64, ext_tok))
    return body.encode()


def _build_response_template749(body_bytes, iv_seed):
    task = _get_str(body_bytes, "auth_task")
    resp_task = TASK_MAP.get(int(task), 1) if task.isdigit() else 1
    js = build_response_749(resp_task, iv_seed)
    head = ("HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "DW-Ticket-Seed: %s\r\n"
            "DW-Client-Ticket-Size: 128\r\n"
            "DW-Server-Ticket-Size: 128\r\n"
            "Connection: close\r\n\r\n"
            % (len(js), iv_seed)).encode()
    return head + js, task, resp_task


# ★ 2026-10-05: 实测"带 extra_data"会让客户端 exit=0 且不再连大厅探针
#   ——文档(0xB88FC0/0xB99610)写明 objB 是"present-and-wrong is fatal",
#   比缺失更糟。所以默认**不发**, 只在本文件同目录存在 auth_extra_data.on
#   时启用, 便于 A/B。
_EXTRA_DATA_FLAG = os.path.join(ROOT, "auth_extra_data.on")
TASK_MAP = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}


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
    iv_seed_req = _get_str(body, "iv_seed") or "0"
    # ★ 2026-10-05: 握手手册里长期未验证的一条 —— 客户端 0xB984E7 处
    #   `cmp [ebp-0xE4], 0`：response.iv_seed **必须为 0**，而之前一直把请求值
    #   回显。用开关 auth_iv0.on 切换，便于 A/B。
    iv_seed = "0" if os.path.exists(os.path.join(ROOT, "auth_iv0.on")) \
        else iv_seed_req
    if os.path.exists(os.path.join(ROOT, "auth_template749.on")):
        return _build_response_template749(body, iv_seed)
    resp_task = TASK_MAP.get(int(task), 1) if task.isdigit() else 1

    # ★ 2026-10-05: 形状以 F:\桌面\ol\大厅（当时真正进过大堂的那套）为准 ——
    #   顶层 ret/code/auth_task/status/success + data 内层 + profile，
    #   _size 以字符串给，**不含 extra_data**。那份 logs\auth3074.log 里
    #   客户端被接受的请求是 auth_task=10 / title_id=1002，应答就是这个形状。
    #   （mklobby_response.py 的扁平+int 模板是另一份产物，实测会把客户端挡在门外。）
    _ext_text, ext_tok = extra_data_json()
    use_ext = os.path.exists(_EXTRA_DATA_FLAG)
    ext_field = ',"extra_data":%s' % ext_tok if use_ext else ""
    fields = ('"member_position":"1","estimated_wait_time":"0","next_poll_after":"1",'
              '"iv_seed":"%s",'
              '"client_ticket":"%s","client_ticket_size":"128",'
              '"server_ticket":"%s","server_ticket_size":"128",'
              '"lsg_server_ticket":"%s","lsg_server_ticket_size":"128"'
              % (iv_seed, TICKET_B64, TICKET_B64, TICKET_B64) + ext_field)
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
            # ★ 2026-10-05: 不能发 Connection: close —— lobby_probe_server.py
            #   的实测注释写明: 客户端 HTTP 状态机(0xB9A370)会把带 close 的 200
            #   当成"仍在飞行中"(state 1/3 而非 5), 事务永不完成 → 账号阶段报错。
            #   改成 HTTP/1.1 默认的 keep-alive, 并把 socket 多留一会儿。
            "Connection: keep-alive\r\n"
            "X-Local-Emulator: unsigned-protocol-experiment\r\n\r\n"
            % (len(js), iv_seed, TICKET_B64, TICKET_B64)).encode()
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
        # Queue endpoint: /v1.0/title/<id>/queue/<q>/member/<m>
        # The client only reads iv_seed, lsg_server_ticket_size,
        # lsg_server_ticket (and auth_task + code).  Keep the body compact.
        if b"/queue/" in head:
            log("  -> queue request detected")
            QUEUE_COUNT[0] += 1
            n = QUEUE_COUNT[0]
            log("  -> queue request #%d" % n)
            if n < 3:
                # Queued: retry after 1 second.
                qjs = ('{"auth_task":57,"code":700,"iv_seed":1,'
                       '"lsg_server_ticket_size":0,'
                       '"next_poll_after":1,'
                       '"estimated_wait_time":1,'
                       '"member_position":%d}' % n).encode()
            else:
                # Accepted: provide the lsg_server_ticket.
                qjs = ('{"auth_task":57,"code":700,"iv_seed":1,'
                       '"lsg_server_ticket_size":128,'
                       '"next_poll_after":0,'
                       '"estimated_wait_time":0,'
                       '"member_position":0,'
                       '"lsg_server_ticket":"%s"}' % TICKET_B64).encode()
            qresp = ("HTTP/1.1 200 OK\r\n"
                     "Content-Type: application/json; charset=utf-8\r\n"
                     "Content-Length: %d\r\n"
                     "Connection: close\r\n\r\n" % len(qjs)).encode() + qjs
            ss.sendall(qresp)
            log("  -> 200 queue reply (%d 字节)" % len(qresp))
        else:
            resp, task, rtask = build_response(body)
            ss.sendall(resp)
            log("  -> 200 task=%s->%s (%d 字节)"
                % (task, rtask, len(resp)))
            # ★ 2026-10-05: 按 lobby_probe_server.py 的做法把 socket **保持
            #   可读 8 秒**。实测客户端每轮 obj_busy=1 / sub_state=6 一直不结算
            #   (HTTP 事务没收尾), 而 9-27 那个成功的服务端正是在应答后
            #   conn.settimeout(8.0) 继续等客户端自己收尾。
            import time as _t
            # auth_halfclose.on: 应答后**立刻半关闭写方向**(SHUT_WR),
            # 不发 TLS close-notify —— 让客户端凭 TCP FIN 判定应答结束。
            # 这是与"静默挂住"并列的另一个收尾候选(A/B)。
            if os.path.exists(os.path.join(ROOT, "auth_halfclose.on")):
                try:
                    ss.shutdown(socket.SHUT_WR)
                except Exception as e:
                    log("  halfclose: %r" % (e,))
                try:
                    ss.settimeout(8.0)
                    while True:
                        if not ss.recv(4096):
                            break
                except Exception:
                    pass
                log("  halfclose 模式: 已 SHUT_WR")
                return
            # auth_hold.on: 完全照 9-27 那台成功服务端的收尾 —— 不发
            # close-notify, 把 socket 一直挂到客户端自己关闭。
            if os.path.exists(os.path.join(ROOT, "auth_hold.on")):
                try:
                    ss.settimeout(40.0)
                    while True:
                        if not ss.recv(4096):
                            break
                except Exception:
                    pass
                log("  hold 模式: 客户端已关闭(未发 close-notify)")
                return
            _deadline = _t.time() + 8.0
            try:
                while _t.time() < _deadline:
                    ss.settimeout(max(0.2, _deadline - _t.time()))
                    chunk = ss.recv(4096)
                    if not chunk:
                        break
                    # ★ 2026-10-05: 应答之后客户端若在同一连接上发下一跳,
                    #   以前是被静默丢弃的。这里必须看见它。
                    log("  ★ 应答后收到 %d 字节: %s"
                        % (len(chunk), chunk[:64].hex(' ')))
            except Exception:
                pass
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
    # Use pre-existing PEM files when present so we can supply a SHA-1 chain.
    kp = os.path.join(ROOT, "_leaf2.key")
    cp = os.path.join(ROOT, "_leaf2_chain.pem")
    if os.path.exists(kp) and os.path.exists(cp):
        certfile, keyfile = cp, kp
    else:
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
