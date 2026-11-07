p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()

old = '''                          aes_key: bytes = b"",
                          inner: bytes = b"",
                          zero_keys: bool = False) -> bytes:'''
new = '''                          aes_key: bytes = b"",
                          inner: bytes = b"",
                          zero_keys: bool = False,
                          len_field: int = -1) -> bytes:'''
assert old in s
s = s.replace(old, new, 1)

old2 = '''    frame_without_tag = struct.pack("<I", frame_len) + bytes([0x00, 0x85]) + body'''
new2 = '''    # The client's 0xBA3AC2 check is:  frame_len_field + cursor <= obj+0xAC.
    # Our own frame_len (382) makes that fail, so the arm never runs.  Allow
    # the wire length field to differ from the actual frame size.
    wire_len = frame_len if len_field < 0 else (len_field & 0xFFFFFFFF)
    frame_without_tag = struct.pack("<I", wire_len) + bytes([0x00, 0x85]) + body'''
assert old2 in s
s = s.replace(old2, new2, 1)
open(p, "w", encoding="utf-8").write(s)
print("probe builder patched")
