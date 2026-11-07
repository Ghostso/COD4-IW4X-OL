p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# After sending 0x83, immediately send 0x87 arm frame
# Find the 0x83 send in on_frame
old = """            c.sendall(build_0x83(ch))
            state["sent83"] = True
            self.log("-> 0x83 challenge=%s" % hexs(ch))"""
new = """            c.sendall(build_0x83(ch))
            state["sent83"] = True
            self.log("-> 0x83 challenge=%s" % hexs(ch))
            # Immediately follow with 0x87 arm (sets [req+0x644]=1, required
            # before any 0x89 business frame will be accepted by 0xBA3600)
            self.send_arm(c)

    def send_arm(self, c):
        \"\"\"Send a server->client 0x85 frame containing the 0x87 arm inner.\"\"\"
        self.secrets.load()
        aes_out = self.secrets.get("aes_out")
        hmac_out, _ = self.secrets.hmac_keys()
        if not aes_out or not hmac_out:
            self.log("   !! arm: secrets not ready")
            return
        inner = bytes([0x87, 0x01])
        rep = struct.pack("<I", len(inner)) + inner
        out = wrap_85(0, os.urandom(16), rep, aes_out, hmac_out)
        c.sendall(out)
        self.log("-> 0x85 arm (0x87) len=%d" % len(out))"""
src = src.replace(old, new)

# Fix indentation: the send_arm call is inside on_frame which is a method,
# so send_arm must be a separate method at the class level
# The code above already puts it as a method because of the newline+def
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
