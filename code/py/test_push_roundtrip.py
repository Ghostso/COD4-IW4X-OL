import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT")
import codol_crypto as cc

# Test encrypt and decrypt of a push frame with sender_id=796
aes_in = os.urandom(16)
hmac_in = os.urandom(16)
aes_out = os.urandom(16)
hmac_out = os.urandom(16)

# Generate push frame
FR_BOOKING_ACCEPTED = b"mmbook accepted\x00"
accepted = len(FR_BOOKING_ACCEPTED).to_bytes(4, "little") + FR_BOOKING_ACCEPTED
sender_id = 796
push_body = cc.instant_push_body(sender_id, "localhost", accepted)
push_frame = cc.build_push(aes_in, hmac_in, 50, push_body, message_type=2)

print(f"Push frame len: {len(push_frame)}")
dec = cc.decrypt_task_frame(push_frame, aes_in, hmac_in)
print(f"Decrypted: marker={dec['marker']} declared={dec['declared']} hmac_ok={dec['hmac_ok']}")

# Unpack plain
plain = dec["plain"]
body = plain[5 : 5 + dec["declared"]]
print(f"Body matches: {body == push_body}")
