# -*- coding: utf-8 -*-
"""Try to actually NEGOTIATE 0x0035 server-side, then mirror with a Python client."""
import ssl, socket, threading, time

def try_serve(cipher_spec, label):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                        r"CODOLServer\lobby_server\lobby_server.key")
    try:
        ctx.set_ciphers(cipher_spec)
    except Exception as e:
        print("  %-22s set_ciphers ERR %s" % (label, e)); return
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    ctx.options |= ssl.OP_NO_TLSv1_3
    ctx.verify_mode = ssl.CERT_NONE

    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0)); srv.listen(1)
    port = srv.getsockname()[1]
    res = {}
    def w():
        try:
            c, a = srv.accept(); c.settimeout(4)
            s = ctx.wrap_socket(c, server_side=True)
            res["cipher"] = s.cipher()
        except Exception as e:
            res["err"] = type(e).__name__ + ":" + str(e)[:80]
    t = threading.Thread(target=w, daemon=True); t.start()
    time.sleep(0.2)
    try:
        cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        cctx.check_hostname = False; cctx.verify_mode = ssl.CERT_NONE
        cctx.minimum_version = ssl.TLSVersion.TLSv1
        cctx.maximum_version = ssl.TLSVersion.TLSv1_2
        cctx.options |= ssl.OP_NO_TLSv1_3
        try: cctx.set_ciphers(cipher_spec)
        except Exception: pass
        s = cctx.wrap_socket(socket.create_connection(("127.0.0.1", port), timeout=5),
                             server_hostname="formal-zone-auth.codol.qq.com")
        res["client_cipher"] = s.cipher()
        s.close()
    except Exception as e:
        res["client_err"] = type(e).__name__ + ":" + str(e)[:80]
    t.join(timeout=5); srv.close()
    print("  %-24s server=%s client=%s %s" % (label, res.get("cipher"), res.get("client_cipher"),
          res.get("err") or res.get("client_err") or ""))

print("=== negotiation trials (python client mirroring client suites) ===")
for spec, label in [("AES256-SHA","AES256-SHA"),
                    ("AES128-SHA","AES128-SHA"),
                    ("AES256-SHA:AES128-SHA","both AES"),
                    ("ALL:COMPLEMENTOFALL:@SECLEVEL=0","ALL seclevel0"),
                    ("RSA+AES:@SECLEVEL=0","RSA+AES"),
                    ("DEFAULT@SECLEVEL=0","DEFAULT")]:
    try_serve(spec, label)
