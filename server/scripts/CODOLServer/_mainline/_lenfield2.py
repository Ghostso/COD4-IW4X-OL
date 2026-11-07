p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()

# reply site
old = '''                                        reply = build_0x85_server_cbc(
                                            seq, src20, frame_len=382,
                                            aes_key=rk, inner=inner,'''
new = '''                                        reply = build_0x85_server_cbc(
                                            seq, src20, frame_len=382,
                                            len_field=reply_85_len_field,
                                            aes_key=rk, inner=inner,'''
assert old in s
s = s.replace(old, new, 1)

# param
old2 = "                    reply_85_zero_keys: bool = False,"
new2 = old2 + "\n                    reply_85_len_field: int = -1,"
assert old2 in s
s = s.replace(old2, new2, 1)

# arg
old3 = '''    ap.add_argument("--reply-85-zero-keys", action="store_true",'''
new3 = '''    ap.add_argument("--reply-85-len-field", type=lambda s: int(s, 0),
                    default=-1,
                    help="override the u32 length field written into reply "
                         "0x85 frames (client checks field + cursor <= "
                         "obj+0xAC, so 382 always fails)")
    ap.add_argument("--reply-85-zero-keys", action="store_true",'''
assert old3 in s
s = s.replace(old3, new3, 1)

# wiring
old4 = "                                       a.reply_85_zero_keys,"
new4 = old4 + "\n                                       a.reply_85_len_field,"
assert old4 in s
s = s.replace(old4, new4, 1)

open(p, "w", encoding="utf-8").write(s)
print("probe wired")
