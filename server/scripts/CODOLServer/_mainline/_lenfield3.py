p = r"CODOLServer\_mainline\_e57a5c_experiment.py"
s = open(p, encoding="utf-8").read()

old = "                reply_85_zero_keys: bool = False,"
new = old + "\n                reply_85_len_field: int = -1,"
assert old in s
s = s.replace(old, new, 1)

old2 = '''        if reply_85_zero_keys:
            argv.append("--reply-85-zero-keys")'''
new2 = old2 + '''
        if reply_85_len_field >= 0:
            argv += ["--reply-85-len-field", str(reply_85_len_field)]'''
assert old2 in s
s = s.replace(old2, new2, 1)

old3 = '''    ap.add_argument("--reply-85-zero-keys", action="store_true",'''
new3 = '''    ap.add_argument("--reply-85-len-field", type=lambda s: int(s, 0),
                    default=-1,
                    help="override the u32 length field in reply 0x85 frames "
                         "(client requires field + cursor <= obj+0xAC)")
    ap.add_argument("--reply-85-zero-keys", action="store_true",'''
assert old3 in s
s = s.replace(old3, new3, 1)

old4 = "            reply_85_zero_keys=a.reply_85_zero_keys,"
new4 = old4 + "\n            reply_85_len_field=a.reply_85_len_field,"
assert old4 in s
s = s.replace(old4, new4, 1)

open(p, "w", encoding="utf-8").write(s)
print("driver wired")
