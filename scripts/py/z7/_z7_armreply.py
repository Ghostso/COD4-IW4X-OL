p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# In decrypt_and_reply, before sending the task reply:
# 1) Send 0x87 arm first (only on the first reply)
# 2) Then send the 0x89 business reply
old = """        objs = self.handle_task(inner)
        rid = self.reply_id
        self.reply_id += 1
        rep = build_reply(fr["seq"], rid, inner["task"], 0, objs)
        out = wrap_85(fr["seq"], os.urandom(16), rep, aes_out, hmac_out)
        c.sendall(out)
        self.log("-> 0x85 reply seq=%d replyId=%d nobj=%d len=%d"
                 % (fr["seq"], rid, len(objs) if objs else 0, len(out)))"""

new = """        # First reply in a session: arm the 0x87 gate first.
        # 0xBA3600 (the 0x89 handler) requires [req+0x644] == 1, which is
        # only set by a successful 0xBA3590 (0x87) arm.  Without the arm,
        # the client drops our replies.
        if not self.armed:
            arm_inner = bytes([0x87, 0x01])
            arm_rep = struct.pack("<I", len(arm_inner)) + arm_inner
            arm_out = wrap_85(fr["seq"], os.urandom(16), arm_rep,
                              aes_out, hmac_out)
            c.sendall(arm_out)
            self.armed = True
            self.log("-> 0x85 arm seq=%d (0x87) len=%d"
                     % (fr["seq"], len(arm_out)))
        objs = self.handle_task(inner)
        rid = self.reply_id
        self.reply_id += 1
        # Build 0x89 business reply: the first decrypted byte must be 0x89
        # so the client's dispatcher routes it to 0xBA3600
        payload = b""
        for o in (objs or []):
            payload += o
        body_89 = (bytes([0x01, 1, 0x00]) + b"\\x00" * 32 +
                   struct.pack("<H", len(payload)) + payload +
                   struct.pack("<I", 0))
        rep = struct.pack("<I", len(body_89)) + body_89
        out = wrap_85(fr["seq"], os.urandom(16), rep, aes_out, hmac_out)
        c.sendall(out)
        self.log("-> 0x85 reply seq=%d replyId=%d 0x89 nobj=%d len=%d"
                 % (fr["seq"], rid, len(objs) if objs else 0, len(out)))"""

src = src.replace(old, new)

# Add armed flag to LobbyServer __init__
old_init = "        self.reply_id = 1\n        self.pending = []"
new_init = "        self.reply_id = 1\n        self.pending = []\n        self.armed = False"
src = src.replace(old_init, new_init)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
