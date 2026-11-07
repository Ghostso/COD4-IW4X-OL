p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# arm uses seq 0 (server-initiated), 0x89 echoes request seq
old = """            arm_out = wrap_85(fr["seq"], os.urandom(16), arm_rep,
                              aes_out, hmac_out)"""
new = """            arm_out = wrap_85(0, os.urandom(16), arm_rep,
                              aes_out, hmac_out)"""
src = src.replace(old, new)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
