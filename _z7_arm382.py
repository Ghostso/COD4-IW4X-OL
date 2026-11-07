p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# Replace the arm sending in decrypt_and_reply to use 382-byte frames
old = """        if not self.armed:
            arm_inner = bytes([0x87, 0x01])
            arm_rep = struct.pack("<I", len(arm_inner)) + arm_inner
            arm_out = wrap_85(0, os.urandom(16), arm_rep,
                              aes_out, hmac_out)
            c.sendall(arm_out)
            self.armed = True
            self.log("-> 0x85 arm seq=%d (0x87) len=%d"
                     % (fr["seq"], len(arm_out)))"""

new = """        if not self.armed:
            # The client's 0xBA3710 parser expects a full-size frame
            # (the wire length field must match what the parser reads).
            # frame_len=382 gives inner_len=352 bytes of AES plaintext.
            frame_len = 382
            inner = bytes([0x87, 0x01])
            inner_len = frame_len - 2 - 4 - 16 - 8  # type+opcode+seq+iv+hmac
            plaintext = inner + b"\\x00" * (inner_len - len(inner))
            iv = os.urandom(16)
            ct = aes128cbc_enc(aes_out, iv, plaintext)
            body = struct.pack("<I", 0) + iv + ct  # seq=0 for server-initiated
            frame_wo_tag = struct.pack("<I", frame_len) + b"\\x00\\x85" + body
            tag = hmac8(hmac_out, frame_wo_tag)
            arm_out = frame_wo_tag + tag
            c.sendall(arm_out)
            self.armed = True
            self.log("-> 0x85 arm (0x87) frame_len=%d total=%d"
                     % (frame_len, len(arm_out)))"""

src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
