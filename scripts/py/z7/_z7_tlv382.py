p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# 1. Revert build_reply to TLV (should already be TLV, verify)
if "0x89 inner message" in src:
    # need to revert
    old_89 = """def build_reply(seq, reply_id, task, status, objects=None):
    \"\"\"Build the server->client 0x85 reply as a 0x89 inner message."""
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
    return struct.pack("<I", len(body)) + body"""
    new_tlv = """def build_reply(seq, reply_id, task, status, objects=None):
    \"\"\"Build the server->client 0x85 reply plaintext (before AES).\"\"\"
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
    return struct.pack("<I", len(body)) + body"""
    src = src.replace(old_89, new_tlv)

# 2. Replace the 0x89 reply code in decrypt_and_reply with TLV + 382 frame
old_89reply = """        # Build 0x89 business reply: the first decrypted byte must be 0x89
        # so the client's dispatcher routes it to 0xBA3600
        payload = b""
        if objs:
            for o in objs:
                payload += o
        else:
            # Even for tasks we don't handle, include one empty 13/08 object
            # so the client's parser sees nobj >= 1 with valid data
            payload += bytes([0x13, 0x08]) + struct.pack("<I", 0)
        # 32B session field must match [req+0x648] (memcmp at 0xBA1171)
        f648_path = self.echo_file.replace("echo.txt", "field648.txt")
        field648 = b"\\x00" * 32  # fallback
        try:
            f648_hex = open(f648_path, encoding="ascii").read().strip()
            if len(f648_hex) == 64:
                field648 = bytes.fromhex(f648_hex)
        except (OSError, ValueError):
            pass
        body_89 = (bytes([0x01, 1, 0x00]) + field648 +
                   struct.pack("<H", len(payload)) + payload +
                   struct.pack("<I", 0))
        rep = struct.pack("<I", len(body_89)) + body_89
        out = wrap_85(fr["seq"], os.urandom(16), rep, aes_out, hmac_out)
        c.sendall(out)
        self.log("-> 0x85 reply seq=%d replyId=%d 0x89 nobj=%d len=%d"
                 % (fr["seq"], rid, len(objs) if objs else 0, len(out)))"""

new_tlvreply = """        # Build TLV reply (0x01 first byte → 0xBA3B36 else path → 0xB9BBC0)
        rep = build_reply(fr["seq"], rid, inner["task"], 0, objs)
        # Pad to 382-byte frame so client's parser sees expected size
        inner_data = rep
        frame_len = 382
        inner_len = frame_len - 2 - 4 - 16 - 8
        plaintext = inner_data + b"\\x00" * (inner_len - len(inner_data))
        iv = os.urandom(16)
        ct = aes128cbc_enc(aes_out, iv, plaintext)
        body = struct.pack("<I", fr["seq"]) + iv + ct
        frame_wo_tag = struct.pack("<I", frame_len) + b"\\x00\\x85" + body
        tag = hmac8(hmac_out, frame_wo_tag)
        out = frame_wo_tag + tag
        c.sendall(out)
        self.log("-> 0x85 reply seq=%d replyId=%d TLV nobj=%d frame=%d"
                 % (fr["seq"], rid, len(objs) if objs else 0, len(out)))"""

src = src.replace(old_89reply, new_tlvreply)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
