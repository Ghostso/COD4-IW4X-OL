p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

old = """    def push_frame(self, c, seq, service, task, payload=b""):
        \"\"\"Send a server->client 0x85 task push frame.\"\"\"
        self.secrets.load()
        aes_out = self.secrets.get("aes_out")
        hmac_out, _ = self.secrets.hmac_keys()
        if not aes_out or not hmac_out:
            self.log("   !! push: secrets not ready")
            return
        inner = self.build_task_inner(service, task, payload)
        # Pad to AES block size
        inner_len = 382 - 2 - 4 - 16 - 8
        if len(inner) > inner_len:
            inner_len = ((len(inner) + 15) // 16) * 16
        plaintext = inner + b"\\x00" * (inner_len - len(inner))
        iv = os.urandom(16)
        ct = aes128cbc_enc(aes_out, iv, plaintext)
        body = struct.pack("<I", seq) + iv + ct
        frame_wo_tag = struct.pack("<I", frame_len) + b"\\x00\\x85" + body
        tag = hmac8(hmac_out, frame_wo_tag)
        frame = frame_wo_tag + tag
        c.sendall(frame)
        self.log("-> 0x85 push seq=%d svc=%d task=%d len=%d" % (seq, service, task, len(frame)))"""

new = """    def push_frame(self, c, seq, service, task, payload=b""):
        \"\"\"Send a server->client 0x85 task push frame.\"\"\"
        self.secrets.load()
        aes_out = self.secrets.get("aes_out")
        hmac_out, _ = self.secrets.hmac_keys()
        if not aes_out or not hmac_out:
            self.log("   !! push: secrets not ready")
            return
        inner = self.build_task_inner(service, task, payload)
        fl = 382
        inner_len = fl - 2 - 4 - 16 - 8
        if len(inner) > inner_len:
            inner_len = ((len(inner) + 15) // 16) * 16
        plaintext = inner + b"\\x00" * (inner_len - len(inner))
        iv = os.urandom(16)
        ct = aes128cbc_enc(aes_out, iv, plaintext)
        body = struct.pack("<I", seq) + iv + ct
        frame_wo_tag = struct.pack("<I", fl) + b"\\x00\\x85" + body
        tag = hmac8(hmac_out, frame_wo_tag)
        frame = frame_wo_tag + tag
        c.sendall(frame)
        self.log("-> 0x85 push seq=%d svc=%d task=%d len=%d" % (seq, service, task, len(frame)))"""

src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
