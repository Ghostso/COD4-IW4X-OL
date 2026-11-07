import sys, os, struct, re
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT")
import codol_crypto as cc
import lobby_server as ls

print(f"Lobby SEC_KEY: {ls.SEC_KEY.hex()}")
assert ls.SEC_KEY == bytes.fromhex("01" * 16), f"SEC_KEY mismatch: {ls.SEC_KEY.hex()}"

# 1. Test 21/5 findSessions
print("\n--- Test 1: 21/5 findSessions ---")
b = cc.Buf(use_types=True)
b.u32(1) # queryKind
b.u32(0)
b.u32(10) # playlist 10
req_21_5 = b.data()

objs, note, pushes = ls.reply_objects(21, 5, req_21_5)
print(f"findSessions note: {note}")
assert len(objs) == 1, f"Expected 1 session object, got {len(objs)}"
session_obj = objs[0]
print(f"Session object length: {len(session_obj)} bytes")

# Parse first field (address blob)
tag = session_obj[0]
assert tag == 0x13, f"Expected tag 0x13, got 0x{tag:02X}"
len_tag = session_obj[1]
assert len_tag == 0x08, f"Expected len_tag 0x08, got 0x{len_tag:02X}"
addr_len = struct.unpack_from("<I", session_obj, 2)[0]
print(f"Address blob length: {addr_len} bytes (0x{addr_len:02X})")
assert addr_len == 67, f"CRITICAL: Address blob length must be 67 (0x43) for 0xB95C50! Got {addr_len}"
addr_blob = session_obj[6 : 6 + addr_len]
ip = f"{addr_blob[0]}.{addr_blob[1]}.{addr_blob[2]}.{addr_blob[3]}"
port = struct.unpack_from("<H", addr_blob, 4)[0]
print(f"Extracted endpoint from address blob: {ip}:{port}")
assert ip == "127.0.0.1" and port == 28960, f"Endpoint mismatch: {ip}:{port}"

# 2. Test 6/14 mmbook
print("\n--- Test 2: 6/14 mmbook ---")
req_mmbook_body = b"\x0a\x01\x00\x00\x00\x00\x00\x00\x00\x13\x08\x1b\x00\x00\x00\x17\x00\x00\x00mmbook 796 AQAAAAAAAAA= 0\x00"
objs_bk, note_bk, pushes_bk = ls.reply_objects(6, 14, req_mmbook_body)
print(f"mmbook note: {note_bk}")
assert len(pushes_bk) == 1, f"Expected 1 push, got {len(pushes_bk)}"
mt, push_body = pushes_bk[0]
assert mt == 2, f"Expected push marker type 2, got {mt}"
print(f"Push body length: {len(push_body)} bytes")

# Parse push_body envelope:
# [08 15 00 00 00] [0A sender_id (8B)] [10 string 00] [13 08 len ... data]
assert push_body[0] == 0x08 and struct.unpack_from("<I", push_body, 1)[0] == 21, "Service != 21"
assert push_body[5] == 0x0A, "SenderID tag != 0x0A"
sender_id = struct.unpack_from("<Q", push_body, 6)[0]
sender_low = sender_id & 0xFFFFFFFF
sender_high = sender_id >> 32
print(f"Push envelope sender_id: {sender_id} (low=A={sender_low}, high=B={sender_high})")
assert sender_low == 796, f"Expected sender_low == 796 (matching mmbook A), got {sender_low}"
assert sender_high == 0, f"Expected sender_high == 0 (matching mmbook B), got {sender_high}"

# Read string "localhost\0"
idx = 14
assert push_body[idx] == 0x10, "Sender name tag != 0x10"
idx += 1
name_end = push_body.find(b"\x00", idx)
sender_name = push_body[idx:name_end].decode("ascii")
print(f"Push envelope sender_name: '{sender_name}'")
idx = name_end + 1

# Read blob
assert push_body[idx] == 0x13 and push_body[idx+1] == 0x08, "Data blob tag != 0x13 0x08"
data_len = struct.unpack_from("<I", push_body, idx+2)[0]
data_blob = push_body[idx+6 : idx+6+data_len]
print(f"Push data blob len: {data_len} bytes")
inner_len = struct.unpack_from("<I", data_blob, 0)[0]
inner_msg = data_blob[4 : 4 + inner_len]
print(f"Inner message (len={inner_len}): {inner_msg}")
assert inner_msg.startswith(b"mmbook accepted"), f"Inner message must start with 'mmbook accepted', got {inner_msg}"

# 3. Test push encryption roundtrip
print("\n--- Test 3: Push frame encryption roundtrip ---")
aes_in = os.urandom(16)
hmac_in = os.urandom(16)
pseq = 50
pf = cc.build_push(aes_in, hmac_in, pseq, push_body, mt)
dec = cc.decrypt_task_frame(pf, aes_in, hmac_in)
assert dec["hmac_ok"], "HMAC failed"
assert dec["marker"] == 2, "Marker != 2"
assert dec["declared"] == len(push_body), "Declared len mismatch"
dec_body = dec["plain"][5 : 5 + dec["declared"]]
assert dec_body == push_body, "Decrypted body mismatch"
print(f"Frame built & decrypted: len={len(pf)} seq={pseq} hmac_ok=True body_match=True")

print("\n=======================================================")
print("ALL OFFLINE REPLAY ASSERTIONS PASSED! 100% GREEN!")
print("=======================================================")
