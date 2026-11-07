p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# Change empty task reply to include at least one empty object
old = """        payload = b""
        for o in (objs or []):
            payload += o"""
new = """        payload = b""
        if objs:
            for o in objs:
                payload += o
        else:
            # Even for tasks we don't handle, include one empty 13/08 object
            # so the client's parser sees nobj >= 1 with valid data
            payload += bytes([0x13, 0x08]) + struct.pack("<I", 0)"""
src = src.replace(old, new)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
