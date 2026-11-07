import re
p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# Remove the misplaced send_arm from on_frame
# It's between "self.log("-> 0x83 ...")\n            # Immediately..." and "        elif op == 0x85:"
# We need to move the method definition after on_85/dispatch

# First: remove the send_arm method from its current (broken) position
pat_remove = re.compile(
    r'(            self\.log\("-> 0x83 challenge=%s" % hexs\(ch\)\)\n)'
    r'(            # Immediately follow with 0x87 arm.*?def send_arm\(self, c\):\n'
    r'.*?self\.log\("-> 0x85 arm \(0x87\) len=%d" % len\(out\)\)\n)'
    r'(        elif op == 0x85:)',
    re.S
)
m = pat_remove.search(src)
if m:
    # Keep only the comment + call, move method to after on_85
    arm_method = '''    def send_arm(self, c):
        """Send a server->client 0x85 frame containing the 0x87 arm inner."""
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
        self.log("-> 0x85 arm (0x87) len=%d" % len(out))

'''
    replacement = (m.group(1) +
                   '            # Immediately follow with 0x87 arm\n'
                   '            self.send_arm(c)\n'
                   + m.group(3))
    src = src[:m.start()] + replacement + src[m.end():]
    
    # Now insert send_arm method after on_85 (before handle_task)
    insert_before = "    def handle_task(self, inner):"
    src = src.replace(insert_before, arm_method + insert_before, 1)

open(p, "w", encoding="utf-8", newline="").write(src)
print("fixed")
