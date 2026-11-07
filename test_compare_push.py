import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT")
import codol_crypto as cc

# What REF_LOBBY_KIT did before:
FR_BOOKING_ACCEPTED = b"mmbook accepted\x00"
accepted_old = len(FR_BOOKING_ACCEPTED).to_bytes(4, "little") + FR_BOOKING_ACCEPTED
body_old = cc.instant_push_body(1, "localhost", accepted_old)
print("Old push body hex:")
print(body_old.hex(" "))

# What it SHOULD be:
body_new = cc.instant_push_body(796, "localhost", b"mmbook accepted\x00")
print("\nNew push body hex (sender_id=796, message='mmbook accepted\\x00'):")
print(body_new.hex(" "))
