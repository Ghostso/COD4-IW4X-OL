p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# Add a push_config method and call it after send_arm in on_frame
# Also need to build inner frames with service/task header

# First, add a helper to build the inner 0x85 task frame
# inner format: u32 declared | 0x86 | service | 0x03 | task | payload(declared-3)
helper = '''
    def build_task_inner(self, service, task, payload=b""):
        """Build inner plaintext for a server->client task push.
        Format: u32 declared | 0x86 | service | 0x03 | task | payload"""
        declared = 3 + len(payload)
        inner = struct.pack("<I", declared) + bytes([0x86, service, 0x03, task]) + payload
        return inner

    def push_frame(self, c, seq, service, task, payload=b""):
        """Send a server->client 0x85 task push frame."""
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
        self.log("-> 0x85 push seq=%d svc=%d task=%d len=%d" % (seq, service, task, len(frame)))

    def push_config(self, c):
        """Push all configuration data after 0x83 handshake."""
        self.secrets.load()
        seq = 100  # start from a high seq to avoid collision with client seq
        # 10/21 x10: publisher .info files
        for i, info_data in enumerate(PUBLISHER_INFOS):
            payload = bytes([0x13, 0x08]) + struct.pack("<I", len(info_data)) + info_data
            self.push_frame(c, seq, 10, 21, payload)
            seq += 1
        # 10/12: user file
        user_data = USER_NAME.encode("ascii") + b"\\x00" * 16
        payload = bytes([0x13, 0x08]) + struct.pack("<I", len(user_data)) + user_data
        self.push_frame(c, seq, 10, 12, payload)
        seq += 1
        # 8/1: public profile
        prof = _profile_public()
        payload = bytes([0x13, 0x08]) + struct.pack("<I", len(prof)) + prof
        self.push_frame(c, seq, 8, 1, payload)
        seq += 1
        # 8/2: secure profile
        prof2 = _profile_secure()
        payload = bytes([0x13, 0x08]) + struct.pack("<I", len(prof2)) + prof2
        self.push_frame(c, seq, 8, 2, payload)
        seq += 1
        # 80/130: CP balance
        cp_data = bytes([0x03, 0x01, 0x08]) + struct.pack("<I", CP_BALANCE)
        self.push_frame(c, seq, 80, 130, cp_data)
        seq += 1
        # 93/1: GP balance
        gp_data = bytes([0x03, 0x02, 0x08]) + struct.pack("<I", GP_BALANCE)
        self.push_frame(c, seq, 93, 1, gp_data)
        seq += 1
        self.log("-> pushed %d config frames" % (seq - 100))
'''

# Insert helper methods before handle_task
insert_before = "    def handle_task(self, inner):"
src = src.replace(insert_before, helper + "\n" + insert_before, 1)

# Call push_config after send_arm in on_frame
old_arm = "            self.send_arm(c)"
new_arm = "            self.send_arm(c)\n            self.push_config(c)"
src = src.replace(old_arm, new_arm)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
