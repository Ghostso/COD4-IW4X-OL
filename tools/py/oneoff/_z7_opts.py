# -*- coding: utf-8 -*-
"""Test: does the client fail because of the TLS1.0 downgrade sentinel?"""
import socket, ssl, threading, time

RAW = open(r"CODOLServer\logs\z7fix\clihello_57389.bin","rb").read()

def build_ctx(opts=0, maxver=None):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                        r"CODOLServer\lobby_server\lobby_server.key")
    ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    ctx.maximum_version = maxver or ssl.TLSVersion.TLSv1_2
    if opts: ctx.options |= opts
    ctx.options |= ssl.OP_NO_TLSv1_3
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

for label, opts, mv in [
    ("baseline TLS1.0-1.2", 0, None),
    ("max=TLSv1.0 only", 0, ssl.TLSVersion.TLSv1),
    ("OP_NO_TICKET", getattr(ssl,"OP_NO_TICKET",0), None),
    ("OP_NO_COMPRESSION", ssl.OP_NO_COMPRESSION, None),
    ("OP_CIPHER_SERVER_PREF", ssl.OP_CIPHER_SERVER_PREFERENCE, None),
]:
    try:
        ctx = build_ctx(opts, mv)
    except Exception as e:
        print("  %-24s ctx err %s" % (label, e)); continue
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    srv.bind(("127.0.0.1",0)); srv.listen(1); port = srv.getsockname()[1]
    res = {}
    def w():
        try:
            c,a = srv.accept(); c.settimeout(5)
            s = ctx.wrap_socket(c, server_side=True)
            res["ok"] = s.cipher()
        except Exception as e:
            res["err"] = type(e).__name__
    threading.Thread(target=w, daemon=True).start()
    time.sleep(0.15)
    cli = socket.create_connection(("127.0.0.1",port), timeout=6)
    cli.sendall(RAW); time.sleep(1.2)
    try: cli.settimeout(0.4); d = cli.recv(4096)
    except Exception: d = b""
    cli.close(); srv.close()
    print("  %-24s srv=%s cli_recv=%d bytes" % (label, res.get("ok") or res.get("err"), len(d)))
    time.sleep(0.3)
