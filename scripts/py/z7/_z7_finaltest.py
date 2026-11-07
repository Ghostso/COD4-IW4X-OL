import socket, ssl, threading, time
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(r"CODOLServer\lobby_server\lobby_server.pem",
                    r"CODOLServer\lobby_server\lobby_server.key")
ctx.set_ciphers("ALL:COMPLEMENTOFALL:@SECLEVEL=0")
ctx.minimum_version = ssl.TLSVersion.TLSv1
ctx.maximum_version = ssl.TLSVersion.TLSv1_2
ctx.options |= ssl.OP_NO_TLSv1_3
ctx.verify_mode = ssl.CERT_NONE
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1",0)); srv.listen(1); port = srv.getsockname()[1]
res={}
def w():
    try:
        c,a = srv.accept(); c.settimeout(5)
        s = ctx.wrap_socket(c, server_side=True)
        res["cipher"]=s.cipher(); res["ver"]=s.version()
    except Exception as e:
        res["err"]=repr(e)[:120]
threading.Thread(target=w,daemon=True).start()
time.sleep(0.2)
cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
cctx.check_hostname=False; cctx.verify_mode=ssl.CERT_NONE
cctx.minimum_version=ssl.TLSVersion.TLSv1
cctx.maximum_version=ssl.TLSVersion.TLSv1_2
cctx.options |= ssl.OP_NO_TLSv1_3
try:
    cctx.set_ciphers("AES256-SHA")
except Exception as e: print("cli set_ciphers:", e)
try:
    s = cctx.wrap_socket(socket.create_connection(("127.0.0.1",port),timeout=5), server_hostname="x")
    print("CLIENT OK:", s.cipher(), s.version()); s.close()
except Exception as e:
    print("CLIENT ERR:", e)
time.sleep(0.8); srv.close()
print("SERVER:", res)
