p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# Replace build_reply to produce 0x89 inner format instead of TLV
# 0x89 inner: u8 ver=1 | u8 subtype | u8 flag=0 | 32B field | u16 len | payload | u32 value
# From lobby_plain_probe.py build_inner_89:
#   body = bytes([0x01, subtype, 0x00]) + flag32 + struct.pack("<H", len(payload)) + payload + struct.pack("<I", value)
old_reply = '''def build_reply(seq, reply_id, task, status, objects=None):
    """Build the server->client 0x85 reply plaintext (before AES)."""
    tlv = b""
    tlv += bytes([TAG_REPLYID]) + struct.pack("<Q", reply_id)
    tlv += bytes([TAG_STATUS]) + struct.pack("<I", status)
    tlv += bytes([TAG_TASK]) + bytes([task])
    nobj = len(objects) if objects else 0
    tlv += bytes([TAG_NOBJ]) + struct.pack("<I", nobj)
    if objects:
        tlv += bytes([TAG_NOBJ]) + struct.pack("<I", nobj)
        for o in objects:
            tlv += o
    body = b"\\x01" + tlv
    return struct.pack("<I", len(body)) + body'''

new_reply = '''def build_reply(seq, reply_id, task, status, objects=None):
    """Build the server->client 0x85 reply as a 0x89 inner message.

    The client's dispatcher (0xBA3AE6) reads the FIRST decrypted byte:
      0x87 -> arm
      0x89 -> business
    Anything else falls through and the connection gets dropped.  Our replies
    must therefore use the 0x89 inner format, NOT the TLV layout (which is
    the /auth/ HTTP body format, not the lobby frame format).

    0x89 inner layout (from 0xBA0FF0):
      u8   ver      == 1
      u8   subtype  in {1,2}
      u8   flag     0
      32B  field    compared with [req+0x648]
      u16   len     <= 0x400
      u8[]  payload
      u32   value
    """
    # Pack any data objects into the payload; empty objects -> empty payload
    payload = b""
    if objects:
        for o in objects:
            payload += o
    flag32 = b"\\x00" * 32
    subtype = 1
    value = 0
    body = (bytes([0x01, subtype, 0x00]) + flag32 +
            struct.pack("<H", len(payload)) + payload +
            struct.pack("<I", value))
    return struct.pack("<I", len(body)) + body'''

src = src.replace(old_reply, new_reply)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
